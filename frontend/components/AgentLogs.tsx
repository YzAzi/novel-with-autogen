"use client";

import type { AgentLog } from "@/lib/types";

export function AgentLogs({ logs }: { logs: AgentLog[] }) {
  if (!logs?.length) return <div style={{ color: "var(--muted)" }}>暂无日志</div>;
  return (
    <div className="card">
      <div style={{ fontWeight: 700, marginBottom: 10 }}>Agent 日志</div>
      <div style={{ display: "grid", gap: 10 }}>
        {logs
          .slice()
          .reverse()
          .map((l, idx) => (
            <div key={idx} style={{ border: "1px solid var(--border)", borderRadius: 10, padding: 10 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
                <div>
                  <span style={{ fontWeight: 700 }}>{l.agent}</span>
                  <span style={{ color: "var(--muted)", marginLeft: 8, fontSize: 12 }}>{l.action}</span>
                </div>
                {l.ts ? <div style={{ color: "var(--muted)", fontSize: 12 }}>{new Date(l.ts).toLocaleString()}</div> : null}
              </div>
              <div style={{ marginTop: 6 }}>{l.summary}</div>
              {l.output_preview ? (
                <pre style={{ marginTop: 8, maxHeight: 260, overflow: "auto" }}>{l.output_preview}</pre>
              ) : null}
            </div>
          ))}
      </div>
    </div>
  );
}

