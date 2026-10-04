#!/usr/bin/env bash
# 每日更新網站資料並 push：wiki 日報 → reports.json、實驗室動態 → labs.json、電子報深讀 → reading.json、X / Jev / 訂閱費用 → costs.json、podcast 摘要與逐字稿 → podcasts.json，加上 arena.ai 排行、alphaxiv 論文、MCP Market，
# Vercel 會在 main 被 push 時自動部署。平常由 18:00 的 wiki daily-news.sh 在快報寫完後呼叫，
# cron 21:30 再跑一次當備援（日報最晚等 AINews 到 21:00）。
#
# 用法：site-data.sh [--push]
#   沒有 --push 只更新 JSON 並顯示差異(dry-run，不 commit 也不 push)。
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="$HOME/.local/bin:$PATH"
# The exporters translate new text with Gemini; without the key they export
# the native language only (local dry runs).
if [ -f "$HOME/infra/.env" ]; then
  set -a
  . "$HOME/infra/.env"
  set +a
fi
PUSH=0
[ "${1:-}" = "--push" ] && PUSH=1
FILES=(src/data/reports.json src/data/labs.json src/data/summaries.json src/data/leaderboard.json src/data/papers.json src/data/mcpmarket.json src/data/reading.json src/data/costs.json src/data/podcasts.json src/data/podcasts)

cd "$REPO"
if [ "$PUSH" = 1 ]; then
  git pull -q --rebase --autostash origin main
fi

cd "$REPO/pipeline"
set +e
uv run --no-sync python -m export.from_wiki
EXPORT_RC=$?
uv run --no-sync python -m export.labs || EXPORT_RC=$?
uv run --no-sync python -m export.reading || EXPORT_RC=$?
uv run --no-sync python -m export.costs || EXPORT_RC=$?
uv run --no-sync python -m export.podcasts || EXPORT_RC=$?
uv run --no-sync python -m leaderboard
SCRAPE_RC=$?
set -e

cd "$REPO"
# Every exporter rewrites its "updatedAt", so a plain diff never comes back
# clean; a day whose data did not change must not commit and redeploy.
if git diff -I '"updatedAt"' --quiet -- "${FILES[@]}"; then
  echo "site-data: no changes"
elif [ "$PUSH" = 0 ]; then
  echo "[dry-run] Will commit and push:"
  git --no-pager diff --stat -- "${FILES[@]}"
else
  git add -- "${FILES[@]}"
  git commit -q -m "chore: 更新日報、實驗室動態、排行榜與論文資料 $(date +%F)"
  git push -q origin main
  echo "site-data: pushed $(git rev-parse --short HEAD)"
fi

# 任一步失敗時沿用舊資料、其餘照樣 push，但這裡回非 0 讓 alert-wrap 告警。
[ "$EXPORT_RC" -ne 0 ] && exit "$EXPORT_RC"
exit "$SCRAPE_RC"
