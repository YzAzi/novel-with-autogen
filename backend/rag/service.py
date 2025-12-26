from __future__ import annotations

import datetime as dt
import json
import os
import uuid
from dataclasses import asdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import RagChunk
from app.db.session import SessionLocal
from rag.chunking import chunk_novel_text
from rag.embeddings_bge_m3 import BgeM3Embeddings
from rag.embeddings_mock import MockEmbeddings
from rag.rerank_bge import BgeReranker
from rag.rerank_mock import MockReranker, rule_score
from rag.types import Chunk, RetrievalDebug


class RAGService:
    def __init__(self) -> None:
        self._chroma = None
        self._embeddings = None
        self._reranker = None
        self._notes: List[str] = []

    def _get_chroma(self):
        if self._chroma is not None:
            return self._chroma
        try:
            import chromadb  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError("chromadb is required") from e

        persist_dir = getattr(settings, "chroma_persist_dir", "data/chroma")
        os.makedirs(persist_dir, exist_ok=True)
        self._chroma = chromadb.PersistentClient(path=persist_dir)
        return self._chroma

    def _collection(self, project_id: str):
        client = self._get_chroma()
        name = f"project_{project_id}"
        return client.get_or_create_collection(name=name)

    def _get_embeddings(self):
        if self._embeddings is not None:
            return self._embeddings
        provider = getattr(settings, "embeddings_provider", "mock")
        if provider == "local_bge_m3":
            try:
                self._embeddings = BgeM3Embeddings(
                    model_name=getattr(settings, "bge_m3_model_name", "BAAI/bge-m3"),
                    device=getattr(settings, "rag_device", None),
                )
            except Exception:
                self._embeddings = MockEmbeddings()
                self._notes.append("Embeddings local_bge_m3 load failed; fallback to mock.")
        else:
            self._embeddings = MockEmbeddings()
        return self._embeddings

    def _get_reranker(self):
        if self._reranker is not None:
            return self._reranker
        provider = getattr(settings, "rerank_provider", "mock")
        if provider == "local_bge":
            try:
                self._reranker = BgeReranker(
                    model_name=getattr(settings, "bge_rerank_model_name", "BAAI/bge-reranker-v2-m3"),
                    device=getattr(settings, "rag_device", None),
                )
            except Exception:
                self._reranker = MockReranker()
                self._notes.append("Reranker local_bge load failed; fallback to mock.")
        else:
            self._reranker = MockReranker()
        return self._reranker

    def pop_notes(self) -> List[str]:
        notes = self._notes[:]
        self._notes.clear()
        return notes

    def _embed_cached(self, db: Session, texts: List[str]) -> List[List[float]]:
        model_name = self._get_embeddings().model_name
        out: List[List[float]] = []
        missing: List[Tuple[int, str, str]] = []
        for idx, t in enumerate(texts):
            cache_key = f"{model_name}:{uuid.uuid5(uuid.NAMESPACE_DNS, t)}"
            row = db.execute(
                sql_text("SELECT vector_json FROM embeddings_cache WHERE cache_key = :k"),
                {"k": cache_key},
            ).fetchone()
            if row:
                out.append(json.loads(row[0]))
            else:
                out.append([])
                missing.append((idx, cache_key, t))

        if missing:
            vectors = self._get_embeddings().embed_texts([t for _, _, t in missing])
            now = dt.datetime.now(dt.timezone.utc).isoformat()
            for (idx, cache_key, _), vec in zip(missing, vectors):
                out[idx] = vec
                db.execute(
                    sql_text(
                        "INSERT OR REPLACE INTO embeddings_cache(cache_key, model_name, vector_json, created_at) VALUES(:k,:m,:v,:t)"
                    ),
                    {"k": cache_key, "m": model_name, "v": json.dumps(vec), "t": now},
                )
        return out

    def index_document(self, project_id: str, type: str, text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        chunks = chunk_novel_text(
            text,
            max_chars=int(getattr(settings, "rag_max_chunk_chars", 1400)),
            overlap_ratio=float(getattr(settings, "rag_overlap_ratio", 0.2)),
        )
        if not chunks:
            return {"indexed_chunks": 0}

        source_id = str(metadata.get("source_id") or "")
        chapter_no = metadata.get("chapter_no")

        with SessionLocal() as db:
            # Remove prior chunks for this (project,type,source_id) to support updates.
            if source_id:
                old_ids = [
                    r[0]
                    for r in db.execute(
                        sql_text("SELECT id FROM rag_chunks WHERE project_id=:p AND type=:t AND source_id=:s"),
                        {"p": project_id, "t": type, "s": source_id},
                    ).fetchall()
                ]
                if old_ids:
                    placeholders = ",".join([f":id{i}" for i in range(len(old_ids))])
                    params = {f"id{i}": cid for i, cid in enumerate(old_ids)}
                    db.execute(sql_text(f"DELETE FROM rag_chunks WHERE id IN ({placeholders})"), params)
                    db.execute(sql_text(f"DELETE FROM rag_chunks_fts WHERE chunk_id IN ({placeholders})"), params)
                    try:
                        self._collection(project_id).delete(ids=old_ids)
                    except Exception:
                        pass

            chunk_ids: List[str] = [str(uuid.uuid4()) for _ in chunks]
            vectors = self._embed_cached(db, [c.text for c in chunks])

            created_at = dt.datetime.now(dt.timezone.utc)
            rows = []
            for cid, c in zip(chunk_ids, chunks):
                meta = dict(metadata)
                meta.update(
                    {
                        "project_id": project_id,
                        "type": type,
                        "chapter_no": chapter_no,
                        "chunk_id": cid,
                        "created_at": created_at.isoformat(),
                        "source_id": source_id,
                        "characters": str(metadata.get("characters") or ""),
                        "locations": str(metadata.get("locations") or ""),
                        "pov": str(metadata.get("pov") or ""),
                    }
                )
                rows.append(
                    RagChunk(
                        id=cid,
                        project_id=project_id,
                        type=type,
                        created_at=created_at,
                        source_id=source_id,
                        chapter_no=chapter_no,
                        characters=str(metadata.get("characters") or ""),
                        locations=str(metadata.get("locations") or ""),
                        pov=str(metadata.get("pov") or ""),
                        text=c.text,
                        snippet=c.snippet,
                        metadata_json=json.dumps(meta, ensure_ascii=False),
                    )
                )

            db.add_all(rows)
            for cid, c in zip(chunk_ids, chunks):
                db.execute(
                    sql_text(
                        "INSERT INTO rag_chunks_fts(chunk_id, project_id, type, chapter_no, text) VALUES(:id,:p,:t,:c,:x)"
                    ),
                    {"id": cid, "p": project_id, "t": type, "c": chapter_no, "x": c.text},
                )

            # Chroma upsert
            try:
                metadatas = [json.loads(r.metadata_json) for r in rows]
                self._collection(project_id).upsert(
                    ids=chunk_ids,
                    embeddings=vectors,
                    metadatas=metadatas,
                    documents=[c.text for c in chunks],
                )
            except Exception:
                pass

            db.commit()

        return {"indexed_chunks": len(chunks)}

    def _vector_retrieve(
        self,
        *,
        project_id: str,
        query: str,
        where: Dict[str, Any],
        top_k: int,
    ) -> List[Chunk]:
        try:
            qvec = self._get_embeddings().embed_query(query)
            res = self._collection(project_id).query(
                query_embeddings=[qvec],
                n_results=top_k,
                where=where or None,
                include=["documents", "metadatas", "distances"],
            )
        except Exception:
            return []

        out: List[Chunk] = []
        ids = (res.get("ids") or [[]])[0]
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        for cid, doc, meta, dist in zip(ids, docs, metas, dists):
            score = 1.0 / (1.0 + float(dist if dist is not None else 1.0))
            out.append(
                Chunk(
                    id=str(cid),
                    project_id=project_id,
                    type=str((meta or {}).get("type", "")),
                    text=str(doc),
                    snippet=str(doc)[:240] + ("…" if len(str(doc)) > 240 else ""),
                    score=score,
                    channel="vector",
                    metadata=dict(meta or {}),
                )
            )
        return out

    def _keyword_retrieve(
        self,
        db: Session,
        *,
        project_id: str,
        query: str,
        types: List[str] | None,
        chapter_no_max_for_chapter: int | None,
        top_k: int,
    ) -> List[Chunk]:
        rows = []
        try:
            where = "project_id = :p AND rag_chunks_fts MATCH :q"
            params: Dict[str, Any] = {"p": project_id, "q": query}
            if types:
                where += " AND type IN ({})".format(",".join([f":t{i}" for i in range(len(types))]))
                for i, t in enumerate(types):
                    params[f"t{i}"] = t

            if chapter_no_max_for_chapter is not None:
                where += " AND (type != 'chapter' OR chapter_no <= :cmax)"
                params["cmax"] = int(chapter_no_max_for_chapter)

            rows = db.execute(
                sql_text(
                    f"""
                    SELECT chunk_id, type, chapter_no, bm25(rag_chunks_fts) AS rank
                    FROM rag_chunks_fts
                    WHERE {where}
                    ORDER BY rank ASC
                    LIMIT :k
                    """
                ),
                {**params, "k": top_k},
            ).fetchall()
        except Exception:
            # Fallback (no FTS5): naive substring scoring over rag_chunks.
            tokens = [t for t in query.replace("，", " ").replace(",", " ").split() if len(t) >= 2][:8]
            if not tokens:
                return []
            where_sql = "project_id = :p"
            params = {"p": project_id}
            if types:
                where_sql += " AND type IN ({})".format(",".join([f":t{i}" for i in range(len(types))]))
                for i, t in enumerate(types):
                    params[f"t{i}"] = t
            if chapter_no_max_for_chapter is not None:
                where_sql += " AND (type != 'chapter' OR chapter_no <= :cmax)"
                params["cmax"] = int(chapter_no_max_for_chapter)
            candidates = db.execute(
                sql_text(f"SELECT id, type, chapter_no, text FROM rag_chunks WHERE {where_sql}"),
                params,
            ).fetchall()
            scored = []
            for cid, t, cno, txt in candidates:
                hit = sum(txt.count(tok) for tok in tokens)
                if hit > 0:
                    scored.append((hit, cid, t, cno))
            scored.sort(key=lambda x: x[0], reverse=True)
            rows = [(cid, t, cno, 1.0 / (1.0 + hit)) for hit, cid, t, cno in scored[:top_k]]

        if not rows:
            return []

        chunk_ids = [r[0] for r in rows]
        chunk_rows = db.execute(
            sql_text(
                "SELECT id, type, text, snippet, metadata_json FROM rag_chunks WHERE id IN ({})".format(
                    ",".join([f":id{i}" for i in range(len(chunk_ids))])
                )
            ),
            {f"id{i}": cid for i, cid in enumerate(chunk_ids)},
        ).fetchall()
        by_id = {r[0]: r for r in chunk_rows}

        out: List[Chunk] = []
        for cid, _, _, rank in rows:
            row = by_id.get(cid)
            if not row:
                continue
            score = 1.0 / (1.0 + float(rank if rank is not None else 1.0))
            meta = json.loads(row[4] or "{}")
            out.append(
                Chunk(
                    id=str(cid),
                    project_id=project_id,
                    type=str(row[1]),
                    text=str(row[2]),
                    snippet=str(row[3]),
                    score=score,
                    channel="keyword",
                    metadata=meta,
                )
            )
        return out

    def retrieve(
        self,
        project_id: str,
        query: str,
        filters: Dict[str, Any] | None,
        top_k: int,
    ) -> List[Chunk]:
        types = (filters or {}).get("types")
        chapter_no = (filters or {}).get("chapter_no")
        chapter_only_before = (filters or {}).get("chapter_only_before", True)
        chapter_no_max_for_chapter = None
        if chapter_no and chapter_only_before:
            chapter_no_max_for_chapter = int(chapter_no) - 1

        where: Dict[str, Any] = {}
        if types:
            where["type"] = {"$in": list(types)}
        if chapter_no_max_for_chapter is not None:
            # Only affects "chapter" type; implemented via rerank rule later for vector, and via WHERE for keyword.
            pass

        topK_v = int((filters or {}).get("top_k_v", max(6, top_k)))
        topK_kw = int((filters or {}).get("top_k_kw", max(6, top_k)))

        vector_hits = self._vector_retrieve(project_id=project_id, query=query, where=where, top_k=topK_v)

        with SessionLocal() as db:
            keyword_hits = self._keyword_retrieve(
                db,
                project_id=project_id,
                query=query,
                types=list(types) if types else None,
                chapter_no_max_for_chapter=chapter_no_max_for_chapter,
                top_k=topK_kw,
            )

        merged: Dict[str, Chunk] = {}
        for c in [*vector_hits, *keyword_hits]:
            if c.id not in merged:
                merged[c.id] = c
            else:
                merged[c.id].score = max(merged[c.id].score, c.score)
                merged[c.id].channel = "vector+keyword"

        candidates = list(merged.values())

        # Rerank
        reranker = self._get_reranker()
        texts = [c.text for c in candidates]
        try:
            rr_scores = reranker.rerank(query=query, texts=texts)
        except Exception:
            rr_scores = [c.score for c in candidates]

        type_weights = getattr(settings, "rag_type_weights", None) or {
            "style_guide": 1.8,
            "world": 1.5,
            "outline": 1.6,
            "characters": 1.7,
            "chapter_summary": 1.4,
            "facts": 1.5,
            "foreshadowing": 1.3,
            "chapter": 1.0,
        }
        target_chapter = chapter_no
        scored: List[Tuple[float, Chunk]] = []
        for c, rr in zip(candidates, rr_scores):
            meta = dict(c.metadata)
            meta.setdefault("type", c.type)
            meta.setdefault("chapter_no", meta.get("chapter_no"))
            base = float(rr)
            if isinstance(reranker, MockReranker):
                base = rule_score(
                    query=query,
                    text=c.text,
                    meta=meta,
                    base_score=c.score,
                    target_chapter=target_chapter,
                    type_weights=type_weights,
                )
            # enforce chapter <= target-1 if needed
            if chapter_no_max_for_chapter is not None and c.type == "chapter":
                try:
                    if meta.get("chapter_no") and int(meta["chapter_no"]) > chapter_no_max_for_chapter:
                        base = -1e9
                except Exception:
                    pass
            scored.append((base, c))

        scored.sort(key=lambda x: x[0], reverse=True)

        # Category quotas
        quotas = getattr(settings, "rag_type_quotas", None) or {
            "style_guide": 1,
            "world": 2,
            "outline": 2,
            "characters": 3,
            "chapter_summary": 3,
            "facts": 3,
            "foreshadowing": 2,
            "chapter": 4,
        }
        selected: List[Chunk] = []
        used: Dict[str, int] = {k: 0 for k in quotas.keys()}
        for score, c in scored:
            if score <= -1e8:
                continue
            t = c.type
            limit = quotas.get(t, 2)
            if used.get(t, 0) >= limit:
                continue
            c.score = float(score)
            c.channel = "rerank"
            selected.append(c)
            used[t] = used.get(t, 0) + 1
            if len(selected) >= top_k:
                break

        return selected

    def build_context(self, project_state: Dict[str, Any], retrieved_chunks: List[Chunk]) -> str:
        grouped: Dict[str, List[Chunk]] = {}
        for c in retrieved_chunks:
            grouped.setdefault(c.type, []).append(c)

        def section(title: str, chunks: List[Chunk], max_items: int | None = None) -> str:
            if not chunks:
                return ""
            items = chunks[: max_items or len(chunks)]
            body = "\n\n".join([f"- ({c.type}#{c.id} score={c.score:.3f}) {c.text.strip()}" for c in items])
            return f"## {title}\n{body}".strip()

        parts: List[str] = []
        parts.append(section("style_guide（规则/禁忌）", grouped.get("style_guide", []), 1))
        parts.append(section("outline（本章 beats / 目标）", grouped.get("outline", []), 2))
        parts.append(section("characters（主要角色要点）", grouped.get("characters", []), 3))
        parts.append(section("facts & foreshadowing（强相关）", [*(grouped.get("facts", []) or []), *(grouped.get("foreshadowing", []) or [])], 6))
        parts.append(section("relevant chapter summaries", grouped.get("chapter_summary", []), 3))
        parts.append(section("relevant chapter raw snippets", grouped.get("chapter", []), 4))

        return "\n\n".join([p for p in parts if p.strip()]).strip()

    def preview(self, *, project_id: str, query: str, chapter_no: int | None, top_k: int) -> RetrievalDebug:
        filters = {
            "types": [
                "style_guide",
                "world",
                "outline",
                "characters",
                "chapter_summary",
                "facts",
                "foreshadowing",
                "chapter",
            ],
            "chapter_no": chapter_no,
            "chapter_only_before": True,
            "top_k_v": int(getattr(settings, "rag_top_k_v", 10)),
            "top_k_kw": int(getattr(settings, "rag_top_k_kw", 10)),
        }
        # For preview, we want to expose intermediate channels too:
        vector_hits = self._vector_retrieve(project_id=project_id, query=query, where={}, top_k=filters["top_k_v"])
        with SessionLocal() as db:
            keyword_hits = self._keyword_retrieve(
                db,
                project_id=project_id,
                query=query,
                types=None,
                chapter_no_max_for_chapter=(chapter_no - 1) if chapter_no else None,
                top_k=filters["top_k_kw"],
            )
        final_selected = self.retrieve(project_id, query, filters, top_k)
        context_string = self.build_context({}, final_selected)
        merged = []
        seen = set()
        for c in [*vector_hits, *keyword_hits]:
            if c.id in seen:
                continue
            seen.add(c.id)
            merged.append(c)
        return RetrievalDebug(
            query=query,
            vector_results=vector_hits,
            keyword_results=keyword_hits,
            merged_candidates=merged,
            final_selected=final_selected,
            context_string=context_string,
        )

    def stats(self, project_id: str) -> Dict[str, Any]:
        with SessionLocal() as db:
            rows = db.execute(
                sql_text(
                    """
                    SELECT type, COUNT(1) as cnt, MAX(created_at) as last_ts
                    FROM rag_chunks
                    WHERE project_id = :p
                    GROUP BY type
                    """
                ),
                {"p": project_id},
            ).fetchall()
        return {r[0]: {"chunks": int(r[1]), "last_updated_at": r[2]} for r in rows}
