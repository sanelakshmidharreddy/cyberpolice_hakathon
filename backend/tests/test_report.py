import io
import stat
from pathlib import Path
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.case_store import case_store
from app.core.audit import audit_logger
from app.core.models import Finding, FindingResult, ModuleResult, OverallVerdict, Verdict

client = TestClient(app)


def create_test_image_bytes() -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (120, 120), color=(50, 100, 150))
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def test_pdf_report_generation_and_integrity_verification():
    # 1. Create a case
    res_case = client.post(
        "/api/cases",
        json={"investigator_name": "Insp. Priya Sharma", "case_reference": "FIR-2026-PDF-001"},
    )
    assert res_case.status_code == 201
    case_data = res_case.json()
    case_id = case_data["case_id"]

    # 2. Upload an image
    img_bytes = create_test_image_bytes()
    res_upload = client.post(
        f"/api/cases/{case_id}/files",
        files={"file": ("evidence_doc.jpg", img_bytes, "image/jpeg")},
    )
    assert res_upload.status_code == 201
    file_id = res_upload.json()["file_id"]

    # 3. Attach a verdict & results
    ev_file = next(f for f in case_store.get_case(case_id).files if f.file_id == file_id)
    ev_file.verdict = Verdict(
        overall=OverallVerdict.AUTHENTIC,
        score=94.5,
        top_reasons=["Consistent metadata", "Error level analysis within uniform threshold"],
    )
    ev_file.results = {
        "image_metadata": ModuleResult(
            module="image_metadata",
            version="1.0.0",
            duration_ms=45,
            findings=[
                Finding(
                    module="image_metadata",
                    check_name="exif_editor_signature",
                    result=FindingResult.PASS,
                    confidence=0.95,
                    explanation="No known image editing software signature detected.",
                )
            ],
        )
    }

    # 4. Generate PDF Report
    res_pdf = client.get(f"/api/cases/{case_id}/report.pdf")
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert res_pdf.content.startswith(b"%PDF-")
    assert len(res_pdf.content) > 1000

    # 5. Verify that INTEGRITY_VERIFIED was recorded in audit log
    audit_trail = audit_logger.get_case_audit_trail(case_id)
    verified_entry = next((a for a in audit_trail if a.action == "INTEGRITY_VERIFIED"), None)
    assert verified_entry is not None
    assert verified_entry.file_id == file_id


def test_pdf_report_hash_tamper_detection():
    # 1. Create case & file
    res_case = client.post(
        "/api/cases",
        json={"investigator_name": "Insp. Vikramaditya", "case_reference": "FIR-2026-TAMPER-002"},
    )
    case_id = res_case.json()["case_id"]

    img_bytes = create_test_image_bytes()
    res_upload = client.post(
        f"/api/cases/{case_id}/files",
        files={"file": ("compromised_photo.jpg", img_bytes, "image/jpeg")},
    )
    file_id = res_upload.json()["file_id"]

    # 2. Tamper with the raw file on disk behind the scenes
    case = case_store.get_case(case_id)
    ev_file = next(f for f in case.files if f.file_id == file_id)
    raw_path = Path(ev_file.storage_path)

    # Temporarily remove read-only to simulate physical disk tampering
    raw_path.chmod(stat.S_IWRITE)
    with open(raw_path, "ab") as f:
        f.write(b"EXTRANEOUS_UNAUTHORIZED_BYTES")
    raw_path.chmod(stat.S_IREAD)

    # 3. Call PDF report generation
    res_pdf = client.get(f"/api/cases/{case_id}/report.pdf")
    assert res_pdf.status_code == 200
    assert res_pdf.content.startswith(b"%PDF-")

    # 4. Verify that INTEGRITY_FAILURE was caught and logged
    audit_trail = audit_logger.get_case_audit_trail(case_id)
    tamper_entry = next((a for a in audit_trail if a.action == "INTEGRITY_FAILURE"), None)
    assert tamper_entry is not None
    assert tamper_entry.file_id == file_id
    assert "Post-upload tampering detected" in tamper_entry.details.get("warning", "")
