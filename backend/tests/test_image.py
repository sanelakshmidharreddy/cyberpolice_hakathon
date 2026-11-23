import io
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import piexif
import pytest

from app.analyzers.image_metadata import ImageMetadataAnalyzer
from app.analyzers.image_ela import ImageELAAnalyzer
from app.core.models import FindingResult


@pytest.fixture
def clean_jpeg(tmp_path) -> Path:
    img = Image.new("RGB", (300, 300), color=(120, 140, 160))
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 50, 250, 250], fill=(200, 100, 80))

    # Standard camera EXIF
    zeroth_ifd = {
        piexif.ImageIFD.Make: "Canon",
        piexif.ImageIFD.Model: "EOS 5D Mark IV",
        piexif.ImageIFD.Software: "Digital Camera EOS Firmware",
        piexif.ImageIFD.DateTime: "2024:06:15 14:30:00",
    }
    exif_ifd = {
        piexif.ExifIFD.DateTimeOriginal: "2024:06:15 14:30:00",
        piexif.ExifIFD.DateTimeDigitized: "2024:06:15 14:30:00",
        piexif.ExifIFD.PixelXDimension: 300,
        piexif.ExifIFD.PixelYDimension: 300,
    }
    exif_bytes = piexif.dump({"0th": zeroth_ifd, "Exif": exif_ifd, "GPS": {}, "1st": {}, "thumbnail": None})

    file_path = tmp_path / "camera_clean.jpg"
    img.save(str(file_path), "JPEG", quality=95, exif=exif_bytes)
    return file_path


@pytest.fixture
def edited_jpeg(tmp_path) -> Path:
    img = Image.new("RGB", (300, 300), color=(100, 150, 200))
    zeroth_ifd = {
        piexif.ImageIFD.Make: "Nikon",
        piexif.ImageIFD.Software: "Adobe Photoshop 2024 (Windows)",
        piexif.ImageIFD.DateTime: "2024:08:20 18:45:10",
    }
    exif_ifd = {
        piexif.ExifIFD.DateTimeOriginal: "2024:08:10 10:00:00",
    }
    exif_bytes = piexif.dump({"0th": zeroth_ifd, "Exif": exif_ifd, "GPS": {}, "1st": {}, "thumbnail": None})

    file_path = tmp_path / "photoshop_edited.jpg"
    img.save(str(file_path), "JPEG", quality=90, exif=exif_bytes)
    return file_path


@pytest.fixture
def future_date_jpeg(tmp_path) -> Path:
    img = Image.new("RGB", (200, 200), color=(50, 50, 50))
    exif_ifd = {
        piexif.ExifIFD.DateTimeOriginal: "2099:12:31 23:59:59",
    }
    exif_bytes = piexif.dump({"0th": {}, "Exif": exif_ifd, "GPS": {}, "1st": {}, "thumbnail": None})

    file_path = tmp_path / "future_date.jpg"
    img.save(str(file_path), "JPEG", quality=90, exif=exif_bytes)
    return file_path


@pytest.fixture
def stripped_jpeg(tmp_path) -> Path:
    img = Image.new("RGB", (200, 200), color=(80, 80, 80))
    file_path = tmp_path / "stripped.jpg"
    img.save(str(file_path), "JPEG", quality=90)
    return file_path


def test_metadata_clean_image(clean_jpeg):
    analyzer = ImageMetadataAnalyzer()
    res = analyzer.execute(clean_jpeg, "case1", "file1")
    assert res.error is None
    results = {f.check_name: f.result for f in res.findings}
    assert results["exif_presence"] == FindingResult.PASS
    assert results["editing_software"] == FindingResult.PASS
    assert results["timestamp_consistency"] == FindingResult.PASS


def test_metadata_photoshop_detection(edited_jpeg):
    analyzer = ImageMetadataAnalyzer()
    res = analyzer.execute(edited_jpeg, "case1", "file2")
    results = {f.check_name: f for f in res.findings}
    assert results["editing_software"].result == FindingResult.TAMPERED
    assert results["editing_software"].confidence >= 0.90
    assert "PHOTOSHOP" in results["editing_software"].explanation


def test_metadata_future_timestamp(future_date_jpeg):
    analyzer = ImageMetadataAnalyzer()
    res = analyzer.execute(future_date_jpeg, "case1", "file3")
    results = {f.check_name: f for f in res.findings}
    assert results["timestamp_validity"].result == FindingResult.TAMPERED


def test_metadata_stripped_exif(stripped_jpeg):
    analyzer = ImageMetadataAnalyzer()
    res = analyzer.execute(stripped_jpeg, "case1", "file4")
    results = {f.check_name: f for f in res.findings}
    assert results["exif_presence"].result == FindingResult.SUSPICIOUS


def test_ela_clean_jpeg(clean_jpeg):
    analyzer = ImageELAAnalyzer()
    res = analyzer.execute(clean_jpeg, "case1", "file1")
    assert res.error is None
    results = {f.check_name: f for f in res.findings}
    assert results["ela_regional_anomaly"].result == FindingResult.PASS
    # Artifact heatmap must be generated and non-empty
    assert len(results["ela_regional_anomaly"].artifact_paths) > 0
    assert Path(results["ela_regional_anomaly"].artifact_paths[0]).exists()


def test_ela_spliced_region(tmp_path):
    # Create base image compressed at low quality 50
    base = Image.new("RGB", (400, 400), color=(100, 100, 100))
    buf = io.BytesIO()
    base.save(buf, "JPEG", quality=50)
    buf.seek(0)
    base = Image.open(buf)

    # Paste a high quality patch with complex noise
    patch = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    patch_img = Image.fromarray(patch)
    base.paste(patch_img, (150, 150))

    spliced_path = tmp_path / "spliced.jpg"
    base.save(str(spliced_path), "JPEG", quality=90)

    analyzer = ImageELAAnalyzer()
    res = analyzer.execute(spliced_path, "case1", "file_spliced")
    assert res.error is None
    results = {f.check_name: f for f in res.findings}
    assert results["ela_regional_anomaly"].result in (FindingResult.SUSPICIOUS, FindingResult.TAMPERED)
    assert len(results["ela_regional_anomaly"].evidence.get("top_regions", [])) > 0


def test_ela_png_not_applicable(tmp_path):
    png_path = tmp_path / "lossless.png"
    Image.new("RGB", (200, 200), color=(20, 40, 60)).save(str(png_path), "PNG")

    analyzer = ImageELAAnalyzer()
    res = analyzer.execute(png_path, "case1", "file_png")
    results = {f.check_name: f for f in res.findings}
    assert results["ela_heatmap"].result == FindingResult.NOT_APPLICABLE
