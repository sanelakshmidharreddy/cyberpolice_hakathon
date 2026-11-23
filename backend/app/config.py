from pathlib import Path
from typing import Literal, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration for FORGE."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "FORGE Digital Evidence Verification Platform"
    APP_VERSION: str = "0.1.0"
    TRACK: str = "Digital Forensics (PS-05, Cyber Hackathon 2026)"
    
    # Storage Mode: 'local' (SQLite + local disk) or 'gcp' (Firestore + GCS)
    STORAGE_MODE: Literal["local", "gcp"] = "local"
    
    # Local Storage Settings
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = Field(default_factory=lambda: (Path(__file__).resolve().parent.parent.parent / "data").resolve())
    
    # Cloud Settings
    GCS_BUCKET: Optional[str] = None
    PROJECT_ID: Optional[str] = None
    
    # Constraints & Timeouts
    MAX_LOCAL_MB: int = 500
    MODULE_TIMEOUT_SECONDS: int = 120
    
    # Security / Access Control for public demos
    DEMO_ACCESS_CODE: Optional[str] = None
    
    # Host & Port
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENVIRONMENT: str = "development"

    @property
    def evidence_dir(self) -> Path:
        """Read-only original evidence directory in local mode."""
        p = self.DATA_DIR / "evidence"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def artifacts_dir(self) -> Path:
        """Generated artifacts directory (heatmaps, waveforms, charts)."""
        p = self.DATA_DIR / "artifacts"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def scratch_dir(self) -> Path:
        """Scratch directory for working copies during forensic processing."""
        p = self.DATA_DIR / "scratch"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def db_path(self) -> Path:
        """Local SQLite database path."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        return self.DATA_DIR / "forge.db"


settings = Settings()
