import datetime
import os
import shutil
from pathlib import Path
from typing import BinaryIO, Optional, Tuple

from app.config import settings
from app.core.hashing import compute_sha256_stream
from app.core.storage import StorageProvider, sanitize_filename


class GCPStorageProvider(StorageProvider):
    """Google Cloud Storage provider for Google Cloud Run deployment.
    Enforces read-only immutable storage in GCS and creates isolated mutable copies in scratch space.
    """

    def __init__(self, bucket_name: Optional[str] = None):
        self.bucket_name = bucket_name or settings.GCS_BUCKET
        self.scratch_dir = settings.DATA_DIR / "scratch"
        self.scratch_dir.mkdir(parents=True, exist_ok=True)
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from google.cloud import storage as gcs
            self._client = gcs.Client()
        return self._client

    @property
    def bucket(self):
        return self.client.bucket(self.bucket_name)

    def generate_signed_upload_url(
        self, case_id: str, file_id: str, filename: str, content_type: str, expiration_minutes: int = 15
    ) -> Tuple[str, str]:
        """Generates a V4 signed PUT URL allowing direct browser-to-bucket streaming upload,
        bypassing Cloud Run 32MB request limits.
        """
        safe_name = sanitize_filename(filename)
        blob_path = f"evidence/{case_id}/{file_id}/{safe_name}"
        blob = self.bucket.blob(blob_path)

        url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(minutes=expiration_minutes),
            method="PUT",
            content_type=content_type,
        )
        return url, f"gs://{self.bucket_name}/{blob_path}"

    def save_evidence_stream(
        self, case_id: str, file_id: str, filename: str, stream: BinaryIO
    ) -> Tuple[str, str, int]:
        """Streams evidence directly to GCS while simultaneously calculating SHA-256."""
        safe_name = sanitize_filename(filename)
        blob_path = f"evidence/{case_id}/{file_id}/{safe_name}"
        blob = self.bucket.blob(blob_path)

        # Stage in temporary scratch file to compute SHA-256 and upload
        import hashlib
        hasher = hashlib.sha256()
        total_bytes = 0
        chunk_size = 65536

        temp_file = self.scratch_dir / f"temp_{file_id}_{safe_name}"
        with open(temp_file, "wb") as f:
            while True:
                chunk = stream.read(chunk_size)
                if not chunk:
                    break
                hasher.update(chunk)
                total_bytes += len(chunk)
                f.write(chunk)

        sha256 = hasher.hexdigest().lower()
        blob.upload_from_filename(str(temp_file))
        if temp_file.exists():
            temp_file.unlink()

        return f"gs://{self.bucket_name}/{blob_path}", sha256, total_bytes

    def get_working_copy(self, storage_path: str, case_id: str, file_id: str) -> Path:
        """Downloads evidence from GCS to local scratch directory for read-only forensic analysis."""
        case_scratch = self.scratch_dir / case_id / file_id
        case_scratch.mkdir(parents=True, exist_ok=True)

        if storage_path.startswith("gs://"):
            parts = storage_path.replace("gs://", "").split("/", 1)
            bucket_name = parts[0]
            blob_path = parts[1]
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            local_target = case_scratch / Path(blob_path).name
            blob.download_to_filename(str(local_target))
            return local_target
        else:
            orig = Path(storage_path)
            local_target = case_scratch / orig.name
            shutil.copyfile(orig, local_target)
            return local_target

    def save_artifact(
        self, case_id: str, file_id: str, artifact_name: str, content: bytes
    ) -> str:
        """Uploads generated forensic artifact (heatmap, spectrogram, timeline) to GCS."""
        safe_name = sanitize_filename(artifact_name)
        blob_path = f"artifacts/{case_id}/{file_id}/{safe_name}"
        blob = self.bucket.blob(blob_path)
        content_type = "image/png"
        if safe_name.endswith(".jpg") or safe_name.endswith(".jpeg"):
            content_type = "image/jpeg"
        elif safe_name.endswith(".pdf"):
            content_type = "application/pdf"

        blob.upload_from_string(content, content_type=content_type)
        return f"gs://{self.bucket_name}/{blob_path}"

    def get_evidence_path(self, storage_path: str) -> Path:
        """Returns local path to evidence file, downloading from GCS if needed."""
        if storage_path.startswith("gs://"):
            parts = storage_path.replace("gs://", "").split("/", 1)
            blob_path = parts[1]
            cached_path = self.scratch_dir / "cache" / blob_path
            cached_path.parent.mkdir(parents=True, exist_ok=True)
            if not cached_path.exists():
                blob = self.client.bucket(parts[0]).blob(blob_path)
                blob.download_to_filename(str(cached_path))
            return cached_path
        return Path(storage_path)

    def cleanup_scratch(self, case_id: str):
        target = self.scratch_dir / case_id
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
