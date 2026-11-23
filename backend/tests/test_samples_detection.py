from pathlib import Path
import pytest

from app.analyzers.image_metadata import ImageMetadataAnalyzer
from app.analyzers.image_ela import ImageELAAnalyzer
from app.analyzers.image_splicing import ImageSplicingAnalyzer
from app.core.models import FindingResult

SAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "samples"


def test_detect_image_original():
    sample_path = SAMPLES_DIR / "image_original.jpg"
    assert sample_path.exists(), "Sample fixture image_original.jpg must exist"

    # 1. Metadata: Should pass all checks with valid GPS
    meta_res = ImageMetadataAnalyzer().execute(sample_path, "case_demo", "orig_img")
    meta_findings = {f.check_name: f for f in meta_res.findings}
    assert meta_findings["exif_presence"].result == FindingResult.PASS
    assert meta_findings["editing_software"].result == FindingResult.PASS
    assert meta_findings["timestamp_consistency"].result == FindingResult.PASS
    assert meta_findings["gps_validity"].result == FindingResult.PASS
    assert meta_findings["gps_validity"].evidence["latitude"] > 20.0

    # 2. ELA: Uniform compression distribution
    ela_res = ImageELAAnalyzer().execute(sample_path, "case_demo", "orig_img")
    ela_findings = {f.check_name: f for f in ela_res.findings}
    assert ela_findings["ela_regional_anomaly"].result == FindingResult.PASS

    # 3. Splicing: No copy-move
    splice_res = ImageSplicingAnalyzer().execute(sample_path, "case_demo", "orig_img")
    splice_findings = {f.check_name: f for f in splice_res.findings}
    assert splice_findings["copy_move_forgery"].result == FindingResult.PASS


def test_detect_image_spliced():
    sample_path = SAMPLES_DIR / "image_spliced.jpg"
    assert sample_path.exists(), "Sample fixture image_spliced.jpg must exist"

    # 1. Metadata: Must flag Photoshop
    meta_res = ImageMetadataAnalyzer().execute(sample_path, "case_demo", "splice_img")
    meta_findings = {f.check_name: f for f in meta_res.findings}
    assert meta_findings["editing_software"].result == FindingResult.TAMPERED
    assert "photoshop" in meta_findings["editing_software"].evidence["detected_editor"]

    # 2. ELA: Must detect regional anomaly
    ela_res = ImageELAAnalyzer().execute(sample_path, "case_demo", "splice_img")
    ela_findings = {f.check_name: f for f in ela_res.findings}
    assert ela_findings["ela_regional_anomaly"].result in (FindingResult.SUSPICIOUS, FindingResult.TAMPERED)


def test_detect_image_copymove():
    sample_path = SAMPLES_DIR / "image_copymove.jpg"
    assert sample_path.exists(), "Sample fixture image_copymove.jpg must exist"

    # Splicing: Must flag copy-move
    splice_res = ImageSplicingAnalyzer().execute(sample_path, "case_demo", "copymove_img")
    splice_findings = {f.check_name: f for f in splice_res.findings}
    assert splice_findings["copy_move_forgery"].result == FindingResult.TAMPERED
    assert len(splice_findings["copy_move_forgery"].artifact_paths) > 0


def test_detect_image_stripped():
    sample_path = SAMPLES_DIR / "image_stripped.jpg"
    assert sample_path.exists(), "Sample fixture image_stripped.jpg must exist"

    # Metadata: Must flag missing EXIF
    meta_res = ImageMetadataAnalyzer().execute(sample_path, "case_demo", "stripped_img")
    meta_findings = {f.check_name: f for f in meta_res.findings}
    assert meta_findings["exif_presence"].result == FindingResult.SUSPICIOUS
