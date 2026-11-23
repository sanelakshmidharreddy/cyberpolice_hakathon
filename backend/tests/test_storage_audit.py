import hashlib
import io
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.audit import AuditLogger
from app.core.storage import LocalStorageProvider


@pytest.fixture
def client():
    return TestClient(app)


def test_storage_and_working_copy(tmp_path):
    storage = LocalStorageProvider(base_data_dir=tmp_path)
    sample_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 100  # Valid JPEG header
    stream = io.BytesIO(sample_bytes)

    case_id = "test-case-001"
    file_id = "test-file-001"
    storage_path, sha256, size = storage.save_evidence_stream(
        case_id, file_id, "evidence.jpg", stream
    )

    assert Path(storage_path).exists()
    assert size == len(sample_bytes)
    assert sha256 == hashlib.sha256(sample_bytes).hexdigest()

    # Working copy test: must create a separate copy in scratch space
    working_copy = storage.get_working_copy(storage_path, case_id, file_id)
    assert working_copy.exists()
    assert str(working_copy) != storage_path
    assert working_copy.read_bytes() == sample_bytes

    # Clean scratch
    storage.cleanup_scratch(case_id)
    assert not (tmp_path / "scratch" / case_id).exists()


def test_append_only_audit_logger(tmp_path):
    db_file = tmp_path / "test_audit.db"
    logger = AuditLogger(db_path=db_file)

    case_id = "case-audit-123"
    entry1 = logger.log(case_id, "CASE_CREATED", actor="Inspector Sharma")
    entry2 = logger.log(
        case_id,
        "UPLOADED",
        file_id="file-1",
        actor="Inspector Sharma",
        details={"name": "cctv.mp4"},
        sha256="abcd1234ef",
    )

    trail = logger.get_case_audit_trail(case_id)
    assert len(trail) == 2
    assert trail[0].action == "CASE_CREATED"
    assert trail[1].action == "UPLOADED"
    assert trail[1].sha256 == "abcd1234ef"


def test_case_api_workflow(client):
    # 1. Create a case
    create_res = client.post(
        "/api/cases",
        json={"investigator_name": "Inspector S. Kumar", "case_reference": "FIR-2026/042"},
    )
    assert create_res.status_code == 201
    case_data = create_res.json()
    case_id = case_data["case_id"]
    assert case_data["case_reference"] == "FIR-2026/042"

    # 2. Upload valid evidence file (JPEG)
    valid_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + b"\x00" * 50
    expected_hash = hashlib.sha256(valid_jpeg).hexdigest()

    upload_res = client.post(
        f"/api/cases/{case_id}/files",
        files={"file": ("crime_scene.jpg", valid_jpeg, "image/jpeg")},
    )
    assert upload_res.status_code == 201
    file_data = upload_res.json()
    assert file_data["original_name"] == "crime_scene.jpg"
    assert file_data["media_type"] == "image"
    assert file_data["sha256_at_upload"] == expected_hash

    # 3. Reject invalid file type (e.g. executable/plain text masquerading)
    invalid_file = b"MZ\x90\x00\x03\x00\x00\x00"  # DOS executable header
    bad_upload_res = client.post(
        f"/api/cases/{case_id}/files",
        files={"file": ("malicious.exe", invalid_file, "application/octet-stream")},
    )
    assert bad_upload_res.status_code == 400
    assert "Unsupported file type" in bad_upload_res.json()["detail"]

    # 4. Check case audit trail
    audit_res = client.get(f"/api/cases/{case_id}/audit")
    assert audit_res.status_code == 200
    trail = audit_res.json()
    actions = [e["action"] for e in trail]
    assert "CASE_CREATED" in actions
    assert "UPLOADED" in actions
