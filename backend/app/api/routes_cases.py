import asyncio
import io
import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from app.config import settings
from app.core.audit import audit_logger
from app.core.case_store import case_store
from app.core.hashing import compute_sha256_file
from app.core.models import (
    ALLOWED_MIMES,
    AuditEntry,
    Case,
    EvidenceFile,
    FileStatus,
    MediaType,
    detect_mime_from_bytes,
)
from app.core.storage import storage

router = APIRouter(tags=["Cases & Evidence"])


class CreateCaseRequest(BaseModel):
    case_id: Optional[str] = None
    investigator_name: str = Field(..., min_length=2, max_length=150)
    case_reference: str = Field(..., min_length=2, max_length=150)
    
    # BSA 2023 Section 63 Particulars
    offense_type: Optional[str] = None
    requestor_name: Optional[str] = None
    authority_basis: Optional[str] = None
    examination_scope: Optional[str] = None
    
    # BSA Part A (Party & Device Particulars)
    producer_name: Optional[str] = None
    parentage_and_address: Optional[str] = None
    device_source_type: Optional[str] = None
    make_and_model: Optional[str] = None
    color: Optional[str] = None
    serial_or_imei: Optional[str] = None
    lawful_control_role: Optional[str] = None
    
    # Custody & Acquisition
    seized_at_ist: Optional[str] = None
    seizure_location: Optional[str] = None
    collection_method: Optional[str] = None
    
    # BSA Part B (Expert Particulars)
    expert_name: Optional[str] = "Dr. A. K. Sharma"
    expert_designation: Optional[str] = "Senior Scientific Officer (Digital Forensics)"
    lab_organization: Optional[str] = "State Cyber Forensic Laboratory / CCSU Bihar Police"


class FinalizeUploadRequest(BaseModel):
    original_name: str
    storage_path: str
    size_bytes: int
    mime: str
    sha256: str


class SimulateForwardRequest(BaseModel):
    source_file_id: Optional[str] = None
    sample_filename: Optional[str] = None


# ------------------------------------------------------------------------------
# 1. SAMPLE FIXTURES DISCOVERY & ATTACHMENT
# ------------------------------------------------------------------------------

@router.get("/samples")
async def list_available_samples():
    """Lists real authentic and tampered forensic fixtures available in samples/."""
    samples_dir = settings.BASE_DIR / "samples"
    if not samples_dir.exists():
        return []

    results = []
    for p in samples_dir.glob("*.*"):
        if p.name.startswith("demo_") or p.name in ["image_original.jpg", "image_spliced.jpg", "cctv_original.mp4", "audio_original.wav"]:
            size_bytes = p.stat().st_size
            ext = p.suffix.lower()
            mtype = "image" if ext in [".jpg", ".jpeg", ".png"] else "video" if ext in [".mp4", ".avi"] else "audio" if ext in [".wav", ".mp3"] else "other"
            
            is_tampered = "tampered" in p.name or "splice" in p.name or "cut" in p.name or "dup" in p.name
            desc = (
                "Tampered evidence fixture demonstrating localized splicing, frame deletion, or ENF jump."
                if is_tampered
                else "Authentic pristine control capture with intact original metadata & temporal continuity."
            )
            results.append({
                "filename": p.name,
                "media_type": mtype,
                "size_bytes": size_bytes,
                "is_tampered": is_tampered,
                "description": desc,
            })
    return results


@router.post("/cases/{case_id}/attach-sample/{filename}")
async def attach_sample_file(case_id: str, filename: str):
    """Loads a verified sample file from samples/ directly into the case."""
    case = case_store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")

    sample_path = settings.BASE_DIR / "samples" / filename
    if not sample_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sample '{filename}' not found on server.")

    with open(sample_path, "rb") as f:
        header = f.read(32)
        detected_mime = detect_mime_from_bytes(header, filename=filename) or "application/octet-stream"
        f.seek(0)

        media_type = ALLOWED_MIMES.get(detected_mime, MediaType.IMAGE)
        file_id = str(uuid.uuid4())

        storage_path, sha256_upload, size_bytes = storage.save_evidence_stream(
            case_id=case_id,
            file_id=file_id,
            filename=filename,
            stream=f,
        )

    evidence_file = EvidenceFile(
        file_id=file_id,
        original_name=filename,
        media_type=media_type,
        size_bytes=size_bytes,
        mime=detected_mime,
        sha256_at_upload=sha256_upload,
        storage_path=storage_path,
        status=FileStatus.QUEUED,
    )
    case_store.add_file(case_id, evidence_file)

    audit_logger.log(
        case_id=case_id,
        file_id=file_id,
        action="SAMPLE_ATTACHED",
        actor=case.investigator_name,
        details={"filename": filename, "media_type": media_type.value, "size_bytes": size_bytes},
        sha256=sha256_upload,
    )

    # Automatically trigger analysis for seamless demo workflow
    from app.core.orchestrator import run_analysis_background
    asyncio.create_task(run_analysis_background(case_id, file_id))

    return evidence_file


# ------------------------------------------------------------------------------
# 2. MESSAGING FORWARD SIMULATION (WHATSAPP/TELEGRAM RE-COMPRESSION DEMO)
# ------------------------------------------------------------------------------

@router.post("/cases/{case_id}/simulate-forward")
async def simulate_messaging_forward(case_id: str, req: SimulateForwardRequest):
    """Simulates WhatsApp/messaging re-compression and EXIF stripping over evidence,
    demonstrating why forwarded media fails BSA Section 63 statutory integrity.
    """
    case = case_store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")

    # Locate source file
    source_file: Optional[EvidenceFile] = None
    if req.source_file_id:
        source_file = next((f for f in case.files if f.file_id == req.source_file_id), None)
    if not source_file and case.files:
        source_file = case.files[0]

    scratch_sub = settings.scratch_dir / f"fwd_{uuid.uuid4().hex[:8]}"
    scratch_sub.mkdir(parents=True, exist_ok=True)

    if source_file:
        src_path = storage.get_evidence_path(source_file.storage_path)
        base_name = source_file.original_name
        orig_sha = source_file.sha256_at_upload
    else:
        # Fallback to authentic demo image
        src_path = settings.BASE_DIR / "samples" / "demo_authentic_scene.jpg"
        base_name = "demo_authentic_scene.jpg"
        orig_sha = "N/A"

    if not src_path.exists():
        raise HTTPException(status_code=400, detail="Source file for forward simulation not found.")

    out_name = f"forwarded_{base_name}"
    out_scratch = scratch_sub / out_name

    # Run real server-side re-compression to strip EXIF and alter SHA-256
    try:
        from PIL import Image
        with Image.open(src_path) as img:
            rgb = img.convert("RGB")
            # Save without EXIF at typical WhatsApp JPEG quality 68
            rgb.save(str(out_scratch), "JPEG", quality=68)
            detected_mime = "image/jpeg"
            media_type = MediaType.IMAGE
    except Exception:
        # Fallback: Copy and modify trailing byte to guarantee distinct cryptographic hash
        with open(src_path, "rb") as rf:
            b = bytearray(rf.read())
        b.extend(b"\x00\x00WHATSAPP_FORWARD_SIMULATION\x00")
        with open(out_scratch, "wb") as wf:
            wf.write(b)
        detected_mime = "application/octet-stream"
        media_type = MediaType.IMAGE

    # Save to evidence store as a real evidence item
    new_file_id = str(uuid.uuid4())
    with open(out_scratch, "rb") as f_in:
        storage_path, sha256_fwd, size_bytes = storage.save_evidence_stream(
            case_id=case_id,
            file_id=new_file_id,
            filename=out_name,
            stream=f_in,
        )

    # Cleanup scratch
    shutil.rmtree(scratch_sub, ignore_errors=True)

    fwd_evidence_file = EvidenceFile(
        file_id=new_file_id,
        original_name=out_name,
        media_type=media_type,
        size_bytes=size_bytes,
        mime=detected_mime,
        sha256_at_upload=sha256_fwd,
        storage_path=storage_path,
        status=FileStatus.QUEUED,
        is_forward_simulation=True,
        forward_source_hash=orig_sha,
    )
    case_store.add_file(case_id, fwd_evidence_file)

    audit_logger.log(
        case_id=case_id,
        file_id=new_file_id,
        action="FORWARD_SIMULATED",
        actor="FORGE Forward Simulator",
        details={
            "source_file": base_name,
            "original_sha256": orig_sha,
            "forwarded_sha256": sha256_fwd,
            "explanation": "Simulated social messaging forward re-compression: EXIF metadata stripped, hash changed.",
        },
        sha256=sha256_fwd,
    )

    from app.core.orchestrator import run_analysis_background
    asyncio.create_task(run_analysis_background(case_id, new_file_id))

    return fwd_evidence_file


# ------------------------------------------------------------------------------
# 3. CASE INTAKE & MANAGEMENT
# ------------------------------------------------------------------------------

@router.post("/cases", response_model=Case, status_code=status.HTTP_201_CREATED)
@router.post("/cases/", response_model=Case, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_case(req: CreateCaseRequest):
    """Creates a new digital forensics case with BSA 2023 Section 63 particulars."""
    case = case_store.create_case(
        investigator_name=req.investigator_name,
        case_reference=req.case_reference,
        case_id=req.case_id,
        offense_type=req.offense_type,
        requestor_name=req.requestor_name,
        authority_basis=req.authority_basis,
        examination_scope=req.examination_scope,
        producer_name=req.producer_name,
        parentage_and_address=req.parentage_and_address,
        device_source_type=req.device_source_type,
        make_and_model=req.make_and_model,
        color=req.color,
        serial_or_imei=req.serial_or_imei,
        lawful_control_role=req.lawful_control_role,
        seized_at_ist=req.seized_at_ist,
        seizure_location=req.seizure_location,
        collection_method=req.collection_method,
        expert_name=req.expert_name,
        expert_designation=req.expert_designation,
        lab_organization=req.lab_organization,
    )
    audit_logger.log(
        case_id=case.case_id,
        action="CASE_CREATED",
        actor=req.investigator_name,
        details={
            "case_reference": req.case_reference,
            "offense_type": case.offense_type,
            "device": f"{case.make_and_model} ({case.device_source_type})",
        },
    )
    return case


@router.get("/cases", response_model=List[Case])
@router.get("/cases/", response_model=List[Case], include_in_schema=False)
async def list_cases():
    """Lists all cases registered on this instance."""
    return case_store.list_cases()


@router.get("/cases/{case_id}", response_model=Case)
@router.get("/cases/{case_id}/", response_model=Case, include_in_schema=False)
async def get_case(case_id: str):
    """Retrieves full case details including all evidence files."""
    case = case_store.get_case(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' was not found.",
        )
    return case


@router.post("/cases/{case_id}/upload-url")
async def get_upload_url(case_id: str, filename: str):
    """Returns direct upload instructions or V4 signed URL in GCP mode."""
    case = case_store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")

    file_id = str(uuid.uuid4())
    if settings.STORAGE_MODE == "gcp":
        return {
            "mode": "gcp",
            "file_id": file_id,
            "upload_url": f"https://storage.googleapis.com/{settings.GCS_BUCKET}/evidence/{case_id}/{file_id}",
            "method": "PUT",
        }

    return {
        "mode": "local",
        "file_id": file_id,
        "direct_upload_endpoint": f"/api/cases/{case_id}/files",
        "message": "Local mode enabled. Submit multipart/form-data directly.",
    }


@router.post("/cases/{case_id}/files", response_model=EvidenceFile, status_code=status.HTTP_201_CREATED)
@router.post("/cases/{case_id}/files/", response_model=EvidenceFile, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def upload_evidence_file(
    case_id: str,
    file: UploadFile = File(...),
    auto_purge: bool = Form(False),
):
    """Streams uploaded evidence file directly in chunks, calculates SHA-256 pre-normalization,
    validates MIME, stores read-only original, and logs immutable audit record.
    """
    case = case_store.get_case(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case '{case_id}' not found.",
        )

    file_id = str(uuid.uuid4())
    scratch_chunk_path = settings.scratch_dir / f"up_{file_id}.tmp"

    import hashlib
    hasher = hashlib.sha256()
    size_bytes = 0
    header_bytes = b""

    # Chunked streaming to scratch disk (avoids full file loading into RAM)
    try:
        with open(scratch_chunk_path, "wb") as f_tmp:
            while chunk := await file.read(65536):
                if len(header_bytes) < 32:
                    header_bytes += chunk[: 32 - len(header_bytes)]
                hasher.update(chunk)
                size_bytes += len(chunk)
                f_tmp.write(chunk)
    except Exception as e:
        if scratch_chunk_path.exists():
            scratch_chunk_path.unlink()
        raise HTTPException(status_code=500, detail=f"Upload streaming error: {str(e)}")

    sha256_upload = hasher.hexdigest().lower()
    detected_mime = detect_mime_from_bytes(header_bytes, filename=file.filename or "")

    if not detected_mime or detected_mime not in ALLOWED_MIMES:
        if scratch_chunk_path.exists():
            scratch_chunk_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Detected format: '{detected_mime or 'unknown'}'. Supported: common image, audio & video formats.",
        )

    media_type = ALLOWED_MIMES[detected_mime]

    # Save to read-only evidence store
    with open(scratch_chunk_path, "rb") as f_tmp:
        storage_path, _, _ = storage.save_evidence_stream(
            case_id=case_id,
            file_id=file_id,
            filename=file.filename or "evidence.bin",
            stream=f_tmp,
        )

    if scratch_chunk_path.exists():
        scratch_chunk_path.unlink()

    evidence_file = EvidenceFile(
        file_id=file_id,
        original_name=file.filename or "evidence.bin",
        media_type=media_type,
        size_bytes=size_bytes,
        mime=detected_mime,
        sha256_at_upload=sha256_upload,
        storage_path=storage_path,
        status=FileStatus.QUEUED,
        auto_purge=auto_purge,
    )
    case_store.add_file(case_id, evidence_file)

    audit_logger.log(
        case_id=case_id,
        file_id=file_id,
        action="UPLOADED",
        actor=case.investigator_name,
        details={
            "original_name": evidence_file.original_name,
            "media_type": evidence_file.media_type.value,
            "size_bytes": size_bytes,
            "mime": detected_mime,
            "auto_purge": auto_purge,
        },
        sha256=sha256_upload,
    )

    return evidence_file


@router.post("/cases/{case_id}/files/{file_id}/finalize", response_model=EvidenceFile)
async def finalize_upload(case_id: str, file_id: str, req: FinalizeUploadRequest):
    case = case_store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")

    if req.mime not in ALLOWED_MIMES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported MIME.")

    media_type = ALLOWED_MIMES[req.mime]
    evidence_file = EvidenceFile(
        file_id=file_id,
        original_name=req.original_name,
        media_type=media_type,
        size_bytes=req.size_bytes,
        mime=req.mime,
        sha256_at_upload=req.sha256,
        storage_path=req.storage_path,
        status=FileStatus.QUEUED,
    )
    case_store.add_file(case_id, evidence_file)
    audit_logger.log(
        case_id=case_id,
        file_id=file_id,
        action="UPLOADED",
        actor=case.investigator_name,
        details={"original_name": req.original_name, "media_type": media_type.value, "size_bytes": req.size_bytes},
        sha256=req.sha256,
    )
    return evidence_file


@router.get("/cases/{case_id}/audit", response_model=List[AuditEntry])
async def get_case_audit(case_id: str):
    case = case_store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    return audit_logger.get_case_audit_trail(case_id)


@router.post("/cases/{case_id}/files/{file_id}/analyze")
async def trigger_analysis(case_id: str, file_id: str):
    from app.core.orchestrator import run_analysis_background
    case = case_store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    ev_file = next((f for f in case.files if f.file_id == file_id), None)
    if not ev_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found.")

    asyncio.create_task(run_analysis_background(case_id, file_id))
    return {
        "status": "scheduled",
        "case_id": case_id,
        "file_id": file_id,
        "media_type": ev_file.media_type.value,
        "message": "Forensic pipeline scheduled in background.",
    }


@router.get("/cases/{case_id}/files/{file_id}/status")
async def get_analysis_status(case_id: str, file_id: str):
    from app.core.orchestrator import get_live_status
    case = case_store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    ev_file = next((f for f in case.files if f.file_id == file_id), None)
    if not ev_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found.")

    return {
        "file_id": file_id,
        "overall_status": ev_file.status.value,
        "modules": get_live_status(file_id),
    }


@router.get("/cases/{case_id}/files/{file_id}/results")
async def get_analysis_results(case_id: str, file_id: str):
    case = case_store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    ev_file = next((f for f in case.files if f.file_id == file_id), None)
    if not ev_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found.")

    if ev_file.status != FileStatus.DONE:
        return {
            "file_id": file_id,
            "status": ev_file.status.value,
            "message": "Analysis is currently running or queued.",
            "verdict": None,
            "results": None,
        }

    return {
        "file_id": file_id,
        "status": ev_file.status.value,
        "sha256_at_upload": ev_file.sha256_at_upload,
        "is_forward_simulation": ev_file.is_forward_simulation,
        "forward_source_hash": ev_file.forward_source_hash,
        "verdict": ev_file.verdict,
        "results": ev_file.results,
    }


@router.get("/cases/{case_id}/artifacts/{file_id}/{artifact_name}")
async def get_artifact(case_id: str, file_id: str, artifact_name: str):
    artifact_path = settings.artifacts_dir / case_id / file_id / artifact_name
    if not artifact_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found.")

    media_type = "image/png"
    if artifact_name.endswith(".jpg") or artifact_name.endswith(".jpeg"):
        media_type = "image/jpeg"
    elif artifact_name.endswith(".pdf"):
        media_type = "application/pdf"

    return FileResponse(path=str(artifact_path), media_type=media_type, filename=artifact_name)


@router.get("/cases/{case_id}/files/{file_id}/content")
async def get_evidence_content(case_id: str, file_id: str):
    case = case_store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    ev_file = next((f for f in case.files if f.file_id == file_id), None)
    if not ev_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found.")
    path = storage.get_evidence_path(ev_file.storage_path)
    if not path.exists():
        if ev_file.auto_purge:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Raw evidence file was auto-purged per case privacy policy. Forensic hashes and findings remain recorded.",
            )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence content not found on disk (may have expired on server restart).")
    return FileResponse(path=str(path), media_type=ev_file.mime, filename=ev_file.original_name)


# ------------------------------------------------------------------------------
# 4. COURTROOM PDF REPORT & TECHNICAL JSON APPENDIX
# ------------------------------------------------------------------------------

@router.get("/cases/{case_id}/report.pdf")
@router.get("/cases/{case_id}/report.pdf/", include_in_schema=False)
async def generate_case_pdf_report(case_id: str):
    """Generates an official courtroom forensic report in PDF format adhering to
    Bharatiya Sakshya Adhiniyam (BSA), 2023 Section 63(4)(c) and ISO/IEC 27037:2012.
    """
    from app.report.pdf_report import generate_pdf_report

    case = case_store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")

    verified_hashes = {}
    for f in case.files:
        path = storage.get_evidence_path(f.storage_path)
        if path.exists():
            current_digest = compute_sha256_file(path)
            is_valid = current_digest.lower() == f.sha256_at_upload.lower()
            f.sha256_at_report = current_digest
            verified_hashes[f.file_id] = (current_digest, is_valid)
            action = "INTEGRITY_VERIFIED" if is_valid else "INTEGRITY_FAILURE"
            details = {"verified_sha256": current_digest, "match": is_valid}
            if not is_valid:
                details["warning"] = "Post-upload tampering detected: SHA-256 hash mismatch."
            audit_logger.log(
                case_id=case_id,
                file_id=f.file_id,
                action=action,
                actor="FORGE Report Engine",
                details=details,
                sha256=current_digest,
            )
        else:
            # If auto-purged or expired, report upload hash
            verified_hashes[f.file_id] = (f.sha256_at_upload, True)

    audit_trail = audit_logger.get_case_audit_trail(case_id)
    pdf_bytes = generate_pdf_report(case, audit_trail, verified_hashes)

    clean_ref = "".join(c if c.isalnum() or c in "-_" else "_" for c in case.case_reference)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="FORGE_BSA63_Report_{clean_ref}.pdf"',
        },
    )


@router.get("/cases/{case_id}/appendix.json")
@router.get("/cases/{case_id}/appendix.json/", include_in_schema=False)
async def download_technical_appendix_json(case_id: str):
    """Provides raw technical data, findings dictionaries, artifact pointers,
    and chain of custody logs as an exportable JSON appendix.
    """
    case = case_store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")

    audit_trail = audit_logger.get_case_audit_trail(case_id)

    payload = {
        "forge_platform_version": settings.APP_VERSION,
        "track": settings.TRACK,
        "statutory_standard": "Bharatiya Sakshya Adhiniyam, 2023 (Section 63) & SWGDE 18-Q-002",
        "case_metadata": case.model_dump(),
        "audit_trail": [a.model_dump() for a in audit_trail],
    }

    clean_ref = "".join(c if c.isalnum() or c in "-_" else "_" for c in case.case_reference)
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="FORGE_Technical_Appendix_{clean_ref}.json"',
        },
    )
