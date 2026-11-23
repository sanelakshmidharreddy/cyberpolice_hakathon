import hashlib
from pathlib import Path
from typing import BinaryIO, Tuple


def compute_sha256_stream(stream: BinaryIO, chunk_size: int = 65536) -> Tuple[str, int]:
    """Computes SHA-256 hash and total size in bytes while streaming binary data.
    
    Args:
        stream: Readable binary stream.
        chunk_size: Buffer chunk size in bytes (default 64KB).
        
    Returns:
        Tuple of (lowercase hex digest string, total byte count).
    """
    hasher = hashlib.sha256()
    total_bytes = 0
    while True:
        chunk = stream.read(chunk_size)
        if not chunk:
            break
        hasher.update(chunk)
        total_bytes += len(chunk)
    return hasher.hexdigest().lower(), total_bytes


def compute_sha256_file(file_path: Path, chunk_size: int = 65536) -> str:
    """Computes SHA-256 hash of a file on disk.
    
    Args:
        file_path: Path to target file.
        chunk_size: Buffer chunk size in bytes.
        
    Returns:
        Lowercase hex digest string.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Cannot compute hash: file not found at {file_path}")
        
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest().lower()


def verify_file_integrity(file_path: Path, expected_sha256: str) -> bool:
    """Verifies that the current file hash strictly matches the expected hash.
    
    Args:
        file_path: Path to target file.
        expected_sha256: Hash captured at original upload.
        
    Returns:
        True if hashes match exactly, False otherwise.
    """
    actual = compute_sha256_file(file_path)
    return actual.lower() == expected_sha256.lower()
