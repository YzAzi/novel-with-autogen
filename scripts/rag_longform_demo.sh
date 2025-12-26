#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://localhost:8000}"

echo "== 1) Create project"
create_res="$(
  curl -sS "${API_BASE}/projects" \
    -H 'Content-Type: application/json' \
    -d '{
      "genre":"都市奇幻连载",
      "setting":"现代大都市中存在隐秘的“契约规则”，每次施法都要付出等价代价。主要舞台：旧城区、地铁环线、江湾码头。",
      "style":"第三人称有限视角，克制、悬疑，章末留钩子",
      "keywords":"契约, 代价, 地铁, 旧城, 追逐",
      "audience":"喜欢悬疑与设定推理的成年读者",
      "target_chapters": 12
    }'
)"
project_id="$(echo "$create_res" | python -c 'import json,sys; print(json.load(sys.stdin)["data"]["id"])')"
echo "project_id: $project_id"

echo
echo "== 2) Generate outline"
curl -sS "${API_BASE}/projects/${project_id}/outline" \
  -H 'Content-Type: application/json' \
  -d '{"theme":"代价与救赎","total_words":120000}' \
  | python -c 'import json,sys; obj=json.load(sys.stdin); print(obj["data"]["outline"][:260]); print("\n...")'

echo
echo "== 3) Generate characters"
curl -sS "${API_BASE}/projects/${project_id}/characters" \
  -H 'Content-Type: application/json' \
  -d '{"constraints":"至少3个主要角色；每个角色都有明确代价与隐瞒。"}' \
  | python -c 'import json,sys; obj=json.load(sys.stdin); print("characters_text preview:", obj["data"]["characters_text"][:180])'

echo
echo "== 4) Expand chapter 1 (RAG + critic + writeback)"
curl -sS "${API_BASE}/projects/${project_id}/chapters/1/expand" \
  -H 'Content-Type: application/json' \
  -d '{"instruction":"从地铁里一次异常停站开场，主角第一次触发契约规则，结尾留悬念。","target_words":900}' \
  | python - <<'PY'
import json,sys
obj=json.load(sys.stdin)
print("revised:", obj["data"].get("revised"))
print("critic_issues:", len(obj["data"].get("critic_issues", [])))
print("text preview:", obj["data"]["text"][:260])
PY

echo
echo "== 5) Expand chapter 2 (forces retrieval from chapter 1 summary/facts/foreshadowing)"
curl -sS "${API_BASE}/projects/${project_id}/chapters/2/expand" \
  -H 'Content-Type: application/json' \
  -d '{"instruction":"承接上一章伏笔，解释异常停站的线索，但不要完全揭底；加强人物动机一致性。","target_words":900}' \
  | python - <<'PY'
import json,sys
obj=json.load(sys.stdin)
print("critic_issues:", len(obj["data"].get("critic_issues", [])))
print("context_used preview:", obj["data"].get("context_used","")[:200])
PY

echo
echo "== 6) RAG preview for chapter 3"
curl -sS "${API_BASE}/projects/${project_id}/rag/preview?chapter=3&query=承接伏笔%20人物一致性%20世界观硬设定&top_k=18" \
  | python - <<'PY'
import json,sys
obj=json.load(sys.stdin)["data"]
print("final_selected:", len(obj["final_selected"]))
print("context_string preview:", obj["context_string"][:260])
PY

echo
echo "Open UI:"
echo "  http://localhost:3000/projects/${project_id}"
echo "  http://localhost:3000/projects/${project_id}/chapters/2"

