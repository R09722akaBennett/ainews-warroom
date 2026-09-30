#!/usr/bin/env bash
# 每日更新網站的外部資料(arena.ai 排行、alphaxiv 論文、MCP Market)並 push，
# Vercel 會在 main 被 push 時自動部署。由 bennett-hub cron 經 alert-wrap.sh 執行。
#
# 用法：site-data.sh [--push]
#   沒有 --push 只更新 JSON 並顯示差異(dry-run，不 commit 也不 push)。
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="$HOME/.local/bin:$PATH"
PUSH=0
[ "${1:-}" = "--push" ] && PUSH=1
FILES=(src/data/leaderboard.json src/data/papers.json src/data/mcpmarket.json)

cd "$REPO"
if [ "$PUSH" = 1 ]; then
  git pull -q --rebase --autostash origin main
fi

cd "$REPO/pipeline"
set +e
uv run --no-sync python -m leaderboard
SCRAPE_RC=$?
set -e

cd "$REPO"
if git diff --quiet -- "${FILES[@]}"; then
  echo "site-data: no changes"
elif [ "$PUSH" = 0 ]; then
  echo "[dry-run] Will commit and push:"
  git --no-pager diff --stat -- "${FILES[@]}"
else
  git add -- "${FILES[@]}"
  git commit -q -m "chore: 更新排行榜與論文資料 $(date +%F)"
  git push -q origin main
  echo "site-data: pushed $(git rev-parse --short HEAD)"
fi

# 爬蟲任一失敗時沿用舊資料，但這裡回非 0 讓 alert-wrap 告警。
exit "$SCRAPE_RC"
