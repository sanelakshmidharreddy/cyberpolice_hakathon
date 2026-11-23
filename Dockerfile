# ==============================================================================
# FORGE: Digital Evidence Authenticity & Integrity Verification Platform
# Cyber Hackathon 2026 | PS-05 | Digital Forensics
# Multi-stage Dockerfile: Node 20 (Vite build) -> Python 3.11-slim (Forensic runtime)
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Frontend Build
# ------------------------------------------------------------------------------
FROM node:20-slim AS frontend-builder
WORKDIR /build

# Copy frontend manifest files
COPY frontend/package*.json ./
# Allow build to succeed even if frontend code is being developed iteratively
RUN if [ -f package.json ]; then npm ci --ignore-scripts || npm install; fi

# Copy frontend source and build static bundle
COPY frontend/ ./
RUN if [ -f package.json ] && grep -q '"build"' package.json; then npm run build; else mkdir -p dist; fi

# ------------------------------------------------------------------------------
# Stage 2: Forensic Backend & Unified Runtime
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    PYTHONPATH=/app/backend

WORKDIR /app

# Install native forensic and system libraries:
# - ffmpeg / ffprobe: video/audio extraction & frame timeline slicing
# - libimage-exiftool-perl: thorough EXIF/metadata anomaly inspection
# - tesseract-ocr: optical character recognition for CCTV on-screen clock verification
# - libgl1, libglib2.0-0: required for OpenCV headless image/video decoding
# - curl: container healthcheck probing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libimage-exiftool-perl \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python backend dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r ./backend/requirements.txt

# Copy built frontend assets from Stage 1
COPY --from=frontend-builder /build/dist ./frontend/dist

# Copy backend source code, samples, and scripts
COPY backend ./backend
COPY samples ./samples
COPY scripts ./scripts

# Create runtime evidence and scratch directories
RUN mkdir -p /app/data/evidence /app/data/artifacts /app/data/scratch /tmp/forge_scratch && \
    chmod -R 777 /app/data /tmp/forge_scratch

# Security: Create non-root user
RUN useradd -m -u 10001 forgeuser && \
    chown -R forgeuser:forgeuser /app
USER forgeuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/healthz || exit 1

WORKDIR /app/backend
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
