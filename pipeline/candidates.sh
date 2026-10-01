#!/usr/bin/env bash
# 每日廣來源候選新聞收集與 Jev 打分。由 bennett-hub cron 在 16:05 經 alert-wrap.sh 執行，
# 16:30 的 wiki 日報讀當天的 pipeline/data/candidates/<date>.json，取重要性 0.75 以上前 15 則當補充材料。
# 2026-10-01 結束影子模式；去重比對的是前三天的日報。
set -euo pipefail
cd "$(dirname "$0")"
set -a
. "$HOME/infra/.env"
set +a
export PATH="$HOME/.local/bin:$PATH"
exec uv run --no-sync python -m candidates "$@"
