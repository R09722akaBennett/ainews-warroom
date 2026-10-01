#!/usr/bin/env bash
# 每日收集 Latent Space podcast（全文、逐字稿、中文結構化摘要）→ pipeline/data/podcasts/ 與 knowledge DB。
# 由 bennett-hub cron 在 17:40 經 alert-wrap.sh 執行；18:00 日報 job 觸發的 site-data.sh 會匯出到網站。
# 已收過的集數不會重抓也不會重新摘要；用 --force <slug> 重做一集。
set -euo pipefail
cd "$(dirname "$0")"
set -a
. "$HOME/infra/.env"
set +a
export PATH="$HOME/.local/bin:$PATH"
exec uv run --no-sync python -m podcasts --live "$@"
