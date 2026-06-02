#!/bin/bash
# Wire up Cloud Scheduler to fire the AI War Room Job daily at 16:00 Taiwan time.
# Run AFTER bin/quick-deploy.sh has created the Job at least once.

set -e

GCP_PROJECT_ID="kdan-it-playground"
GCP_REGION="asia-east1"
JOB_NAME="ainews-pipeline"
SCHEDULER_JOB_NAME="ainews-daily"
SCHEDULER_SA_EMAIL="ainews-scheduler-sa@${GCP_PROJECT_ID}.iam.gserviceaccount.com"

gcloud config set project $GCP_PROJECT_ID

echo "Granting Cloud Run invoker to scheduler SA..."
gcloud run jobs add-iam-policy-binding $JOB_NAME \
  --region=$GCP_REGION \
  --member="serviceAccount:$SCHEDULER_SA_EMAIL" \
  --role="roles/run.invoker" >/dev/null

URI="https://${GCP_REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${GCP_PROJECT_ID}/jobs/${JOB_NAME}:run"

if gcloud scheduler jobs describe $SCHEDULER_JOB_NAME --location=$GCP_REGION >/dev/null 2>&1; then
  echo "Updating existing scheduler job $SCHEDULER_JOB_NAME..."
  gcloud scheduler jobs update http $SCHEDULER_JOB_NAME \
    --location=$GCP_REGION \
    --schedule="0 16 * * *" \
    --time-zone="Asia/Taipei" \
    --uri="$URI" \
    --http-method=POST \
    --oauth-service-account-email="$SCHEDULER_SA_EMAIL"
else
  echo "Creating scheduler job $SCHEDULER_JOB_NAME..."
  gcloud scheduler jobs create http $SCHEDULER_JOB_NAME \
    --location=$GCP_REGION \
    --schedule="0 16 * * *" \
    --time-zone="Asia/Taipei" \
    --uri="$URI" \
    --http-method=POST \
    --oauth-service-account-email="$SCHEDULER_SA_EMAIL"
fi

echo "Scheduler is set. Fire a one-off test run:"
echo "  gcloud scheduler jobs run $SCHEDULER_JOB_NAME --location=$GCP_REGION"
