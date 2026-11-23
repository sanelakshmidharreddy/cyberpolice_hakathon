from pathlib import Path
import pytest

from app.analyzers.video_frames import VideoFramesAnalyzer
from app.analyzers.video_timestamps import VideoTimestampsAnalyzer
from app.core.models import FindingResult

SAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "samples"


def test_video_frames_original():
    sample_path = SAMPLES_DIR / "cctv_original.mp4"
    assert sample_path.exists(), "cctv_original.mp4 must exist"

    analyzer = VideoFramesAnalyzer()
    res = analyzer.execute(sample_path, "case_vid", "f_orig")
    assert res.error is None

    findings = {f.check_name: f for f in res.findings}
    assert findings["duplicated_frames"].result == FindingResult.PASS
    assert findings["motion_continuity"].result == FindingResult.PASS
    assert len(findings["motion_continuity"].artifact_paths) > 0
    assert Path(findings["motion_continuity"].artifact_paths[0]).exists()


def test_video_frames_cut():
    sample_path = SAMPLES_DIR / "cctv_cut.mp4"
    assert sample_path.exists(), "cctv_cut.mp4 must exist"

    analyzer = VideoFramesAnalyzer()
    res = analyzer.execute(sample_path, "case_vid", "f_cut")
    assert res.error is None

    findings = {f.check_name: f for f in res.findings}
    assert findings["motion_continuity"].result in (FindingResult.SUSPICIOUS, FindingResult.TAMPERED)
    assert len(findings["motion_continuity"].evidence.get("cut_points", [])) > 0


def test_video_frames_duplicated_loop():
    sample_path = SAMPLES_DIR / "cctv_dup.mp4"
    assert sample_path.exists(), "cctv_dup.mp4 must exist"

    analyzer = VideoFramesAnalyzer()
    res = analyzer.execute(sample_path, "case_vid", "f_dup")
    assert res.error is None

    findings = {f.check_name: f for f in res.findings}
    assert findings["duplicated_frames"].result == FindingResult.TAMPERED
    assert len(findings["duplicated_frames"].evidence.get("duplicated_runs", [])) > 0


def test_video_timestamps_container():
    sample_path = SAMPLES_DIR / "cctv_original.mp4"
    analyzer = VideoTimestampsAnalyzer()
    res = analyzer.execute(sample_path, "case_vid", "f_orig")
    assert res.error is None

    findings = {f.check_name: f for f in res.findings}
    assert findings["container_duration_check"].result == FindingResult.PASS
    assert findings["container_duration_check"].evidence["total_frames"] > 0
