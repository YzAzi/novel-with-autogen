"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { AgentLogs } from "@/components/AgentLogs";
import { api } from "@/lib/api";
import type { AgentLog, ProjectState, RagStats } from "@/lib/types";

export function ProjectClient({ projectId }: { projectId: string }) {
  const [project, setProject] = useState<ProjectState | null>(null);
  const [logs, setLogs] = useState<AgentLog[]>([]);
  const [tab, setTab] = useState<"main" | "kb">("main");
  const [ragStats, setRagStats] = useState<RagStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const chapterNumbers = useMemo(() => {
    const keys = Object.keys(project?.chapters || {});
    return keys
      .map((k) => Number(k))
      .filter((n) => Number.isFinite(n))
      .sort((a, b) => a - b);
  }, [project]);

  async function refresh() {
    const res = await api.getProject(projectId);
    setProject(res.data);
    setLogs(res.agent_logs || []);
  }

  useEffect(() => {
    refresh().catch((e) => setError(String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function runOutline() {
    setBusy("outline");
    setError(null);
    try {
      const res = await api.generateOutline(projectId, { theme: "", total_words: 80000 });
      setProject(res.data);
      setLogs(res.agent_logs || []);
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  }

  async function runCharacters() {
    setBusy("characters");
    setError(null);
    try {
      const res = await api.generateCharacters(projectId, { constraints: "" });
      setProject(res.data);
      setLogs(res.agent_logs || []);
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  }

  async function loadRagStats() {
    setBusy("rag_stats");
    setError(null);
    try {
      const res = await api.ragStats(projectId);
      setRagStats(res.data);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  }

  if (!project) {
    return (
      <div className="card">
        <div style={{ color: "var(--muted)" }}>加载中...</div>
        {error ? <div style={{ color: "#ff9aa2", marginTop: 10 }}>{error}</div> : null}
      </div>
    );
  }

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
          <div>
            <div style={{ fontWeight: 700 }}>项目：{project.id}</div>
            <div style={{ color: "var(--muted)", marginTop: 6 }}>
              {project.genre} · {project.style} · 目标 {project.target_chapters} 章
            </div>
          </div>
          <div className="row">
            <button onClick={runOutline} disabled={busy !== null}>
              {busy === "outline" ? "生成中..." : "生成/更新大纲"}
            </button>
            <button onClick={runCharacters} disabled={busy !== null}>
              {busy === "characters" ? "生成中..." : "生成/更新角色"}
            </button>
          </div>
        </div>
        {error ? <div style={{ color: "#ff9aa2", marginTop: 10 }}>{error}</div> : null}
      </div>

      <div className="row">
        <button onClick={() => setTab("main")} disabled={tab === "main"}>
          项目内容
        </button>
        <button
          onClick={() => {
            setTab("kb");
            if (!ragStats) loadRagStats();
          }}
          disabled={tab === "kb" || busy !== null}
        >
          知识库
        </button>
        {tab === "kb" ? (
          <button onClick={loadRagStats} disabled={busy !== null}>
            {busy === "rag_stats" ? "刷新中..." : "刷新知识库统计"}
          </button>
        ) : null}
      </div>

      {tab === "kb" ? (
        <div className="card">
          <div style={{ fontWeight: 700, marginBottom: 10 }}>知识库统计（RAG chunks）</div>
          <pre>{JSON.stringify(ragStats || {}, null, 2)}</pre>
          <div style={{ color: "var(--muted)", fontSize: 12, marginTop: 10 }}>
            提示：每次生成/扩写都会自动入库索引；扩写会先检索再写。
          </div>
        </div>
      ) : (
        <>
          <div className="card">
            <div style={{ fontWeight: 700, marginBottom: 10 }}>大纲</div>
            <pre>{project.outline || "（空）"}</pre>
          </div>

          <div className="card">
            <div style={{ fontWeight: 700, marginBottom: 10 }}>角色卡（JSON）</div>
            <pre>{JSON.stringify(project.characters || {}, null, 2)}</pre>
            {project.characters_text ? (
              <>
                <div style={{ fontWeight: 700, margin: "14px 0 10px" }}>角色总结（可读文本）</div>
                <pre>{project.characters_text}</pre>
              </>
            ) : null}
          </div>
        </>
      )}

      <div className="card">
        <div style={{ fontWeight: 700, marginBottom: 10 }}>章节</div>
        <div className="row">
          {chapterNumbers.length ? (
            chapterNumbers.map((n) => (
              <Link key={n} href={`/projects/${projectId}/chapters/${n}`} className="card" style={{ padding: 10 }}>
                第 {n} 章（已生成）
              </Link>
            ))
          ) : (
            <div style={{ color: "var(--muted)" }}>暂无章节，先到任意章节页扩写。</div>
          )}
          <Link href={`/projects/${projectId}/chapters/1`} className="card" style={{ padding: 10 }}>
            去扩写第 1 章 →
          </Link>
        </div>
      </div>

      <AgentLogs logs={logs} />
    </div>
  );
}

