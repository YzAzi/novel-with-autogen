#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://localhost:8000}"

echo "== 1) Create project"
create_res="$(
  curl -sS "${API_BASE}/projects" \
    -H 'Content-Type: application/json' \
    -d '{
      "genre":"科幻悬疑",
      "setting":"近未来轨道太空站，资源紧缺，权力斗争暗流涌动。",
      "style":"简洁、节奏快、带一点冷幽默",
      "keywords":"失忆, 太空站, 阴谋, 赎罪",
      "audience":"喜欢硬科幻与悬疑的成年读者",
      "target_chapters": 10
    }'
)"
echo "$create_res" | python - <<'PY'
import json,sys
obj=json.load(sys.stdin)
print("project_id:", obj["data"]["id"])
PY
project_id="$(echo "$create_res" | python -c 'import json,sys; print(json.load(sys.stdin)["data"]["id"])')"

echo
echo "== 2) Generate outline"
curl -sS "${API_BASE}/projects/${project_id}/outline" \
  -H 'Content-Type: application/json' \
  -d '{"theme":"记忆与身份的代价","total_words":80000}' \
  | python -c 'import json,sys; obj=json.load(sys.stdin); print(obj["data"]["outline"][:400]); print("\n...")'

echo
echo "== 3) Generate characters"
curl -sS "${API_BASE}/projects/${project_id}/characters" \
  -H 'Content-Type: application/json' \
  -d '{"constraints":"主角必须在第1章做出一个道德灰度选择；反派动机要自洽。"}' \
  | python -c 'import json,sys; obj=json.load(sys.stdin); print("characters keys:", list(obj["data"]["characters"].keys())[:10])'

echo
echo "== 4) Expand chapter 1"
curl -sS "${API_BASE}/projects/${project_id}/chapters/1/expand" \
  -H 'Content-Type: application/json' \
  -d '{"instruction":"从一次紧急事故切入，展现主角的失忆与隐藏能力，结尾埋伏笔。","target_words":1200}' \
  | python -c 'import json,sys; obj=json.load(sys.stdin); print(obj["data"]["text"][:800]); print("\n...")'

echo
echo "Done. Open the UI: http://localhost:3000/projects/${project_id}"

