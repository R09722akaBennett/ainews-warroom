#!/bin/bash
# Deploy the AI War Room pipeline as a Cloud Run Job.
#
# One-time prerequisites (run bin/bootstrap.sh once before the first deploy,
# or follow the manual steps in README — they enable APIs, create the GCS
# state bucket and service account).
#
# Secrets are read from pipeline/.env at deploy time (see below). Make sure that
# file exists and includes GITHUB_PAT before running this.
#
# Usage:
#   bin/quick-deploy.sh   # run from the repo root
#
# After deploy, test with:
#   gcloud run jobs execute ainews-pipeline --region=asia-east1 --wait

set -e

GCP_PROJECT_ID="kdan-it-playground"
GCP_REGION="asia-east1"
AR_REPO="ainews-ar-repo"
JOB_NAME="ainews-pipeline"
STATE_BUCKET="${GCP_PROJECT_ID}-ainews-state"
# Job runs as Bennett's existing SA (kept in sync with bootstrap.sh)
SA_EMAIL="bennett-tai-kdanmobile-com@${GCP_PROJECT_ID}.iam.gserviceaccount.com"

TAG=$(date +"%Y%m%d-%H%M%S")
IMAGE_BASE="$GCP_REGION-docker.pkg.dev/$GCP_PROJECT_ID/$AR_REPO/$JOB_NAME"
IMAGE_WITH_TAG="$IMAGE_BASE:$TAG"

echo "Checking gcloud auth..."
gcloud auth list --filter=status:ACTIVE --format="value(account)" \
  || { echo "Run 'gcloud auth login' first"; exit 1; }

echo "Setting GCP project to $GCP_PROJECT_ID..."
gcloud config set project $GCP_PROJECT_ID

echo "Checking or creating Artifact Registry repo $AR_REPO..."
gcloud artifacts repositories describe $AR_REPO --location=$GCP_REGION >/dev/null 2>&1 || {
    echo "Repository does not exist, creating $AR_REPO..."
    gcloud artifacts repositories create $AR_REPO \
        --repository-format=docker \
        --location=$GCP_REGION \
        --description="AI war room images"
}

echo "Building and pushing Docker image via Cloud Build..."
gcloud builds submit . --config=bin/cloudbuild.yaml \
    --substitutions=_GCP_REGION="$GCP_REGION",_AR_REPO="$AR_REPO",_JOB_NAME="$JOB_NAME",_TAG="$TAG" \
    --project=$GCP_PROJECT_ID

echo "Cloud Build complete: $IMAGE_WITH_TAG"

# --- Cloud Run Job env (Option B: plaintext env vars, sourced from pipeline/.env) ---
# NOTE: secret values land in the Job spec as PLAINTEXT. Anyone with Editor+ on
# $GCP_PROJECT_ID can read them via `gcloud run jobs describe ... --format=yaml`.
# Accepted trade-off for now (matches the team's streamlit-app deploy). Migrate to
# Secret Manager (--set-secrets) if GOOGLE_API_KEY spend or GITHUB_PAT blast radius
# grows — git history of bootstrap.sh shows the secret-based setup.
ENV_FILE="pipeline/.env"
[ -f "$ENV_FILE" ] || { echo "ERROR: $ENV_FILE not found — run this from the repo root."; exit 1; }
set -a; source "$ENV_FILE"; set +a

# GITHUB_PAT is NOT in .env by default. Add it before deploying:
#   echo 'GITHUB_PAT=github_pat_xxx' >> pipeline/.env
# Use a fine-grained PAT scoped to repo=ainews-warroom with contents:write only.
: "${GOOGLE_API_KEY:?missing in $ENV_FILE}"
: "${GITHUB_PAT:?missing — add a fine-grained PAT (contents:write on ainews-warroom) to $ENV_FILE}"

# Custom delimiter (^@@^) so any secret value containing a comma can't break parsing.
ENV_VARS="^@@^STATE_BUCKET=$STATE_BUCKET"
ENV_VARS+="@@GEMINI_MODEL=${GEMINI_MODEL:-gemini-3-flash-preview}"
ENV_VARS+="@@TZ=Asia/Taipei"
ENV_VARS+="@@GIT_BRANCH=main"
ENV_VARS+="@@GOOGLE_API_KEY=$GOOGLE_API_KEY"
ENV_VARS+="@@REDDIT_CLIENT_ID=$REDDIT_CLIENT_ID"
ENV_VARS+="@@REDDIT_CLIENT_SECRET=$REDDIT_CLIENT_SECRET"
ENV_VARS+="@@REDDIT_USER_AGENT=${REDDIT_USER_AGENT:-ainews-pipeline/0.1}"
ENV_VARS+="@@GITHUB_PAT=$GITHUB_PAT"

# Deploy as a Job. Try update first (subsequent runs); fall back to create (first run).
echo "Deploying Cloud Run Job $JOB_NAME..."
if gcloud run jobs describe $JOB_NAME --region=$GCP_REGION >/dev/null 2>&1; then
    gcloud run jobs update $JOB_NAME \
        --image=$IMAGE_WITH_TAG \
        --region=$GCP_REGION \
        --service-account=$SA_EMAIL \
        --set-env-vars="$ENV_VARS" \
        --cpu=2 --memory=4Gi \
        --task-timeout=86400s \
        --max-retries=1
else
    gcloud run jobs create $JOB_NAME \
        --image=$IMAGE_WITH_TAG \
        --region=$GCP_REGION \
        --service-account=$SA_EMAIL \
        --set-env-vars="$ENV_VARS" \
        --cpu=2 --memory=4Gi \
        --task-timeout=86400s \
        --max-retries=1
fi

echo "=========================================================="
echo "Deployed. Image: $IMAGE_WITH_TAG"
echo "Test the Job:"
echo "  gcloud run jobs execute $JOB_NAME --region=$GCP_REGION --wait"
echo "Tail logs:"
echo "  gcloud beta run jobs logs tail $JOB_NAME --region=$GCP_REGION"
