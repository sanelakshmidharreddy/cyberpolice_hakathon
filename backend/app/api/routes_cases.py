import uuid
from typing import List, Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.core.audit import audit_logger
from app.core.case_store import case_store
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

router = APIRouter(prefix="/api/cases", tags=["Cases & Evidence"])


class CreateCaseRequest(BaseModel):
    investigator_name: str = Field(..., min_length=2, max_length=100)
    case_reference: str = Field(..., min_length=2, max_length=100)


class FinalizeUploadRequest(BaseModel):
    original_name: str
    storage_path: str
    size_bytes: int
    mime: str
    sha256: str


@router.post("", response_model=Case, status_code=status.HTTP_201_CREATED)
async def create_case(req: CreateCaseRequest):
    """Creates a new digital forensics case."""
    case = case_store.create_case(
        investigator_name=req.investigator_name,
        case_reference=req.case_reference,
    )
    audit_logger.log(
        case_id=case.case_id,
        action="CASE_CREATED",
        actor=req.investigator_name,
        details={"case_reference": req.case_reference},
    )
    return case


@router.get("", response_model=List[Case])
async def list_cases():
    """Lists all cases registered on this instance."""
    return case_store.list_cases()


@router.get("/{case_id}", response_model=Case)
async def get_case(case_id: str):
    """Retrieves full case details including all evidence files."""
    case = case_store.get_case(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' was not found.",
        )
    return case


@router.post("/{case_id}/upload-url")
async def get_upload_url(case_id: str, filename: str):
    """Returns direct upload instructions or V4 signed URL in GCP mode."""
    case = case_store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")

    file_id = str(uuid.uuid4())
    if settings.STORAGE_MODE == "gcp":
        # Signed V4 URL generation (wired in Phase 11)
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
        "message": "Local mode enabled. Submit multipart/form-data directly to direct_upload_endpoint.",
    }


@router.post("/{case_id}/files", response_model=EvidenceFile, status_code=status.HTTP_201_CREATED)
async def upload_evidence_file(
    case_id: str,
    file: UploadFile = File(...),
):
    """Streams uploaded evidence file, validates MIME by magic bytes, calculates SHA-256,
    stores read-only original, and logs immutable chain of custody audit record.
    """
    case = case_store.get_case(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case '{case_id}' not found.",
        )

    # Read first 32 bytes for magic byte verification
    header = await file.read(32)
    detected_mime = detect_mime_from_bytes(header, filename=file.filename or "")

    if not detected_mime or detected_mime not in ALLOWED_MIMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file type. Detected MIME: '{detected_mime or 'unknown'}'. "
                f"Allowed formats: {list(ALLOWED_MIMES.keys())}"
            ),
        )

    media_type = ALLOWED_MIMES[detected_mime]
    file_id = str(uuid.uuid4())

    # Rewind stream
    await file.seek(0)

    # Stream to storage while calculating SHA-256 and enforcing read-only permissions
    storage_path, sha256_upload, size_bytes = storage.save_evidence_stream(
        case_id=case_id,
        file_id=file_id,
        filename=file.filename or "evidence.bin",
        stream=file.file,
    )

    evidence_file = EvidenceFile(
        file_id=file_id,
        original_name=file.filename or "evidence.bin",
        media_type=media_type,
        size_bytes=size_bytes,
        mime=detected_mime,
        sha256_at_upload=sha256_upload,
        storage_path=storage_path,
        status=FileStatus.QUEUED,
    )

    case_store.add_file(case_id, evidence_file)

    # Immutable Audit Log Entry
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
        },
        sha256=sha256_upload,
    )

    return evidence_file


@router.post("/{case_id}/files/{file_id}/finalize", response_model=EvidenceFile)
async def finalize_upload(case_id: str, file_id: str, req: FinalizeUploadRequest):
    """Registers file metadata and logs UPLOADED audit entry after direct GCP signed URL upload."""
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
        details={
            "original_name": req.original_name,
            "media_type": media_type.value,
            "size_bytes": req.size_bytes,
            "mime": req.mime,
        },
        sha256=req.sha256,
    )
    return evidence_file


@router.get("/{case_id}/audit", response_model=List[AuditEntry])
async def get_case_audit(case_id: str):
    """Fetches the immutable chain-of-custody audit log for a case."""
    case = case_store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    return audit_logger.get_case_audit_trail(case_id)


@router.post("/{case_id}/files/{file_id}/analyze")
async def trigger_analysis(case_id: str, file_id: str):
    """Triggers background multi-modal forensic analysis on a working copy."""
    import asyncio
    from app.core.orchestrator import run_analysis_background

    case = case_store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")

    ev_file = next((f for f in case.files if f.file_id == file_id), None)
    if not ev_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found.")

    # Schedule background execution
    asyncio.create_task(run_analysis_background(case_id, file_id))

    return {
        "status": "scheduled",
        "case_id": case_id,
        "file_id": file_id,
        "media_type": ev_file.media_type.value,
        "message": "Forensic pipeline initialized in background. Track progress via status endpoint.",
    }


@router.get("/{case_id}/files/{file_id}/status")
async def get_analysis_status(case_id: str, file_id: str):
    """Returns live module progress (queued, running, done, failed) and overall status."""
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


@router.get("/{case_id}/files/{file_id}/results")
async def get_analysis_results(case_id: str, file_id: str):
    """Returns final synthesized Verdict, all module findings, and artifact paths."""
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
        "verdict": ev_file.verdict,
        "results": ev_file.results,
    }


@router.get("/{case_id}/artifacts/{file_id}/{artifact_name}")
async def get_artifact(case_id: str, file_id: str, artifact_name: str):
    """Serves generated visual and forensic artifacts (heatmaps, waveforms, timelines)."""
    artifact_path = settings.artifacts_dir / case_id / file_id / artifact_name
    if not artifact_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found.")

    media_type = "image/png"
    if artifact_name.endswith(".jpg") or artifact_name.endswith(".jpeg"):
        media_type = "image/jpeg"
    elif artifact_name.endswith(".pdf"):
        media_type = "application/pdf"

    return FileResponse(path=str(artifact_path), media_type=media_type, filename=artifact_name)


@router.get("/{case_id}/files/{file_id}/content")
async def get_evidence_content(case_id: str, file_id: str):
    """Serves original evidence file for preview in frontend viewers."""
    case = case_store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    ev_file = next((f for f in case.files if f.file_id == file_id), None)
    if not ev_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found.")
    path = storage.get_evidence_path(ev_file.storage_path)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence content not found on disk.")
    return FileResponse(path=str(path), media_type=ev_file.mime, filename=ev_file.original_name)


@router.get("/{case_id}/report.pdf")
async def generate_case_pdf_report(case_id: str):
    """Generates an official courtroom forensic report in PDF format with automatic
    cryptographic hash re-verification and Section 65B compliance.
    """
    from fastapi.responses import Response
    from app.core.hashing import compute_sha256_file
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

            if is_valid:
                audit_logger.log(
                    case_id=case_id,
                    file_id=f.file_id,
                    action="INTEGRITY_VERIFIED",
                    actor="FORGE Automated Report Engine",
                    details={"file_name": f.original_name, "verified_sha256": current_digest},
                    sha256=current_digest,
                )
            else:
                audit_logger.log(
                    case_id=case_id,
                    file_id=f.file_id,
                    action="INTEGRITY_FAILURE",
                    actor="FORGE Automated Report Engine",
                    details={
                        "file_name": f.original_name,
                        "upload_sha256": f.sha256_at_upload,
                        "current_sha256": current_digest,
                        "warning": "Post-upload tampering detected on stored evidence!",
                    },
                    sha256=current_digest,
                )
        else:
            verified_hashes[f.file_id] = ("FILE_NOT_FOUND", False)

    audit_trail = audit_logger.get_case_audit_trail(case_id)
    pdf_bytes = generate_pdf_report(case, audit_trail, verified_hashes)

    clean_ref = "".join(c if c.isalnum() or c in "-_" else "_" for c in case.case_reference)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="FORGE_Report_{clean_ref}.pdf"',
        },
    )


