#!/bin/bash
# Daily AI War Room pipeline — runs on Mac Studio via crontab
#
# Setup:
#   crontab -e
#   0 16 * * * /Users/kdanmobile/ainews-warroom/pipeline/daily.sh >> /Users/kdanmobile/ainews-warroom/pipeline/logs/daily.log 2>&1
#
# This runs at 16:00 (4 PM) Taiwan time every day.

set -euo pipefail

REPO_DIR="/Users/kdanmobile/ainews-warroom"
PIPELINE_DIR="$REPO_DIR/pipeline"
LOG_DIR="$PIPELINE_DIR/logs"

# Ensure uv and other tools are on PATH (cron has minimal PATH)
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/usr/local/bin:/opt/homebrew/bin:$PATH"

mkdir -p "$LOG_DIR"

echo ""
echo "=========================================="
echo "AI War Room — $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

cd "$PIPELINE_DIR"

# Load environment (set -a exports all vars for child processes)
set -a
source .env 2>/dev/null || true
set +a

# Step 1: Collect news + generate report
echo "[1/7] Running agent..."
uv run python -m agent

# Step 2: Collect + classify competitor news (daily)
echo "[2/7] Collecting & classifying competitor news..."
uv run python -m competitor

# Step 3: Auto-compress (weekly on Mon, monthly on 1st, quarterly on quarter start)
# On Mondays, also generate competitor weekly report
echo "[3/7] Running compress..."
uv run python -m compress auto
if [ "$(date +%u)" = "1" ]; then
    echo "  Monday — generating competitor weekly report..."
    uv run python -m competitor --classify
fi

# Step 3.5: IDP Community RSS + LLM translation
echo "[3.5/7] Fetching IDP Community RSS..."
uv run python -m idp || echo "WARNING: IDP fetch failed (exit $?), continuing..."

# Step 3: Export DB → JSON for website
echo "[4/7] Exporting site data..."
uv run python -m export

# Step 4: Fetch Arena AI leaderboard
echo "[5/7] Fetching leaderboard..."
uv run python -m leaderboard

# Step 5: Mattermost notification disabled
echo "[6/7] Mattermost notification disabled; skipping."

# Step 6: Push to git → triggers Vercel deploy
echo "[7/7] Pushing to git..."
cd "$REPO_DIR"
git add src/data/reports.json src/data/sources.json src/data/summaries.json src/data/legacy.json src/data/leaderboard.json src/data/papers.json src/data/competitors.json src/data/mcpmarket.json src/data/idp.json
if git diff --cached --quiet; then
    echo "No changes to push."
else
    git commit -m "daily report $(date '+%Y-%m-%d')"
    git push
    echo "Pushed. Vercel will auto-deploy."
fi

echo "Done at $(date '+%H:%M:%S')"
