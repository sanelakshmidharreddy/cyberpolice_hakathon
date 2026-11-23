from pathlib import Path
import cv2
import numpy as np
import pytest

from app.analyzers.image_splicing import ImageSplicingAnalyzer
from app.core.models import FindingResult


@pytest.fixture
def clean_image(tmp_path) -> Path:
    """Creates a natural non-duplicated image with uniform high-frequency noise."""
    np.random.seed(42)
    h, w = 320, 320
    # Gradient background with consistent uniform noise
    y, x = np.mgrid[0:h, 0:w]
    gradient = ((x + y) / (h + w) * 180).astype(np.uint8)
    noise = np.random.normal(0, 6, (h, w)).astype(np.int16)
    combined = np.clip(gradient.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    bgr = cv2.cvtColor(combined, cv2.COLOR_GRAY2BGR)

    path = tmp_path / "clean_splicing.jpg"
    cv2.imwrite(str(path), bgr)
    return path


@pytest.fixture
def copymove_image(tmp_path) -> Path:
    """Creates an image where a textured object is duplicated across the scene."""
    np.random.seed(42)
    h, w = 400, 400
    canvas = np.ones((h, w, 3), dtype=np.uint8) * 180

    # Draw complex distinctive texture in source region
    src_x, src_y = 50, 50
    size = 80
    for r in range(10, 35, 5):
        cv2.circle(canvas, (src_x + 40, src_y + 40), r, (20, 40, 200), 2)
    cv2.rectangle(canvas, (src_x + 20, src_y + 20), (src_x + 60, src_y + 60), (50, 180, 50), -1)
    # Add high-contrast feature dots
    for i in range(15):
        cv2.circle(canvas, (src_x + 15 + (i * 3) % 50, src_y + 15 + (i * 7) % 50), 3, (0, 0, 0), -1)

    # Copy the region and clone it to dst_x, dst_y (translation vector)
    dst_x, dst_y = 240, 200
    canvas[dst_y:dst_y+size, dst_x:dst_x+size] = canvas[src_y:src_y+size, src_x:src_x+size]

    path = tmp_path / "copymove_sample.jpg"
    cv2.imwrite(str(path), canvas)
    return path


@pytest.fixture
def noise_inconsistent_image(tmp_path) -> Path:
    """Creates an image where a localized patch has significantly different noise variance."""
    np.random.seed(42)
    h, w = 384, 384
    # Smooth background with very low noise (std = 2)
    base = np.ones((h, w), dtype=np.float32) * 128.0
    base += np.random.normal(0, 2.0, (h, w))

    # Insert a 64x64 patch with high sensor noise variance (std = 28.0)
    base[128:192, 128:192] += np.random.normal(0, 28.0, (64, 64))

    clipped = np.clip(base, 0, 255).astype(np.uint8)
    bgr = cv2.cvtColor(clipped, cv2.COLOR_GRAY2BGR)

    path = tmp_path / "noise_inconsistent.jpg"
    cv2.imwrite(str(path), bgr)
    return path


def test_copy_move_clean(clean_image):
    analyzer = ImageSplicingAnalyzer()
    res = analyzer.execute(clean_image, "case_splice", "f_clean")
    assert res.error is None
    results = {f.check_name: f for f in res.findings}
    assert results["copy_move_forgery"].result == FindingResult.PASS


def test_copy_move_detected(copymove_image):
    analyzer = ImageSplicingAnalyzer()
    res = analyzer.execute(copymove_image, "case_splice", "f_dup")
    assert res.error is None
    results = {f.check_name: f for f in res.findings}
    assert results["copy_move_forgery"].result == FindingResult.TAMPERED
    assert results["copy_move_forgery"].confidence >= 0.85
    assert len(results["copy_move_forgery"].artifact_paths) > 0
    assert Path(results["copy_move_forgery"].artifact_paths[0]).exists()


def test_noise_inconsistency_detected(noise_inconsistent_image):
    analyzer = ImageSplicingAnalyzer()
    res = analyzer.execute(noise_inconsistent_image, "case_splice", "f_noise")
    assert res.error is None
    results = {f.check_name: f for f in res.findings}
    assert results["noise_inconsistency"].result == FindingResult.SUSPICIOUS
    assert results["noise_inconsistency"].evidence["anomalous_blocks"] > 0
    assert len(results["noise_inconsistency"].artifact_paths) > 0
    assert Path(results["noise_inconsistency"].artifact_paths[0]).exists()
