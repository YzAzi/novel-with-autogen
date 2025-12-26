# Novel Multi-Agent Studio（多智能体协作写小说）

一个最小可运行的全栈闭环：FastAPI + SQLite +（可选）AutoGen + Next.js，用于按流程协作写小说：大纲 → 角色 → 扩写章节，并把每一步的中间产物与 agent 日志落库，便于前端刷新展示。

本项目已增强长篇连载一致性：引入 Hybrid RAG（ChromaDB + SQLite FTS5）+ 写后记忆提炼（summary/facts/foreshadowing）+ ConsistencyCriticAgent 审查。

## 功能概览

- 多智能体：`OutlineAgent` / `CharacterAgent` / `WriterAgent`
- `Coordinator` 负责调度与落库（outline / characters / chapters / logs）
- RAG：分层知识索引 + 扩写前检索 + 重排序 + 可视化预览
- 写后链路：chapter_summary / facts / foreshadowing 自动提炼并入库索引
- `ConsistencyCriticAgent`：一致性审查（可选 AUTO_REVISE 自动修订）
- 后端 API：
  - `POST /projects`
  - `POST /projects/{id}/outline`
  - `POST /projects/{id}/characters`
  - `POST /projects/{id}/chapters/{n}/expand`
  - `GET /projects/{id}`
  - `GET /projects/{id}/rag/stats`
  - `GET /projects/{id}/rag/preview?chapter={n}&query={q}&top_k={k}`
- 默认 `MOCK_LLM=1`：无需任何密钥即可跑通流程；配置 `.env` 可接入真实 LLM（通过 AutoGen）

## 1) 环境变量

复制 `.env.example` 为 `.env`：

```bash
cp .env.example .env
```

常用配置：

- `MOCK_LLM=1`：使用 mock 输出（默认建议）
- `MOCK_LLM=0` + `LLM_API_KEY` + `LLM_MODEL`（可选 `LLM_BASE_URL`）：启用真实 LLM（AutoGen）
- `DB_PATH`：SQLite 文件路径（Docker 下默认 `/data/app.db`）
- `NEXT_PUBLIC_API_BASE`：前端请求后端的地址（默认 `http://localhost:8000`）
- RAG（默认全 mock 可运行）：
  - `CHROMA_PERSIST_DIR`：ChromaDB 持久化目录（默认 `data/chroma` -> `backend/data/chroma/`）
  - `EMBEDDINGS_PROVIDER=local_bge_m3|mock`（失败自动降级 mock）
  - `RERANK_PROVIDER=local_bge|mock`（失败自动降级 mock）
  - `CRITIC_PROVIDER=llm|mock`，`AUTO_REVISE=true|false`

注意：不要把任何真实密钥写进仓库。

## 2) RAG 分层（用于一致性）

索引类型（`type`）：

- `style_guide`：写作规则/禁忌/视角
- `world`：世界观硬设定
- `outline`：卷/章大纲 beats
- `characters`：角色圣经（JSON + 可读文本）
- `chapter`：正文 chunk
- `chapter_summary`：章摘要（写后自动生成）
- `facts`：新增事实/状态变化（写后自动提炼）
- `foreshadowing`：伏笔（写后自动提炼）

扩写时强制流程：`retrieve -> build_context -> Writer -> 写后提炼 -> Critic`。前端章节页可查看检索到的 chunks、最终 context、critic issues。

## 本地模型说明（可选）

本仓库默认 `EMBEDDINGS_PROVIDER=mock`、`RERANK_PROVIDER=mock`、`CRITIC_PROVIDER=mock`，无需下载任何模型即可运行。

若要启用本地 bge-m3 embeddings / bge-reranker：

- 设置 `EMBEDDINGS_PROVIDER=local_bge_m3`、`RERANK_PROVIDER=local_bge`
- `BGE_M3_MODEL_NAME` / `BGE_RERANK_MODEL_NAME` 支持“模型名”或“本地路径”
- 完全离线推荐：
  - 把离线模型放在仓库根目录 `./model/bge-m3` 与 `./model/bge-reranker-v2-m3`
  - `.env` 中设置 `BGE_M3_MODEL_NAME=model/bge-m3`、`BGE_RERANK_MODEL_NAME=model/bge-reranker-v2-m3`
  - 额外设置 `HF_HUB_OFFLINE=1`、`TRANSFORMERS_OFFLINE=1` 防止触网

Docker Compose 已内置挂载：`./model -> /models:ro`，并默认使用 `/models/bge-m3`、`/models/bge-reranker-v2-m3`。

## 3) 一键启动（推荐：Docker Compose）

```bash
cp .env.example .env
docker compose up --build
```

- 前端：http://localhost:3000
- 后端：http://localhost:8000/healthz

如果你把 `MOCK_LLM=0` 打开了但后端报 “AutoGen is not installed / ext OpenAI client not available”，请重新构建镜像以安装新依赖：

```bash
docker compose build --no-cache backend
docker compose up
```

SQLite 数据会落在 `./data/app.db`（通过 volume 挂载）。

## 4) 本地启动（不使用 Docker）

后端：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
mkdir -p data
export DB_PATH="$(pwd)/data/app.db"
export BACKEND_CORS_ORIGINS="http://localhost:3000"
cd backend
uvicorn app.main:app --reload --port 8000
```

前端：

```bash
cd frontend
npm install
export NEXT_PUBLIC_API_BASE="http://localhost:8000"
npm run dev
```

## 5) curl 演示完整流程

```bash
bash scripts/seed_demo.sh
```

可用 `API_BASE` 指定后端地址：

```bash
API_BASE="http://localhost:8000" bash scripts/seed_demo.sh
```

RAG 长篇一致性演示（包含第 1、2 章扩写与 rag/preview）：

```bash
bash scripts/rag_longform_demo.sh
```

## 6) 简单检查

- 后端：`python -m compileall backend/app`
- 前端：`cd frontend && npm run build`
