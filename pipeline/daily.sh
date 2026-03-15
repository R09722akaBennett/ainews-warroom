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

mkdir -p "$LOG_DIR"

echo ""
echo "=========================================="
echo "AI War Room — $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

cd "$PIPELINE_DIR"

# Load environment
source .env 2>/dev/null || true

# Step 1: Collect news + generate report
echo "[1/5] Running agent..."
uv run python -m agent

# Step 2: Auto-compress (weekly on Mon, monthly on 1st, quarterly on quarter start)
echo "[2/5] Running compress..."
uv run python -m compress auto

# Step 3: Export DB → JSON for website
echo "[3/5] Exporting site data..."
uv run python -m export

# Step 4: Notify Mattermost
echo "[4/5] Sending to Mattermost..."
uv run python -m notify

# Step 5: Push to git → triggers Vercel deploy
echo "[5/5] Pushing to git..."
cd "$REPO_DIR"
git add src/data/reports.json src/data/sources.json src/data/summaries.json src/data/legacy.json
if git diff --cached --quiet; then
    echo "No changes to push."
else
    git commit -m "daily report $(date '+%Y-%m-%d')"
    git push
    echo "Pushed. Vercel will auto-deploy."
fi

echo "Done at $(date '+%H:%M:%S')"
