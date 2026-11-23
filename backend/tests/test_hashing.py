import hashlib
import io
import tempfile
from pathlib import Path
from app.core.hashing import compute_sha256_file, compute_sha256_stream, verify_file_integrity


def test_compute_sha256_stream():
    data = b"Digital Evidence Forensics PS-05 Hackathon 2026"
    expected = hashlib.sha256(data).hexdigest()
    
    stream = io.BytesIO(data)
    digest, size = compute_sha256_stream(stream)
    assert digest == expected
    assert size == len(data)


def test_file_integrity_verification():
    data = b"Original uncorrupted forensic footage stream"
    expected = hashlib.sha256(data).hexdigest()

    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(data)
        tf_path = Path(tf.name)

    try:
        assert verify_file_integrity(tf_path, expected) is True

        # Simulate tampering by altering a single byte
        with open(tf_path, "wb") as f:
            f.write(b"Tampered uncorrupted forensic footage stream")

        assert verify_file_integrity(tf_path, expected) is False
    finally:
        if tf_path.exists():
            tf_path.unlink()
