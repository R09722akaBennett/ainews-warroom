#!/usr/bin/env bash
# 每日廣來源候選新聞收集與 Jev 打分（影子模式，不影響日報）。
# 由 bennett-hub cron 在 15:15 經 alert-wrap.sh 執行，排在 14:30 日報之後，
# 才有當天日報實際引用的項目可以拿來校準門檻。
set -euo pipefail
cd "$(dirname "$0")"
set -a
. "$HOME/infra/.env"
set +a
export PATH="$HOME/.local/bin:$PATH"
exec uv run --no-sync python -m candidates "$@"
