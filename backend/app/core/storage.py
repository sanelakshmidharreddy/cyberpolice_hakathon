import os
import re
import shutil
import stat
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO, Optional, Tuple

from app.config import settings
from app.core.hashing import compute_sha256_stream


def sanitize_filename(filename: str) -> str:
    """Removes path traversals and dangerous characters from filename."""
    base = Path(filename).name
    clean = re.sub(r"[^\w\.\-]", "_", base)
    return clean[:200] or "unnamed_evidence"


class StorageProvider(ABC):
    """Abstract interface for evidence and artifact storage."""

    @abstractmethod
    def save_evidence_stream(
        self, case_id: str, file_id: str, filename: str, stream: BinaryIO
    ) -> Tuple[str, str, int]:
        """Streams evidence directly to storage, calculating SHA-256 simultaneously.
        
        Returns:
            Tuple of (storage_path_or_uri, sha256_digest, size_bytes)
        """
        pass

    @abstractmethod
    def get_working_copy(self, storage_path: str, case_id: str, file_id: str) -> Path:
        """Creates a mutable working copy in scratch space. Original remains read-only."""
        pass

    @abstractmethod
    def save_artifact(
        self, case_id: str, file_id: str, artifact_name: str, content: bytes
    ) -> str:
        """Saves generated visual/forensic artifact and returns path or URL."""
        pass

    @abstractmethod
    def get_evidence_path(self, storage_path: str) -> Path:
        """Returns direct filesystem path to read-only original (local mode)."""
        pass

    @abstractmethod
    def cleanup_scratch(self, case_id: str):
        """Cleans temporary working copies for a case."""
        pass


class LocalStorageProvider(StorageProvider):
    """Local filesystem storage provider for offline and edge deployments."""

    def __init__(self, base_data_dir: Optional[Path] = None):
        self.data_dir = base_data_dir or settings.DATA_DIR
        self.evidence_dir = self.data_dir / "evidence"
        self.artifacts_dir = self.data_dir / "artifacts"
        self.scratch_dir = self.data_dir / "scratch"
        for d in (self.evidence_dir, self.artifacts_dir, self.scratch_dir):
            d.mkdir(parents=True, exist_ok=True)

    def save_evidence_stream(
        self, case_id: str, file_id: str, filename: str, stream: BinaryIO
    ) -> Tuple[str, str, int]:
        safe_name = sanitize_filename(filename)
        case_evidence_dir = self.evidence_dir / case_id
        case_evidence_dir.mkdir(parents=True, exist_ok=True)

        target_file = case_evidence_dir / f"{file_id}_{safe_name}"

        # If file previously existed, remove read-only attribute before overwriting
        if target_file.exists():
            target_file.chmod(stat.S_IWRITE)

        # Stream directly to disk while computing SHA-256
        import hashlib
        hasher = hashlib.sha256()
        total_bytes = 0
        chunk_size = 65536

        with open(target_file, "wb") as f:
            while True:
                chunk = stream.read(chunk_size)
                if not chunk:
                    break
                hasher.update(chunk)
                total_bytes += len(chunk)
                f.write(chunk)

        sha256 = hasher.hexdigest().lower()

        # Enforce Read-Only permission on original file for integrity protection
        try:
            target_file.chmod(stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
        except Exception:
            pass

        return str(target_file), sha256, total_bytes

    def get_working_copy(self, storage_path: str, case_id: str, file_id: str) -> Path:
        original = Path(storage_path)
        if not original.exists():
            raise FileNotFoundError(f"Original evidence not found: {storage_path}")

        case_scratch = self.scratch_dir / case_id / file_id
        case_scratch.mkdir(parents=True, exist_ok=True)

        working_path = case_scratch / original.name
        # Copy to working directory with write permissions enabled
        shutil.copyfile(original, working_path)
        try:
            working_path.chmod(stat.S_IREAD | stat.S_IWRITE)
        except Exception:
            pass
        return working_path

    def save_artifact(
        self, case_id: str, file_id: str, artifact_name: str, content: bytes
    ) -> str:
        case_artifact_dir = self.artifacts_dir / case_id / file_id
        case_artifact_dir.mkdir(parents=True, exist_ok=True)

        safe_name = sanitize_filename(artifact_name)
        target_path = case_artifact_dir / safe_name
        with open(target_path, "wb") as f:
            f.write(content)
        return str(target_path)

    def get_evidence_path(self, storage_path: str) -> Path:
        return Path(storage_path)

    def cleanup_scratch(self, case_id: str):
        target = self.scratch_dir / case_id
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)


def get_storage() -> StorageProvider:
    """Storage provider factory supporting local and GCP modes."""
    if settings.STORAGE_MODE == "gcp" and settings.GCS_BUCKET:
        try:
            from app.core.gcp_storage import GCPStorageProvider
            return GCPStorageProvider()
        except Exception as e:
            import logging
            logging.getLogger("forge.storage").warning(f"Failed to initialize GCP storage: {e}. Falling back to LocalStorageProvider.")
    return LocalStorageProvider()


storage = get_storage()
