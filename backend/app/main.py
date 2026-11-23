import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.api.routes_cases import router as cases_router

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("forge.api")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Digital Evidence Authenticity & Integrity Verification Platform for Cyber Hackathon 2026 (PS-05).",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """Enriches requests with unique Request-ID, timing, and security checks."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    start_time = time.perf_counter()

    # Optional demo access code verification for public Cloud Run deployments
    if settings.DEMO_ACCESS_CODE and not request.url.path.startswith(("/healthz", "/api/docs", "/api/openapi.json", "/api/redoc", "/assets/", "/vite.svg")):
        access_code = request.headers.get("X-Forge-Access-Code") or request.query_params.get("access_code")
        if access_code != settings.DEMO_ACCESS_CODE:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "Unauthorized",
                    "message": "Valid X-Forge-Access-Code required for public demo access.",
                    "request_id": request_id,
                },
                headers={"X-Request-ID": request_id},
            )

    try:
        response: Response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
        
        # Don't log healthz spam
        if request.url.path != "/healthz":
            logger.info(
                f"[{request_id}] {request.method} {request.url.path} -> {response.status_code} ({duration_ms:.2f}ms)"
            )
        return response
    except Exception as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.exception(f"[{request_id}] Unhandled error during {request.method} {request.url.path}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "message": "A forensic processing error occurred. Check system logs.",
                "request_id": request_id,
            },
            headers={"X-Request-ID": request_id},
        )


@app.get("/healthz", tags=["System"])
async def health_check():
    """Liveness and readiness probe for Cloud Run and local monitoring."""
    now_utc = datetime.now(timezone.utc)
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "track": settings.TRACK,
        "storage_mode": settings.STORAGE_MODE,
        "timestamp_utc": now_utc.isoformat(),
        "timestamp_unix": int(now_utc.timestamp()),
    }


@app.get("/api", tags=["System"])
async def api_root():
    """Root API information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "track": settings.TRACK,
        "docs_url": "/api/docs",
        "health_url": "/healthz",
        "storage_mode": settings.STORAGE_MODE,
        "disclaimer": "Forensic indicators provided with confidence levels. Results are computational aids, not final legal opinions.",
    }


# Mount API routers
app.include_router(cases_router)


# Mount built frontend static files if present (used in single-container Cloud Run deployment)
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

    @app.exception_handler(404)
    async def spa_fallback(request: Request, exc):
        """SPA fallback for client-side routing on page refresh."""
        if not request.url.path.startswith(("/api", "/healthz")):
            index_file = frontend_dist / "index.html"
            if index_file.exists():
                return FileResponse(str(index_file))
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
else:
    @app.get("/", tags=["System"])
    async def index_fallback():
        return {
            "message": "FORGE Backend API is running.",
            "health": "/healthz",
            "docs": "/api/docs",
            "frontend_status": "Not built yet or running in separate Vite dev server during local development.",
        }
