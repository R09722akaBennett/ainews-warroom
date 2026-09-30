#!/usr/bin/env bash
# 每日前沿實驗室動態：收集與分類；週一另外產出上週的實驗室週報。
# 由 bennett-hub cron 在 14:40 經 alert-wrap.sh 執行；週一含週報約 20 分鐘，
# 15:30 的 site-data.sh 會把結果匯出到網站。
set -euo pipefail
cd "$(dirname "$0")"
set -a
. "$HOME/infra/.env"
set +a
export PATH="$HOME/.local/bin:$PATH"
ARGS=()
[ "$(date +%u)" = "1" ] && ARGS+=(--classify)
exec uv run --no-sync python -m labs "${ARGS[@]}" "$@"
