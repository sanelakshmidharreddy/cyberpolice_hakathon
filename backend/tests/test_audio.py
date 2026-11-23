from pathlib import Path
import pytest

from app.analyzers.audio_tamper import AudioTamperAnalyzer
from app.analyzers.audio_deepfake import AudioDeepfakeAnalyzer
from app.core.models import FindingResult

SAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "samples"


def test_audio_tamper_original():
    sample_path = SAMPLES_DIR / "audio_original.wav"
    assert sample_path.exists(), "audio_original.wav must exist"

    analyzer = AudioTamperAnalyzer()
    res = analyzer.execute(sample_path, "case_aud", "f_orig")
    assert res.error is None

    findings = {f.check_name: f for f in res.findings}
    assert findings["silence_gap_detection"].result == FindingResult.PASS
    assert findings["enf_continuity"].result == FindingResult.PASS
    assert len(res.findings[0].artifact_paths) > 0
    assert Path(res.findings[0].artifact_paths[0]).exists()


def test_audio_tamper_spliced():
    sample_path = SAMPLES_DIR / "audio_spliced.wav"
    assert sample_path.exists(), "audio_spliced.wav must exist"

    analyzer = AudioTamperAnalyzer()
    res = analyzer.execute(sample_path, "case_aud", "f_splice")
    assert res.error is None

    findings = {f.check_name: f for f in res.findings}
    assert findings["enf_continuity"].result == FindingResult.TAMPERED
    assert len(findings["enf_continuity"].evidence.get("anomalies", [])) > 0


def test_audio_tamper_cut():
    sample_path = SAMPLES_DIR / "audio_cut.wav"
    assert sample_path.exists(), "audio_cut.wav must exist"

    analyzer = AudioTamperAnalyzer()
    res = analyzer.execute(sample_path, "case_aud", "f_cut")
    assert res.error is None

    findings = {f.check_name: f for f in res.findings}
    assert findings["silence_gap_detection"].result == FindingResult.TAMPERED
    assert len(findings["silence_gap_detection"].evidence.get("zero_runs", [])) > 0


def test_audio_deepfake_analyzer():
    sample_path = SAMPLES_DIR / "audio_original.wav"
    analyzer = AudioDeepfakeAnalyzer()
    res = analyzer.execute(sample_path, "case_aud", "f_orig")
    assert res.error is None
    # Result must be either PASS or INCONCLUSIVE based on environment, never crash
    assert res.findings[0].result in (FindingResult.PASS, FindingResult.INCONCLUSIVE)
