import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class MediaType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


class FileStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class FindingResult(str, Enum):
    PASS = "pass"
    SUSPICIOUS = "suspicious"
    TAMPERED = "tampered"
    NOT_APPLICABLE = "not_applicable"
    INCONCLUSIVE = "inconclusive"


class OverallVerdict(str, Enum):
    AUTHENTIC = "AUTHENTIC"
    SUSPICIOUS = "SUSPICIOUS"
    LIKELY_TAMPERED = "LIKELY_TAMPERED"
    INCONCLUSIVE = "INCONCLUSIVE"


class Finding(BaseModel):
    module: str
    check_name: str
    result: FindingResult
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: str
    evidence: Dict[str, Any] = Field(default_factory=dict)
    artifact_paths: List[str] = Field(default_factory=list)


class ModuleResult(BaseModel):
    module: str
    version: str = "1.0.0"
    duration_ms: float = 0.0
    findings: List[Finding] = Field(default_factory=list)
    error: Optional[str] = None


class Verdict(BaseModel):
    overall: OverallVerdict
    score: float = Field(ge=0.0, le=100.0)
    top_reasons: List[str] = Field(default_factory=list)
    per_module_scores: Dict[str, float] = Field(default_factory=dict)


class EvidenceFile(BaseModel):
    file_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_name: str
    media_type: MediaType
    size_bytes: int
    mime: str
    sha256_at_upload: str
    sha256_at_report: Optional[str] = None
    storage_path: str
    status: FileStatus = FileStatus.QUEUED
    uploaded_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    results: Optional[Dict[str, ModuleResult]] = None
    verdict: Optional[Verdict] = None


class Case(BaseModel):
    case_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    investigator_name: str
    case_reference: str
    files: List[EvidenceFile] = Field(default_factory=list)


class AuditEntry(BaseModel):
    id: Optional[int] = None
    timestamp_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    case_id: str
    file_id: Optional[str] = None
    action: str  # e.g. UPLOADED, ANALYSIS_STARTED, ANALYSIS_COMPLETED, INTEGRITY_VERIFIED, INTEGRITY_FAILURE
    actor: str = "system"
    details: Dict[str, Any] = Field(default_factory=dict)
    sha256: Optional[str] = None


# MIME magic byte validation helpers
ALLOWED_MIMES = {
    # Images
    "image/jpeg": MediaType.IMAGE,
    "image/png": MediaType.IMAGE,
    "image/tiff": MediaType.IMAGE,
    "image/heic": MediaType.IMAGE,
    "image/heif": MediaType.IMAGE,
    # Videos
    "video/mp4": MediaType.VIDEO,
    "video/x-msvideo": MediaType.VIDEO,
    "video/quicktime": MediaType.VIDEO,
    "video/x-matroska": MediaType.VIDEO,
    # Audio
    "audio/wav": MediaType.AUDIO,
    "audio/x-wav": MediaType.AUDIO,
    "audio/mpeg": MediaType.AUDIO,
    "audio/mp3": MediaType.AUDIO,
    "audio/mp4": MediaType.AUDIO,
    "audio/x-m4a": MediaType.AUDIO,
    "audio/ogg": MediaType.AUDIO,
    "audio/flac": MediaType.AUDIO,
}


def detect_mime_from_bytes(header_bytes: bytes, filename: str = "") -> Optional[str]:
    """Detect MIME type by inspecting magic header bytes with filename extension fallback."""
    if not header_bytes:
        return None
        
    # JPEG: FF D8 FF
    if header_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
        
    # PNG: 89 50 4E 47 0D 0A 1A 0A
    if header_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
        
    # TIFF: II*\0 (little endian) or MM\0* (big endian)
    if header_bytes.startswith(b"II*\x00") or header_bytes.startswith(b"MM\x00*"):
        return "image/tiff"
        
    # RIFF container (WAV or AVI)
    if header_bytes.startswith(b"RIFF") and len(header_bytes) >= 12:
        riff_type = header_bytes[8:12]
        if riff_type == b"WAVE":
            return "audio/wav"
        if riff_type == b"AVI ":
            return "video/x-msvideo"
            
    # Matroska / MKV (1A 45 DF A3)
    if header_bytes.startswith(b"\x1a\x45\xdf\xa3"):
        return "video/x-matroska"
        
    # FLAC (fLaC)
    if header_bytes.startswith(b"fLaC"):
        return "audio/flac"
        
    # OGG (OggS)
    if header_bytes.startswith(b"OggS"):
        return "audio/ogg"
        
    # MP3 (ID3v2 or frame sync 0xFF 0xFB/0xF3/0xF2)
    if header_bytes.startswith(b"ID3") or (len(header_bytes) >= 2 and header_bytes[0] == 0xff and (header_bytes[1] & 0xe0) == 0xe0):
        return "audio/mpeg"
        
    # MP4 / MOV / M4A / HEIC (ftyp atom check)
    if len(header_bytes) >= 12 and header_bytes[4:8] == b"ftyp":
        major_brand = header_bytes[8:12].lower()
        if major_brand in (b"heic", b"heix", b"hevc", b"mif1", b"msf1"):
            return "image/heic"
        if major_brand in (b"m4a ", b"m4b "):
            return "audio/x-m4a"
        if major_brand in (b"qt  ", b"moov"):
            return "video/quicktime"
        return "video/mp4"

    # Fallback to file extension mapping for edge formats
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    ext_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "tif": "image/tiff",
        "tiff": "image/tiff",
        "heic": "image/heic",
        "mp4": "video/mp4",
        "avi": "video/x-msvideo",
        "mov": "video/quicktime",
        "mkv": "video/x-matroska",
        "wav": "audio/wav",
        "mp3": "audio/mpeg",
        "m4a": "audio/x-m4a",
        "ogg": "audio/ogg",
        "flac": "audio/flac",
    }
    return ext_map.get(ext)
