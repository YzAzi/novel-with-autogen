"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AgentLogs } from "@/components/AgentLogs";
import { api } from "@/lib/api";
import type { AgentLog, CriticIssue, ExpandChapterResult, ProjectState, RagPreview, RetrievedChunkSummary } from "@/lib/types";

export default function ChapterPage({ params }: { params: { id: string; n: string } }) {
  const projectId = params.id;
  const chapterNumber = Number(params.n);
  const [project, setProject] = useState<ProjectState | null>(null);
  const [logs, setLogs] = useState<AgentLog[]>([]);
  const [instruction, setInstruction] = useState("加强冲突与悬念，结尾埋一个反转伏笔。");
  const [targetWords, setTargetWords] = useState(2500);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [text, setText] = useState<string>("");
  const [previewOn, setPreviewOn] = useState(false);
  const [preview, setPreview] = useState<RagPreview | null>(null);
  const [expandResult, setExpandResult] = useState<ExpandChapterResult | null>(null);

  async function refresh() {
    const res = await api.getProject(projectId);
    setProject(res.data);
    setLogs(res.agent_logs || []);
    const existing = res.data.chapters?.[String(chapterNumber)];
    if (existing) setText(existing);
  }

  useEffect(() => {
    refresh().catch((e) => setError(String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, chapterNumber]);

  async function runExpand() {
    setBusy(true);
    setError(null);
    try {
      const res = await api.expandChapter(projectId, chapterNumber, { instruction, target_words: targetWords });
      setText(res.data.text);
      setExpandResult(res.data);
      setLogs(res.agent_logs || []);
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function loadPreview() {
    setBusy(true);
    setError(null);
    try {
      const res = await api.ragPreview(projectId, { chapter: chapterNumber, query: instruction, top_k: 18 });
      setPreview(res.data);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  function ChunkList({ title, chunks }: { title: string; chunks: RetrievedChunkSummary[] }) {
    return (
      <div className="card" style={{ padding: 10 }}>
        <div style={{ fontWeight: 700, marginBottom: 8 }}>{title}</div>
        {chunks?.length ? (
          <div style={{ display: "grid", gap: 8 }}>
            {chunks.map((c) => (
              <div key={c.id} style={{ border: "1px solid var(--border)", borderRadius: 10, padding: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
                  <div>
                    <span style={{ fontWeight: 700 }}>{c.type}</span>
                    <span style={{ color: "var(--muted)", marginLeft: 8, fontSize: 12 }}>
                      {c.channel} score={c.score.toFixed(3)}
                    </span>
                  </div>
                  <div style={{ color: "var(--muted)", fontSize: 12 }}>
                    {c.chapter_no ? `chapter=${c.chapter_no}` : "chapter=-"} {c.source_id ? `source=${c.source_id}` : ""}
                  </div>
                </div>
                <pre style={{ marginTop: 8, maxHeight: 180, overflow: "auto" }}>{c.snippet}</pre>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ color: "var(--muted)" }}>（空）</div>
        )}
      </div>
    );
  }

  function CriticPanel({ issues }: { issues: CriticIssue[] }) {
    return (
      <div className="card">
        <div style={{ fontWeight: 700, marginBottom: 10 }}>一致性审查（Critic）</div>
        {issues?.length ? (
          <div style={{ display: "grid", gap: 10 }}>
            {issues.map((it, idx) => (
              <div key={idx} style={{ border: "1px solid var(--border)", borderRadius: 10, padding: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
                  <div>
                    <span style={{ fontWeight: 700 }}>{it.issue_type}</span>
                    <span style={{ color: "var(--muted)", marginLeft: 8, fontSize: 12 }}>{it.severity}</span>
                  </div>
                </div>
                <div style={{ marginTop: 6 }}>{it.conflict}</div>
                {it.evidence_snippet ? <pre style={{ marginTop: 8 }}>{it.evidence_snippet}</pre> : null}
              </div>
            ))}
          </div>
        ) : (
          <div style={{ color: "var(--muted)" }}>暂无问题（或未启用 critic）。</div>
        )}
        {expandResult?.revised ? <div style={{ color: "var(--accent)", marginTop: 10 }}>已自动修订（AUTO_REVISE）</div> : null}
      </div>
    );
  }

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
          <div>
            <div style={{ fontWeight: 700 }}>第 {chapterNumber} 章</div>
            <div style={{ color: "var(--muted)", marginTop: 6 }}>
              项目：<Link href={`/projects/${projectId}`}>{projectId}</Link>
            </div>
          </div>
          <div className="row" style={{ alignItems: "center" }}>
            <Link href={`/projects/${projectId}`} style={{ color: "var(--muted)" }}>
              ← 返回项目
            </Link>
          </div>
        </div>
      </div>

      <div className="card">
        <div style={{ fontWeight: 700, marginBottom: 10 }}>扩写参数</div>
        <div style={{ display: "grid", gap: 10 }}>
          <div className="row">
            <div style={{ flex: 1, minWidth: 240 }}>
              <label>扩写指令</label>
              <input value={instruction} onChange={(e) => setInstruction(e.target.value)} />
            </div>
            <div style={{ width: 180 }}>
              <label>目标字数</label>
              <input
                type="number"
                min={200}
                max={20000}
                value={targetWords}
                onChange={(e) => setTargetWords(Number(e.target.value))}
              />
            </div>
          </div>
          <div className="row" style={{ alignItems: "center" }}>
            <button onClick={runExpand} disabled={busy}>
              {busy ? "扩写中..." : "扩写本章"}
            </button>
            <button
              onClick={() => {
                const next = !previewOn;
                setPreviewOn(next);
                if (next) loadPreview();
              }}
              disabled={busy}
            >
              {previewOn ? "关闭检索预览" : "检索预览"}
            </button>
            {error ? <div style={{ color: "#ff9aa2" }}>{error}</div> : null}
          </div>
        </div>
      </div>

      {previewOn ? (
        <div style={{ display: "grid", gap: 12 }}>
          <div className="card">
            <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
              <div style={{ fontWeight: 700 }}>RAG 检索预览</div>
              <button onClick={loadPreview} disabled={busy}>
                {busy ? "加载中..." : "刷新预览"}
              </button>
            </div>
            <div style={{ color: "var(--muted)", fontSize: 12, marginTop: 8 }}>
              展示 vector/keyword 召回、合并候选与最终选用 chunks，以及最终 context 模板（可折叠查看）。
            </div>
          </div>

          {preview ? (
            <>
              <div className="card">
                <div style={{ fontWeight: 700, marginBottom: 10 }}>最终 Context（模板）</div>
                <pre style={{ maxHeight: 420, overflow: "auto" }}>{preview.context_string}</pre>
              </div>
              <div className="row">
                <div style={{ flex: 1, minWidth: 320 }}>
                  <ChunkList title="Final selected（用于写作）" chunks={preview.final_selected} />
                </div>
                <div style={{ flex: 1, minWidth: 320 }}>
                  <ChunkList title="Vector recall" chunks={preview.vector_results} />
                </div>
                <div style={{ flex: 1, minWidth: 320 }}>
                  <ChunkList title="Keyword recall" chunks={preview.keyword_results} />
                </div>
                <div style={{ flex: 1, minWidth: 320 }}>
                  <ChunkList title="Merged candidates" chunks={preview.merged_candidates} />
                </div>
              </div>
            </>
          ) : (
            <div className="card" style={{ color: "var(--muted)" }}>
              加载中...
            </div>
          )}
        </div>
      ) : null}

      {expandResult ? (
        <>
          <div className="card">
            <div style={{ fontWeight: 700, marginBottom: 10 }}>本次写作使用的 Context（截断）</div>
            <pre style={{ maxHeight: 420, overflow: "auto" }}>{expandResult.context_used}</pre>
          </div>
          <ChunkList title="本次检索到的来源（chunks）" chunks={expandResult.retrieved_context_sources} />
          <CriticPanel issues={expandResult.critic_issues} />
        </>
      ) : null}

      <div className="card">
        <div style={{ fontWeight: 700, marginBottom: 10 }}>正文</div>
        <pre>{text || "（空）"}</pre>
      </div>

      <AgentLogs logs={logs} />
    </div>
  );
}
