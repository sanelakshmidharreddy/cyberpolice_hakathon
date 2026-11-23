import os
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
    auto_purge: bool = False
    is_forward_simulation: bool = False
    forward_source_hash: Optional[str] = None
    results: Optional[Dict[str, ModuleResult]] = None
    verdict: Optional[Verdict] = None


class Case(BaseModel):
    case_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    investigator_name: str
    case_reference: str
    
    # BSA 2023 Section 63 & Chain-of-Custody Particulars
    offense_type: Optional[str] = "Suspected Digital Evidence Tampering"
    requestor_name: Optional[str] = "Investigating Officer / Cyber PS"
    authority_basis: Optional[str] = "Station Diary Entry / Seizure Memo"
    examination_scope: Optional[str] = "Verification of authenticity, metadata integrity & temporal continuity"
    
    # BSA Section 63 Part A (Party & Device Particulars)
    producer_name: Optional[str] = "Not Specified"
    parentage_and_address: Optional[str] = "Not Specified"
    device_source_type: Optional[str] = "Mobile"  # Computer / Storage Media, DVR, Mobile, Flash Drive, CD/DVD, Server, Cloud, Other
    make_and_model: Optional[str] = "Unspecified Device"
    color: Optional[str] = "Black"
    serial_or_imei: Optional[str] = "SN/IMEI: Not Disclosed"
    lawful_control_role: Optional[str] = "Owned"  # Owned, Maintained, Managed, Operated
    
    # Custody & Acquisition
    seized_at_ist: Optional[str] = None
    seizure_location: Optional[str] = None
    collection_method: Optional[str] = "Direct Logical Copy"
    
    # BSA Section 63 Part B (Expert Particulars)
    expert_name: Optional[str] = "Dr. A. K. Sharma"
    expert_designation: Optional[str] = "Senior Scientific Officer (Digital Forensics)"
    lab_organization: Optional[str] = "State Cyber Forensic Laboratory / CCSU Bihar Police"

    files: List[EvidenceFile] = Field(default_factory=list)


class AuditEntry(BaseModel):
    id: Optional[int] = None
    timestamp_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    case_id: str
    file_id: Optional[str] = None
    action: str  # e.g. CASE_CREATED, UPLOADED, RAW_FILE_PURGED, ANALYSIS_STARTED, FORWARD_SIMULATED
    actor: str = "system"
    details: Dict[str, Any] = Field(default_factory=dict)
    sha256: Optional[str] = None


# Comprehensive MIME format mapping supporting smartphones and common forensics formats
ALLOWED_MIMES = {
    # Images
    "image/jpeg": MediaType.IMAGE,
    "image/jpg": MediaType.IMAGE,
    "image/png": MediaType.IMAGE,
    "image/tiff": MediaType.IMAGE,
    "image/webp": MediaType.IMAGE,
    "image/heic": MediaType.IMAGE,
    "image/heif": MediaType.IMAGE,
    "image/bmp": MediaType.IMAGE,
    
    # Videos
    "video/mp4": MediaType.VIDEO,
    "video/x-msvideo": MediaType.VIDEO,
    "video/quicktime": MediaType.VIDEO,
    "video/x-matroska": MediaType.VIDEO,
    "video/webm": MediaType.VIDEO,
    "video/mpeg": MediaType.VIDEO,
    "video/3gpp": MediaType.VIDEO,
    
    # Audio
    "audio/wav": MediaType.AUDIO,
    "audio/x-wav": MediaType.AUDIO,
    "audio/wave": MediaType.AUDIO,
    "audio/mpeg": MediaType.AUDIO,
    "audio/mp3": MediaType.AUDIO,
    "audio/mp4": MediaType.AUDIO,
    "audio/x-m4a": MediaType.AUDIO,
    "audio/m4a": MediaType.AUDIO,
    "audio/ogg": MediaType.AUDIO,
    "audio/flac": MediaType.AUDIO,
    "audio/aac": MediaType.AUDIO,
}

# Extension to MIME fallback dictionary
EXTENSION_MIMES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".heic": "image/heic",
    ".heif": "image/heif",
    ".bmp": "image/bmp",
    ".mp4": "video/mp4",
    ".avi": "video/x-msvideo",
    ".mov": "video/quicktime",
    ".mkv": "video/x-matroska",
    ".webm": "video/webm",
    ".3gp": "video/3gpp",
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/x-m4a",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".aac": "audio/aac",
}


def detect_mime_from_bytes(header_bytes: bytes, filename: str = "") -> Optional[str]:
    """Detect MIME type by inspecting magic header bytes with filename extension fallback."""
    ext = os.path.splitext(filename.lower())[1] if filename else ""

    if header_bytes:
        # JPEG: FF D8 FF
        if header_bytes.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"

        # PNG: 89 50 4E 47 0D 0A 1A 0A
        if header_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"

        # WEBP: RIFF....WEBP
        if header_bytes.startswith(b"RIFF") and len(header_bytes) >= 12 and header_bytes[8:12] == b"WEBP":
            return "image/webp"

        # TIFF: II*\0 or MM\0*
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

        # MP3 ID3 header (ID3)
        if header_bytes.startswith(b"ID3") or (len(header_bytes) >= 2 and header_bytes[0] == 0xFF and (header_bytes[1] & 0xE0) == 0xE0):
            return "audio/mpeg"

        # MP4 / QuickTime / M4A (ftyp / moov)
        if len(header_bytes) >= 8 and (header_bytes[4:8] == b"ftyp" or header_bytes[4:8] == b"moov"):
            if ext in [".m4a", ".aac"]:
                return "audio/x-m4a"
            if ext == ".mov":
                return "video/quicktime"
            return "video/mp4"

        # OGG container (OggS)
        if header_bytes.startswith(b"OggS"):
            return "audio/ogg"

    # Fallback to extension matching
    if ext and ext in EXTENSION_MIMES:
        return EXTENSION_MIMES[ext]

    return None
