from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class ChunkedText:
    text: str
    snippet: str


def _split_paragraphs(text: str) -> List[str]:
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not cleaned:
        return []
    # Prefer scene/paragraph boundaries.
    parts = [p.strip() for p in cleaned.split("\n\n") if p.strip()]
    return parts


def chunk_novel_text(
    text: str,
    *,
    max_chars: int = 1400,
    overlap_ratio: float = 0.2,
    snippet_chars: int = 240,
) -> List[ChunkedText]:
    paragraphs = _split_paragraphs(text)
    if not paragraphs:
        return []

    chunks: List[str] = []
    i = 0
    while i < len(paragraphs):
        buf: List[str] = []
        total = 0
        while i < len(paragraphs) and (total + len(paragraphs[i]) + (2 if buf else 0)) <= max_chars:
            buf.append(paragraphs[i])
            total += len(paragraphs[i]) + (2 if buf else 0)
            i += 1

        if not buf:  # single huge paragraph, hard cut
            p = paragraphs[i]
            buf = [p[:max_chars]]
            paragraphs[i] = p[max_chars:]
            if not paragraphs[i].strip():
                i += 1

        chunk_text = "\n\n".join(buf).strip()
        chunks.append(chunk_text)

        # Overlap by reusing tail paragraphs.
        if i < len(paragraphs) and overlap_ratio > 0:
            overlap_target = int(max_chars * overlap_ratio)
            tail: List[str] = []
            tail_len = 0
            for p in reversed(buf):
                if tail_len >= overlap_target:
                    break
                tail.insert(0, p)
                tail_len += len(p) + 2
            if tail:
                paragraphs.insert(i, "\n\n".join(tail))

    return [ChunkedText(text=c, snippet=(c[:snippet_chars] + ("…" if len(c) > snippet_chars else ""))) for c in chunks]

