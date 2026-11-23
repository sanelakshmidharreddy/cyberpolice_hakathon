from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.models import (
    Finding,
    FindingResult,
    ModuleResult,
    OverallVerdict,
)
from app.core.scoring import compute_verdict
from app.core.orchestrator import analyze_evidence_file_sync

SAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "samples"


@pytest.fixture
def client():
    return TestClient(app)


def test_scoring_authentic():
    results = {
        "image_metadata": ModuleResult(
            module="image_metadata",
            findings=[
                Finding(
                    module="image_metadata",
                    check_name="exif_presence",
                    result=FindingResult.PASS,
                    confidence=0.90,
                    explanation="EXIF headers authentic.",
                )
            ],
        ),
        "image_ela": ModuleResult(
            module="image_ela",
            findings=[
                Finding(
                    module="image_ela",
                    check_name="ela_heatmap",
                    result=FindingResult.PASS,
                    confidence=0.88,
                    explanation="Error levels uniform.",
                )
            ],
        ),
    }

    verdict = compute_verdict(results)
    assert verdict.overall == OverallVerdict.AUTHENTIC
    assert verdict.score < 20.0
    assert len(verdict.top_reasons) > 0


def test_scoring_tampered():
    results = {
        "image_metadata": ModuleResult(
            module="image_metadata",
            findings=[
                Finding(
                    module="image_metadata",
                    check_name="editing_software",
                    result=FindingResult.TAMPERED,
                    confidence=0.95,
                    explanation="Photoshop software signature identified.",
                )
            ],
        )
    }

    verdict = compute_verdict(results)
    assert verdict.overall == OverallVerdict.LIKELY_TAMPERED
    assert verdict.score >= 60.0
    assert any("Photoshop" in r for r in verdict.top_reasons)


def test_scoring_suspicious():
    results = {
        "image_metadata": ModuleResult(
            module="image_metadata",
            findings=[
                Finding(
                    module="image_metadata",
                    check_name="exif_presence",
                    result=FindingResult.SUSPICIOUS,
                    confidence=0.70,
                    explanation="Metadata missing or scrubbed.",
                )
            ],
        )
    }

    verdict = compute_verdict(results)
    assert verdict.overall == OverallVerdict.SUSPICIOUS
    assert 20.0 <= verdict.score <= 60.0


def test_end_to_end_orchestration_flow(client):
    # 1. Create case
    case_res = client.post(
        "/api/cases",
        json={"investigator_name": "Forensic Officer Verma", "case_reference": "CR-2026/99"},
    )
    assert case_res.status_code == 201
    case_id = case_res.json()["case_id"]

    # 2. Upload spliced image sample
    spliced_file = SAMPLES_DIR / "image_spliced.jpg"
    assert spliced_file.exists()

    with open(spliced_file, "rb") as f:
        file_bytes = f.read()

    upload_res = client.post(
        f"/api/cases/{case_id}/files",
        files={"file": ("evidence_spliced.jpg", file_bytes, "image/jpeg")},
    )
    assert upload_res.status_code == 201
    file_id = upload_res.json()["file_id"]

    # 3. Synchronously run analysis on working copy
    analyze_evidence_file_sync(case_id, file_id)

    # 4. Check status and results
    status_res = client.get(f"/api/cases/{case_id}/files/{file_id}/status")
    assert status_res.status_code == 200
    assert status_res.json()["overall_status"] == "done"

    results_res = client.get(f"/api/cases/{case_id}/files/{file_id}/results")
    assert results_res.status_code == 200
    results_data = results_res.json()
    assert results_data["status"] == "done"
    assert results_data["verdict"]["overall"] == "LIKELY_TAMPERED"
    assert "image_metadata" in results_data["results"]
    assert "image_ela" in results_data["results"]

    # 5. Verify audit log captures both start and completion
    audit_res = client.get(f"/api/cases/{case_id}/audit")
    assert audit_res.status_code == 200
    actions = [e["action"] for e in audit_res.json()]
    assert "ANALYSIS_STARTED" in actions
    assert "ANALYSIS_COMPLETED" in actions
