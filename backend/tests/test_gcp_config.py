from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from app.core.gcp_storage import GCPStorageProvider
from app.core.storage import sanitize_filename, get_storage, LocalStorageProvider
from app.config import settings


def test_sanitize_filename_prevents_traversal():
    assert sanitize_filename("../../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\windows\\system32\\calc.exe") == "calc.exe"
    assert sanitize_filename("valid_image_01.jpg") == "valid_image_01.jpg"
    assert sanitize_filename("with spaces and (brackets).png") == "with_spaces_and__brackets_.png"


def test_storage_factory_local_mode():
    provider = get_storage()
    assert isinstance(provider, LocalStorageProvider)


def test_gcp_storage_signed_url_generation():
    provider = GCPStorageProvider(bucket_name="test-forensic-bucket")
    
    # Mock GCP client and blob
    mock_blob = MagicMock()
    mock_blob.generate_signed_url.return_value = "https://storage.googleapis.com/test-forensic-bucket/evidence/signed?sig=xyz"
    
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    
    mock_client = MagicMock()
    mock_client.bucket.return_value = mock_bucket
    
    provider._client = mock_client
    
    signed_url, gs_uri = provider.generate_signed_upload_url(
        case_id="case-100",
        file_id="file-200",
        filename="cctv_tape.mp4",
        content_type="video/mp4",
    )
    
    assert "https://storage.googleapis.com" in signed_url
    assert gs_uri == "gs://test-forensic-bucket/evidence/case-100/file-200/cctv_tape.mp4"
    mock_bucket.blob.assert_called_with("evidence/case-100/file-200/cctv_tape.mp4")
    mock_blob.generate_signed_url.assert_called_once()


def test_dockerfile_and_deploy_scripts_exist():
    root = Path(__file__).resolve().parent.parent.parent
    dockerfile = root / "Dockerfile"
    deploy_sh = root / "scripts" / "deploy_cloud_run.sh"
    deploy_ps1 = root / "scripts" / "deploy_cloud_run.ps1"
    cors_json = root / "scripts" / "cors_gcs.json"

    assert dockerfile.exists()
    assert deploy_sh.exists()
    assert deploy_ps1.exists()
    assert cors_json.exists()

    # Verify Dockerfile multi-stage structure
    content = dockerfile.read_text(encoding="utf-8")
    assert "FROM node:20" in content
    assert "FROM python:3.11-slim" in content
    assert "tesseract-ocr" in content
    assert "libimage-exiftool-perl" in content
    assert "ffmpeg" in content
