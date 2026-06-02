#!/bin/bash
# Cloud Run Job entrypoint for AI War Room pipeline.
#
#   1. Pull warroom.db from GCS (state bucket)
#   2. Run the daily pipeline (agent / competitor / compress / export / leaderboard / notify)
#   3. Push warroom.db back to GCS
#   4. Clone target GitHub repo with PAT, copy src/data/*.json, commit + push
#      → Vercel auto-deploys
#
# Required env (set on the Cloud Run Job):
#   (set on the Cloud Run Job by bin/quick-deploy.sh, sourced from pipeline/.env)
#   STATE_BUCKET           — GCS bucket holding warroom.db
#   GOOGLE_API_KEY         — Gemini
#   REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET — Reddit API
#   MATTERMOST_URL         — chat.kdan.cc
#   MATTERMOST_BOT_TOKEN / MATTERMOST_CHANNEL_ID — Mattermost notify
#   GITHUB_PAT             — fine-grained PAT with contents:write on the repo
#   GIT_BRANCH             — defaults to main

set -euo pipefail

REPO_OWNER="R09722akaBennett"
REPO_NAME="ainews-warroom"
BRANCH="${GIT_BRANCH:-main}"

STATE_URI="gs://${STATE_BUCKET}/warroom.db"
DB_PATH="/app/pipeline/warroom.db"

echo "=========================================="
echo "AI War Room Job — $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "=========================================="

# 1. Restore db from GCS (allow miss on first run)
echo "[0/7] Restoring warroom.db from $STATE_URI..."
if ! gcloud storage cp "$STATE_URI" "$DB_PATH" 2>&1; then
  echo "  (no existing db in GCS — pipeline will create a fresh one)"
fi

cd /app/pipeline

# 2~7. Mirror pipeline/daily.sh, minus the local git push
echo "[1/7] agent — collect news + generate report..."
uv run python -m agent

echo "[2/7] competitor — collect + classify..."
uv run python -m competitor

echo "[3/7] compress auto..."
uv run python -m compress auto
if [ "$(date +%u)" = "1" ]; then
  echo "  Monday — generating competitor weekly..."
  uv run python -m competitor --classify
fi

echo "[3.5/7] idp..."
uv run python -m idp || echo "  WARN: idp failed (exit $?), continuing"

echo "[4/7] export DB → JSON..."
uv run python -m export

echo "[5/7] leaderboard..."
uv run python -m leaderboard

echo "[6/7] notify Mattermost..."
if [[ -n "${MATTERMOST_URL:-}" && -n "${MATTERMOST_BOT_TOKEN:-}" ]]; then
  uv run python -m notify || echo "  WARN: notify failed (exit $?), continuing"
else
  echo "  skip — MATTERMOST_URL or MATTERMOST_BOT_TOKEN not set"
fi

# 8. Save db
echo "[7a/7] Saving warroom.db back to $STATE_URI..."
gcloud storage cp "$DB_PATH" "$STATE_URI"

# 9. git push site data
echo "[7b/7] Pushing src/data/*.json to GitHub..."
if [[ -z "${GITHUB_PAT:-}" ]]; then
  echo "  ERROR: GITHUB_PAT not set — cannot push. Job ends here."
  exit 1
fi

# Commit author must be associable by GitHub with the Vercel-owner account
# (R09722akaBennett), or Vercel (Hobby) refuses to deploy. The account's real email
# is private, so use its GitHub noreply address — GitHub always links it to the user
# and it sidesteps push protection on private emails.
git config --global user.email "74374763+R09722akaBennett@users.noreply.github.com"
git config --global user.name "R09722akaBennett"
git config --global init.defaultBranch main

WORK=/tmp/repo
rm -rf "$WORK"
git clone --depth=1 --branch "$BRANCH" \
  "https://x-access-token:${GITHUB_PAT}@github.com/${REPO_OWNER}/${REPO_NAME}.git" "$WORK"

# Copy the JSONs that export wrote
mkdir -p "$WORK/src/data"
cp /app/src/data/*.json "$WORK/src/data/"

cd "$WORK"
git add src/data/
if git diff --cached --quiet; then
  echo "  no changes — skipping commit/push"
else
  git commit -m "daily report $(date '+%Y-%m-%d')"
  git push origin "$BRANCH"
  echo "  pushed — Vercel will auto-deploy"
fi

echo "Done at $(date '+%Y-%m-%d %H:%M:%S %Z')"
