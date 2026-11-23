#!/usr/bin/env bash
# ==============================================================================
# FORGE: Cloud Run Deployment Script
# Cyber Hackathon 2026 | PS-05 | Digital Forensics
# ==============================================================================
set -euo pipefail

# ANSI Color Codes
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}==================================================================${NC}"
echo -e "${CYAN}  FORGE: Digital Evidence Platform - Cloud Run Deployment Setup   ${NC}"
echo -e "${CYAN}==================================================================${NC}"

# 1. Environment & Project Resolution
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || true)}"
if [ -z "$PROJECT_ID" ]; then
  echo -e "${RED}[ERROR] GCP Project ID not specified and no default found in gcloud config.${NC}"
  echo -e "Usage: PROJECT_ID=my-gcp-project REGION=asia-south1 ./scripts/deploy_cloud_run.sh"
  exit 1
fi

REGION="${REGION:-asia-south1}"
SERVICE_NAME="${SERVICE_NAME:-forge}"
BUCKET_NAME="${BUCKET_NAME:-forge-evidence-${PROJECT_ID}}"
DEMO_CODE="${DEMO_ACCESS_CODE:-FORGE2026}"

echo -e "${GREEN}[INFO] Project ID:      ${PROJECT_ID}${NC}"
echo -e "${GREEN}[INFO] Region:          ${REGION}${NC}"
echo -e "${GREEN}[INFO] Service Name:    ${SERVICE_NAME}${NC}"
echo -e "${GREEN}[INFO] Evidence Bucket: ${BUCKET_NAME}${NC}"

# 2. Enable Required Google Cloud APIs
echo -e "\n${YELLOW}[1/5] Enabling Google Cloud Services...${NC}"
gcloud services enable \
  run.googleapis.com \
  storage.googleapis.com \
  firestore.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  --project="${PROJECT_ID}"

# 3. Provision Cloud Storage Bucket for Evidence & Signed Direct Uploads
echo -e "\n${YELLOW}[2/5] Configuring Cloud Storage Bucket...${NC}"
if ! gsutil ls -b "gs://${BUCKET_NAME}" >/dev/null 2>&1; then
  echo -e "${GREEN}[INFO] Creating bucket gs://${BUCKET_NAME}...${NC}"
  gcloud storage buckets create "gs://${BUCKET_NAME}" \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --uniform-bucket-level-access
fi

# Apply CORS policy for direct browser-to-bucket signed PUT upload
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo -e "${GREEN}[INFO] Applying CORS rules to gs://${BUCKET_NAME}...${NC}"
gcloud storage buckets update "gs://${BUCKET_NAME}" \
  --cors-file="${SCRIPT_DIR}/cors_gcs.json"

# 4. Provision Service Account with Least Privilege
echo -e "\n${YELLOW}[3/5] Configuring Service Account & IAM Roles...${NC}"
SA_NAME="forge-runner"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe "${SA_EMAIL}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo -e "${GREEN}[INFO] Creating service account ${SA_NAME}...${NC}"
  gcloud iam service-accounts create "${SA_NAME}" \
    --display-name="FORGE Forensic Engine Runner" \
    --project="${PROJECT_ID}"
fi

# Grant Storage Object Admin (for reading evidence working copies & storing artifacts)
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectAdmin" >/dev/null

# Grant Token Creator (for generating V4 signed upload URLs on Cloud Run)
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/iam.serviceAccountTokenCreator" >/dev/null

# 5. Build and Deploy Single-Container to Cloud Run
echo -e "\n${YELLOW}[4/5] Building Container and Deploying to Cloud Run...${NC}"
gcloud run deploy "${SERVICE_NAME}" \
  --source . \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --platform=managed \
  --service-account="${SA_EMAIL}" \
  --allow-unauthenticated \
  --memory=4Gi \
  --cpu=2 \
  --concurrency=10 \
  --timeout=300 \
  --set-env-vars="STORAGE_MODE=gcp,GCS_BUCKET=${BUCKET_NAME},DEMO_ACCESS_CODE=${DEMO_CODE}"

# 6. Verify Deployment Health
echo -e "\n${YELLOW}[5/5] Verifying Deployment Health...${NC}"
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --format="value(status.url)")

echo -e "${GREEN}==================================================================${NC}"
echo -e "${GREEN}  FORGE SUCCESSFULLY DEPLOYED TO GOOGLE CLOUD RUN!               ${NC}"
echo -e "${GREEN}==================================================================${NC}"
echo -e "Service URL:       ${CYAN}${SERVICE_URL}${NC}"
echo -e "Health Check:      ${CYAN}${SERVICE_URL}/healthz${NC}"
echo -e "Interactive Docs:  ${CYAN}${SERVICE_URL}/api/docs${NC}"
echo -e "Demo Access Code:  ${CYAN}${DEMO_CODE}${NC}"
echo -e "=================================================================="
