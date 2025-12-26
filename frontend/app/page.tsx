"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { api } from "@/lib/api";
import { AgentLogs } from "@/components/AgentLogs";
import type { AgentLog } from "@/lib/types";

export default function HomePage() {
  const router = useRouter();
  const [genre, setGenre] = useState("科幻");
  const [style, setStyle] = useState("简洁、节奏快");
  const [keywords, setKeywords] = useState("太空站, 失忆, 阴谋");
  const [audience, setAudience] = useState("喜欢硬科幻与悬疑的成年读者");
  const [setting, setSetting] = useState("近未来轨道太空站，资源紧缺，政治势力角力。");
  const [targetChapters, setTargetChapters] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [logs, setLogs] = useState<AgentLog[]>([]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await api.createProject({
        genre,
        setting,
        style,
        keywords,
        audience,
        target_chapters: targetChapters
      });
      setLogs(res.agent_logs || []);
      router.push(`/projects/${res.data.id}`);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div className="card">
        <div style={{ fontWeight: 700, marginBottom: 10 }}>创建写作项目</div>
        <form onSubmit={onSubmit} style={{ display: "grid", gap: 10 }}>
          <div className="row">
            <div style={{ flex: 1, minWidth: 240 }}>
              <label>题材</label>
              <input value={genre} onChange={(e) => setGenre(e.target.value)} />
            </div>
            <div style={{ flex: 1, minWidth: 240 }}>
              <label>风格</label>
              <input value={style} onChange={(e) => setStyle(e.target.value)} />
            </div>
          </div>
          <div className="row">
            <div style={{ flex: 1, minWidth: 240 }}>
              <label>关键词</label>
              <input value={keywords} onChange={(e) => setKeywords(e.target.value)} />
            </div>
            <div style={{ width: 160 }}>
              <label>目标章节数</label>
              <input
                type="number"
                min={1}
                max={200}
                value={targetChapters}
                onChange={(e) => setTargetChapters(Number(e.target.value))}
              />
            </div>
          </div>
          <div className="row">
            <div style={{ flex: 1, minWidth: 240 }}>
              <label>读者画像</label>
              <input value={audience} onChange={(e) => setAudience(e.target.value)} />
            </div>
          </div>
          <div>
            <label>设定</label>
            <textarea value={setting} onChange={(e) => setSetting(e.target.value)} />
          </div>
          <div className="row" style={{ alignItems: "center" }}>
            <button type="submit" disabled={loading}>
              {loading ? "创建中..." : "创建项目"}
            </button>
            {error ? <div style={{ color: "#ff9aa2" }}>{error}</div> : null}
          </div>
        </form>
      </div>

      <AgentLogs logs={logs} />
    </div>
  );
}

