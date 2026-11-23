# ==============================================================================
# FORGE: Cloud Run Deployment Script (PowerShell for Windows)
# Cyber Hackathon 2026 | PS-05 | Digital Forensics
# ==============================================================================
param (
    [string]$ProjectId = $env:PROJECT_ID,
    [string]$Region = "asia-south1",
    [string]$ServiceName = "forge",
    [string]$BucketName = "",
    [string]$DemoAccessCode = "FORGE2026"
)

$ErrorActionPreference = "Stop"

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "  FORGE: Digital Evidence Platform - Cloud Run Deployment Setup   " -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan

if (-not $ProjectId) {
    try {
        $ProjectId = (gcloud config get-value project 2>$null).Trim()
    } catch {}
}

if (-not $ProjectId) {
    Write-Host "[ERROR] GCP Project ID not provided and no default project found in gcloud config." -ForegroundColor Red
    Write-Host "Usage: .\scripts\deploy_cloud_run.ps1 -ProjectId 'my-gcp-project' -Region 'asia-south1'"
    exit 1
}

if (-not $BucketName) {
    $BucketName = "forge-evidence-$ProjectId"
}

Write-Host "[INFO] Project ID:      $ProjectId" -ForegroundColor Green
Write-Host "[INFO] Region:          $Region" -ForegroundColor Green
Write-Host "[INFO] Service Name:    $ServiceName" -ForegroundColor Green
Write-Host "[INFO] Evidence Bucket: $BucketName" -ForegroundColor Green

# 1. Enable APIs
Write-Host "`n[1/5] Enabling Google Cloud Services..." -ForegroundColor Yellow
gcloud services enable `
    run.googleapis.com `
    storage.googleapis.com `
    firestore.googleapis.com `
    artifactregistry.googleapis.com `
    cloudbuild.googleapis.com `
    --project=$ProjectId

# 2. Bucket & CORS
Write-Host "`n[2/5] Configuring Cloud Storage Bucket..." -ForegroundColor Yellow
$bucketExists = $false
try {
    $null = gsutil ls -b "gs://$BucketName" 2>$null
    $bucketExists = $true
} catch {}

if (-not $bucketExists) {
    Write-Host "[INFO] Creating bucket gs://$BucketName..." -ForegroundColor Green
    gcloud storage buckets create "gs://$BucketName" `
        --project=$ProjectId `
        --location=$Region `
        --uniform-bucket-level-access
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$CorsPath = Join-Path $ScriptDir "cors_gcs.json"
Write-Host "[INFO] Applying CORS rules to gs://$BucketName..." -ForegroundColor Green
gcloud storage buckets update "gs://$BucketName" --cors-file=$CorsPath

# 3. Service Account
Write-Host "`n[3/5] Configuring Service Account & IAM Roles..." -ForegroundColor Yellow
$SaName = "forge-runner"
$SaEmail = "$SaName@$ProjectId.iam.gserviceaccount.com"

try {
    $null = gcloud iam service-accounts describe $SaEmail --project=$ProjectId 2>$null
} catch {
    Write-Host "[INFO] Creating service account $SaName..." -ForegroundColor Green
    gcloud iam service-accounts create $SaName `
        --display-name="FORGE Forensic Engine Runner" `
        --project=$ProjectId
}

gcloud projects add-iam-policy-binding $ProjectId `
    --member="serviceAccount:$SaEmail" `
    --role="roles/storage.objectAdmin" | Out-Null

gcloud projects add-iam-policy-binding $ProjectId `
    --member="serviceAccount:$SaEmail" `
    --role="roles/iam.serviceAccountTokenCreator" | Out-Null

# 4. Deploy to Cloud Run
Write-Host "`n[4/5] Building Container and Deploying to Cloud Run..." -ForegroundColor Yellow
gcloud run deploy $ServiceName `
    --source . `
    --project=$ProjectId `
    --region=$Region `
    --platform=managed `
    --service-account=$SaEmail `
    --allow-unauthenticated `
    --memory="4Gi" `
    --cpu="2" `
    --concurrency=10 `
    --timeout=300 `
    --set-env-vars="STORAGE_MODE=gcp,GCS_BUCKET=$BucketName,DEMO_ACCESS_CODE=$DemoAccessCode"

# 5. Output Results
Write-Host "`n[5/5] Verifying Deployment..." -ForegroundColor Yellow
$ServiceUrl = (gcloud run services describe $ServiceName --project=$ProjectId --region=$Region --format="value(status.url)").Trim()

Write-Host "==================================================================" -ForegroundColor Green
Write-Host "  FORGE SUCCESSFULLY DEPLOYED TO GOOGLE CLOUD RUN!               " -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "Service URL:       $ServiceUrl" -ForegroundColor Cyan
Write-Host "Health Check:      $ServiceUrl/healthz" -ForegroundColor Cyan
Write-Host "Interactive Docs:  $ServiceUrl/api/docs" -ForegroundColor Cyan
Write-Host "Demo Access Code:  $DemoAccessCode" -ForegroundColor Cyan
Write-Host "=================================================================="
