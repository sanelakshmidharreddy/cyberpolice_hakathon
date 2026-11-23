# FORGE: Digital Evidence Authenticity & Integrity Verification Platform

[![Python](https://img.shields.io/badge/Python-3.11-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-5-646CFF.svg?style=flat&logo=vite&logoColor=white)](https://vitejs.dev/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4-38B2AC.svg?style=flat&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![Docker](https://img.shields.io/badge/Docker-Multi--stage-2496ED.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![Cloud Run](https://img.shields.io/badge/Google_Cloud_Run-Ready-4285F4.svg?style=flat&logo=google-cloud&logoColor=white)](https://cloud.google.com/run)
[![License](https://img.shields.io/badge/License-Proprietary_Hackathon-orange.svg)]()

> **Cyber Hackathon 2026** (Organized by C-DAC Patna / CCSU Bihar Police)  
> **Problem Statement:** PS-05  
> **Track:** Digital Forensics  
> **Solution Name:** FORGE  

---

## 1. Executive Summary

In contemporary law enforcement and judicial proceedings, digital media (surveillance CCTV footage, crime scene photographs, leaked audio recordings) are vital pieces of evidence. However, digital manipulation tools (Photoshop, Premiere, deepfake audio tools) allow bad actors to forge evidence or compromise investigations.

**FORGE** is an end-to-end, courtroom-admissible digital forensics platform that provides:

1. **Strict Cryptographic Chain of Custody (ISO/IEC 27037:2012)**:
   - On-the-fly streaming SHA-256 calculation during evidence upload.
   - Enforced POSIX read-only permissions on original evidence files (`chmod 444`).
   - Automated hash re-verification before report generation.
   - Append-only immutable audit trail logging every forensic action.

2. **CPU-Optimized Multi-Modal Forensic Analytics**:
   - **Images**: EXIF metadata & software signature detection (Photoshop/GIMP/Snapseed), Quality-90 Error Level Analysis (ELA) heatmaps, ORB + RANSAC copy-move affine clustering, and high-pass median residual noise variance mapping.
   - **Video**: Inter-frame perceptual hashing, Farneback optical flow motion discontinuity cuts, CCTV freeze-frame / loop detection, and on-screen burned-in clock OCR verification.
   - **Audio**: 50 Hz Electric Network Frequency (ENF) power grid phase jump detection via Second-Order Sections (SOS) bandpass filtering, digital zero silence gap detection, and acoustic vocal tract anti-spoofing.

3. **Zero-Fabrication Integrity Policy**:
   - Every metric derives from real signal processing and computer vision computation.
   - If a modality or check cannot run (e.g. no audio track, missing EXIF), FORGE reports `NOT_APPLICABLE` or `INCONCLUSIVE` with plain-English technical explanations.

4. **Courtroom-Ready Section 65B PDF Reports**:
   - Official ReportLab PDF generator containing case dossier, upload vs. verification SHA-256 comparison table, categorical verdicts (`AUTHENTIC`, `SUSPICIOUS`, `LIKELY_TAMPERED`), high-resolution visual heatmap artifacts, complete audit logs, and statutory legal declarations.

5. **Cloud Run & Offline Edge Architecture**:
   - Unified single-container deployment serving built React frontend and FastAPI backend on port 8080.
   - Google Cloud Storage provider with V4 signed URLs for direct browser-to-bucket upload, bypassing Cloud Run request limits.

---

## 2. Forensic Module Capability Matrix

| Modality | Module Name | Core Techniques & Algorithms | Anomalies Flagged |
| :--- | :--- | :--- | :--- |
| **Image** | `image_metadata` | EXIF/IPTC parsing, software signature regex, timestamp boundary checks, embedded thumbnail dHash comparison. | Editing software tags (Photoshop, GIMP, Snapseed), future timestamps, dimension discrepancies, thumbnail mismatches. |
| **Image** | `image_ela` | JPEG resave at Quality 90, absolute error delta calculation, 32x32 grid z-score anomalies, DCT histogram periodicity. | Double JPEG compression artifacts, localized editing error spikes, copy-pasted foreign regions. |
| **Image** | `image_splicing` | ORB keypoint clustering, Lowe's ratio test, RANSAC affine estimation, median high-pass noise residual variance. | Duplicated image segments (copy-move cloning), composite noise-floor variance mismatches. |
| **Video** | `video_frames` | Frame-by-frame perceptual difference hash (`dhash`), Farneback dense optical flow, 3-sigma adaptive motion thresholding. | Temporal jump cuts (missing frames), surveillance freeze-frame loops, frame deletion. |
| **Video** | `video_timestamps` | Container vs stream duration verification, 1 Hz banner strip Tesseract OCR timestamp tracking. | Container duration mismatch, CCTV on-screen clock stalls ($\Delta T = 0$), clock teleportation jumps. |
| **Audio** | `audio_tamper` | 6th-order Butterworth SOS bandpass (48-52 Hz), Hilbert analytic signal phase extraction, zero-amplitude run scanner. | 50 Hz ENF grid phase discontinuities (audio splicing), digital zero silence insertions. |
| **Audio** | `audio_deepfake` | Sliding 4-second vocal spectral flux analysis, high-frequency acoustic roll-off. | Synthetic speech artifacts, voice cloning vocoder anomalies. |

---

## 3. Quickstart: Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- (Optional): `ffmpeg`, `exiftool`, `tesseract-ocr` (Analyzers degrade gracefully if tools are not present on local host)

### 1. Clone & Set Up Backend
```bash
git clone https://github.com/rahulganesh-tech/forge.git
cd forge

# Create virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 2. Set Up & Build Frontend
```bash
cd frontend
npm install
npm run build
cd ..
```

### 3. Start Unified Server
```bash
# Run server from workspace root (serves both API and built React UI)
uvicorn app.main:app --app-dir backend --port 8080 --reload
```
Open **`http://localhost:8080`** in your browser.

---

## 4. Running the Test Suite

FORGE includes a comprehensive suite of 40 unit and integration tests covering hashing, storage isolation, audit trails, every forensic analyzer, scoring, PDF generation, and deployment configurations:

```bash
# Run full test suite with verbose output
pytest backend/tests -v
```

---

## 5. Generating Synthetic Forensic Samples

FORGE includes a non-copyrighted synthetic sample generator that creates 10 test fixtures (originals and deliberate forensic manipulations):

```bash
python samples/generate_samples.py
```

Generated sample fixtures in `samples/`:
1. `image_original.jpg` — Clean JPEG with camera metadata.
2. `image_photoshop.jpg` — Injected Adobe Photoshop software signature.
3. `image_future_date.jpg` — Injected future timestamp (Year 2035).
4. `image_stripped.jpg` — Completely stripped EXIF metadata.
5. `image_copymove.jpg` — Cloned visual region with ORB keypoint match.
6. `image_spliced.jpg` — Foreign inserted high-frequency block triggering ELA.
7. `cctv_original.mp4` — Continuous CCTV surveillance footage with smooth motion.
8. `cctv_cut.mp4` — CCTV clip with spliced 2-second jump cut deletion.
9. `cctv_dup.mp4` — CCTV footage with a 2-second frozen surveillance loop.
10. `audio_original.wav` — Continuous tone recording with natural 50 Hz hum.
11. `audio_spliced.wav` — Spliced audio clip with an abrupt 50 Hz ENF phase jump.
12. `audio_cut.wav` — Audio recording with artificial digital zero silence inserted.

---

## 6. Complete cURL API Walkthrough

### A. Healthcheck Probe
```bash
curl -X GET http://localhost:8080/healthz
```

### B. Create Forensics Case
```bash
curl -X POST http://localhost:8080/api/cases \
  -H "Content-Type: application/json" \
  -d '{
    "investigator_name": "Insp. Rajesh Kumar",
    "case_reference": "FIR-2026-PAT-0042"
  }'
```

### C. Upload Evidence File (Streaming SHA-256)
```bash
curl -X POST http://localhost:8080/api/cases/<CASE_ID>/files \
  -F "file=@samples/image_copymove.jpg"
```

### D. Trigger Multi-Modal Forensic Analysis
```bash
curl -X POST http://localhost:8080/api/cases/<CASE_ID>/files/<FILE_ID>/analyze
```

### E. Poll Analysis Progress
```bash
curl -X GET http://localhost:8080/api/cases/<CASE_ID>/files/<FILE_ID>/status
```

### F. Fetch Forensic Results & Verdict
```bash
curl -X GET http://localhost:8080/api/cases/<CASE_ID>/files/<FILE_ID>/results
```

### G. Download Courtroom Forensic Report (PDF)
```bash
curl -X GET http://localhost:8080/api/cases/<CASE_ID>/report.pdf \
  -o FORGE_Courtroom_Report.pdf
```

---

## 7. Google Cloud Run Deployment

FORGE is packaged as a single-container multi-stage Docker image, combining Node 20 (Vite frontend build) and Python 3.11-slim (native forensic runtime with `ffmpeg`, `exiftool`, and `tesseract-ocr`).

### Automated Deployment Script:
```bash
# On Linux / macOS:
PROJECT_ID="your-gcp-project-id" REGION="asia-south1" ./scripts/deploy_cloud_run.sh

# On Windows (PowerShell):
.\scripts\deploy_cloud_run.ps1 -ProjectId "your-gcp-project-id" -Region "asia-south1"
```

### What the script automates:
1. Enables Cloud Run, Cloud Storage, and Firestore APIs.
2. Creates GCS bucket `forge-evidence-<PROJECT_ID>` with CORS configuration for direct browser-to-bucket upload.
3. Provisions service account `forge-runner` with `roles/storage.objectAdmin` and `roles/iam.serviceAccountTokenCreator`.
4. Deploys container to Cloud Run with 4GB RAM, 2 vCPUs, and concurrency 10.
5. Verifies deployment health via `/healthz`.

---

## 8. Legal Disclaimer & Section 65B Compliance

Forensic outputs provided by the FORGE platform are **computational indicators accompanied by calibrated statistical confidence ratings**. They are engineered to assist digital forensic investigators and judicial authorities under **Section 65B of the Indian Evidence Act, 1872** and **Section 63 of the Bharatiya Sakshya Adhiniyam, 2023**. Results provide transparent technical proof and do not replace final legal adjudication by a competent court of law.

---

**Developed for Cyber Hackathon 2026** • C-DAC Patna / CCSU Bihar Police
