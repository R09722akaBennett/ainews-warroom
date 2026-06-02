#!/bin/bash
# One-time GCP setup for the AI War Room Cloud Run Job.
# Run this ONCE before the first bin/quick-deploy.sh.
#
# What this does:
#   - enables required GCP APIs
#   - creates the state GCS bucket (and uploads current warroom.db if present)
#   - grants minimum IAM on the existing Job SA (Bennett's personal SA)
#   - creates a dedicated Scheduler SA
#
# Secrets are NOT managed here — bin/quick-deploy.sh injects them as plaintext
# env vars sourced from pipeline/.env (Option B). No Secret Manager / admin grant
# needed. (Git history has the old Secret Manager bootstrap if we ever switch back.)
#
# Idempotent: safe to re-run; existing resources are skipped.

set -e

GCP_PROJECT_ID="kdan-it-playground"
GCP_REGION="asia-east1"
JOB_NAME="ainews-pipeline"
STATE_BUCKET="${GCP_PROJECT_ID}-ainews-state"
# Job runs as Bennett's existing SA (least-privilege via per-resource bindings below)
SA_EMAIL="bennett-tai-kdanmobile-com@${GCP_PROJECT_ID}.iam.gserviceaccount.com"
# Scheduler uses a dedicated SA so it has invoke-only rights and nothing else
SCHEDULER_SA_NAME="ainews-scheduler-sa"
SCHEDULER_SA_EMAIL="${SCHEDULER_SA_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com"

gcloud config set project $GCP_PROJECT_ID

echo "Enabling APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudscheduler.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  storage.googleapis.com

echo "Creating state bucket gs://$STATE_BUCKET..."
gcloud storage buckets describe gs://$STATE_BUCKET >/dev/null 2>&1 || \
  gcloud storage buckets create gs://$STATE_BUCKET \
    --location=$GCP_REGION --uniform-bucket-level-access

if [ -f pipeline/warroom.db ]; then
  echo "Uploading current pipeline/warroom.db as initial state..."
  gcloud storage cp pipeline/warroom.db gs://$STATE_BUCKET/warroom.db
fi

echo "Verifying job SA exists ($SA_EMAIL)..."
gcloud iam service-accounts describe $SA_EMAIL >/dev/null 2>&1 \
  || { echo "ERROR: $SA_EMAIL not found. Check the SA email."; exit 1; }

echo "Granting bucket IAM to job SA..."
gcloud storage buckets add-iam-policy-binding gs://$STATE_BUCKET \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/storage.objectUser" >/dev/null

echo "Creating scheduler service account..."
gcloud iam service-accounts describe $SCHEDULER_SA_EMAIL >/dev/null 2>&1 || \
  gcloud iam service-accounts create $SCHEDULER_SA_NAME \
    --display-name="AI news pipeline (Cloud Scheduler trigger)"

# Scheduler SA needs invoker on the Job; this binding is harmless before the Job exists
# but gcloud will reject it then. Defer this to after first deploy:
echo ""
echo "=========================================================="
echo "Bootstrap done. No admin / Secret Manager grant needed."
echo "=========================================================="
echo ""
echo "Before deploying, make sure pipeline/.env has GITHUB_PAT set:"
echo "  echo 'GITHUB_PAT=github_pat_xxx' >> pipeline/.env"
echo "  (fine-grained PAT, repo=ainews-warroom, contents:write only)"
echo ""
echo "Next steps:"
echo "  1) bin/quick-deploy.sh                # build image + create Job"
echo "  2) gcloud run jobs execute $JOB_NAME --region=$GCP_REGION --wait   # smoke test"
echo "  3) bin/setup-scheduler.sh             # wire up Cloud Scheduler (daily 16:00 TW)"
