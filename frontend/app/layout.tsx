import "./globals.css";

export const metadata = {
  title: "Novel Multi-Agent Studio",
  description: "多智能体协作写小说 - Outline/Character/Writer"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <main>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 14 }}>
            <a href="/" style={{ fontSize: 18, fontWeight: 700 }}>
              Novel Multi-Agent Studio
            </a>
            <span style={{ color: "var(--muted)", fontSize: 12 }}>Mock LLM 可运行；配置 .env 可接入真实 LLM</span>
          </div>
          {children}
        </main>
      </body>
    </html>
  );
}

