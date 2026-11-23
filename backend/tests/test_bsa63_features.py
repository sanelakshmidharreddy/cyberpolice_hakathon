import io
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.case_store import case_store
from app.core.storage import storage

client = TestClient(app)


def test_bsa63_case_creation_and_fields():
    payload = {
        "case_id": "TEST-CYB-2026-9999",
        "case_reference": "FIR-2026-TEST-9999",
        "investigator_name": "Inspector R. Verma",
        "offense_type": "Suspected Fabricated Media / Extortion Inquiry",
        "requestor_name": "Inspector R. Verma",
        "authority_basis": "Station Diary Entry / Seizure Memo",
        "examination_scope": "Check continuity and metadata anomalies",
        "producer_name": "Mahesh Kumar Sinha",
        "parentage_and_address": "S/o Devendra Sinha, Boring Road, Patna",
        "device_source_type": "DVR",
        "make_and_model": "Hikvision 8-Channel DVR",
        "color": "Black",
        "serial_or_imei": "SN: DEMO-DVR-988124",
        "lawful_control_role": "Maintained & Operated",
        "seized_at_ist": "18/11/2026 14:35 IST",
        "seizure_location": "Security Cabin, Commercial Complex",
        "collection_method": "Direct USB Export (Non-Forwarded)",
        "expert_name": "Dr. A. K. Sharma",
        "expert_designation": "Senior Scientific Officer (Cyber Forensics)",
        "lab_organization": "State Cyber Forensic Science Laboratory, Patna",
    }
    res = client.post("/api/cases", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["case_id"] == "TEST-CYB-2026-9999"
    assert data["producer_name"] == "Mahesh Kumar Sinha"
    assert data["device_source_type"] == "DVR"
    assert data["lawful_control_role"] == "Maintained & Operated"


def test_attach_sample_and_simulate_forward():
    # 1. Create a case
    res = client.post(
        "/api/cases",
        json={"investigator_name": "SI Ananya Deshmukh", "case_reference": "FIR-2026-FWD-001"},
    )
    assert res.status_code == 201
    case_id = res.json()["case_id"]

    # 2. Attach authentic sample
    att_res = client.post(f"/api/cases/{case_id}/attach-sample/demo_authentic_scene.jpg")
    assert att_res.status_code == 200
    source_file = att_res.json()
    assert source_file["original_name"] == "demo_authentic_scene.jpg"
    orig_sha = source_file["sha256_at_upload"]

    # 3. Simulate forward (re-compression + metadata strip)
    sim_res = client.post(
        f"/api/cases/{case_id}/simulate-forward",
        json={"source_file_id": source_file["file_id"]},
    )
    assert sim_res.status_code == 200
    fwd_file = sim_res.json()
    assert fwd_file["is_forward_simulation"] is True
    assert fwd_file["forward_source_hash"] == orig_sha
    # Hash MUST be altered due to recompression
    assert fwd_file["sha256_at_upload"] != orig_sha

    # 4. Appendix JSON export
    app_res = client.get(f"/api/cases/{case_id}/appendix.json")
    assert app_res.status_code == 200
    appendix = app_res.json()
    assert appendix["case_metadata"]["case_id"] == case_id
    assert len(appendix["case_metadata"]["files"]) == 2

    # 5. Court-ready PDF export
    pdf_res = client.get(f"/api/cases/{case_id}/report.pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert pdf_res.content.startswith(b"%PDF-")


def test_auto_purge_raw_file_lifecycle():
    # 1. Create case
    res = client.post(
        "/api/cases",
        json={"investigator_name": "Inspector S. Privacy", "case_reference": "FIR-2026-PRV-001"},
    )
    case_id = res.json()["case_id"]

    # 2. Upload file with auto_purge=true
    test_content = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + b"A" * 100
    up_res = client.post(
        f"/api/cases/{case_id}/files",
        files={"file": ("sensitive_evidence.jpg", test_content, "image/jpeg")},
        data={"auto_purge": "true"},
    )
    assert up_res.status_code == 201
    file_data = up_res.json()
    assert file_data["auto_purge"] is True
    file_id = file_data["file_id"]
    storage_path = Path(file_data["storage_path"])

    assert storage_path.exists()

    # 3. Trigger analysis (auto-purge deletes raw file at end of pipeline)
    trig_res = client.post(f"/api/cases/{case_id}/files/{file_id}/analyze")
    assert trig_res.status_code in (200, 202)

    # Wait or inspect directly via orchestrator
    import time
    for _ in range(30):
        c = case_store.get_case(case_id)
        f = next(item for item in c.files if item.file_id == file_id)
        if f.status in ("done", "failed"):
            break
        time.sleep(0.2)

    # Raw file was purged
    assert not storage_path.exists(), "Raw evidence file should be auto-purged from disk"
    # Metadata and hash remain intact in DB
    assert f.sha256_at_upload != ""
    assert f.status == "done"
