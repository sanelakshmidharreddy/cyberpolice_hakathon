import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import wave

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import butter, filtfilt, hilbert, sosfiltfilt

from app.analyzers.base import BaseAnalyzer
from app.core.models import Finding, FindingResult, MediaType
from app.core.storage import storage

logger = logging.getLogger("forge.analyzers.audio_tamper")


def load_wav_file(file_path: Path) -> Tuple[np.ndarray, int]:
    """Loads a WAV audio file into floating point numpy array and sample rate."""
    with wave.open(str(file_path), "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        rate = wf.getframerate()
        n_frames = wf.getnframes()
        raw_bytes = wf.readframes(n_frames)

    # Convert bytes to numpy based on width
    if sampwidth == 2:
        data = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    elif sampwidth == 4:
        data = np.frombuffer(raw_bytes, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        data = np.frombuffer(raw_bytes, dtype=np.uint8).astype(np.float32) / 128.0 - 1.0

    if n_channels > 1:
        # Convert to mono by averaging channels
        data = data.reshape(-1, n_channels).mean(axis=1)

    return data, rate


def butter_bandpass_filter(data: np.ndarray, lowcut: float, highcut: float, fs: int, order: int = 4) -> np.ndarray:
    """Zero-phase Butterworth bandpass filter."""
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype="band")
    return filtfilt(b, a, data)


class AudioTamperAnalyzer(BaseAnalyzer):
    """Audio forensic engine detecting spectral discontinuities, silence cuts, and 50Hz ENF jumps."""

    name: str = "audio_tamper"
    version: str = "1.0.0"
    supported_media: List[MediaType] = [MediaType.AUDIO]

    def analyze(self, file_path: Path, case_id: str, file_id: str) -> List[Finding]:
        findings: List[Finding] = []

        try:
            audio, sample_rate = load_wav_file(file_path)
        except Exception as e:
            return [
                Finding(
                    module=self.name,
                    check_name="audio_load",
                    result=FindingResult.INCONCLUSIVE,
                    confidence=0.5,
                    explanation=f"Cannot decode audio stream (must be standard WAV or PCM): {str(e)}",
                )
            ]

        total_samples = len(audio)
        duration_s = total_samples / sample_rate
        if duration_s < 1.0:
            return [
                Finding(
                    module=self.name,
                    check_name="audio_duration",
                    result=FindingResult.INCONCLUSIVE,
                    confidence=0.5,
                    explanation="Audio stream shorter than 1.0 second; insufficient data for spectral analysis.",
                )
            ]

        suspicious_intervals: List[Tuple[float, float, str]] = []

        # -------------------------------------------------------------
        # 1. Digital Zero Silence Gap Detection (Cut Artifacts)
        # -------------------------------------------------------------
        zero_runs = []
        is_zero = np.abs(audio) < 1e-6
        zero_indices = np.where(is_zero)[0]

        if len(zero_indices) > 0:
            diffs = np.diff(zero_indices)
            split_points = np.where(diffs > 1)[0]
            start_idx = zero_indices[0]

            for sp in split_points:
                end_idx = zero_indices[sp]
                run_length = end_idx - start_idx + 1
                if (run_length / sample_rate) >= 0.25:  # >= 250ms exact zero run
                    t_start = round(start_idx / sample_rate, 2)
                    t_end = round(end_idx / sample_rate, 2)
                    zero_runs.append({"start_s": t_start, "end_s": t_end, "duration_s": round(t_end - t_start, 2)})
                    suspicious_intervals.append((t_start, t_end, "Digital Silence Gap"))
                start_idx = zero_indices[sp + 1]

            # Check final segment
            last_end = zero_indices[-1]
            last_len = last_end - start_idx + 1
            if (last_len / sample_rate) >= 0.25:
                t_start = round(start_idx / sample_rate, 2)
                t_end = round(last_end / sample_rate, 2)
                zero_runs.append({"start_s": t_start, "end_s": t_end, "duration_s": round(t_end - t_start, 2)})
                suspicious_intervals.append((t_start, t_end, "Digital Silence Gap"))

        if zero_runs:
            findings.append(
                Finding(
                    module=self.name,
                    check_name="silence_gap_detection",
                    result=FindingResult.TAMPERED,
                    confidence=0.92,
                    explanation=(
                        f"Detected {len(zero_runs)} anomalous digital silence gap(s) (exact zero amplitude runs). "
                        "Digital audio recorded in physical environments always contains ambient noise; exact zero "
                        "runs are unnatural and demonstrate deletion or cut points."
                    ),
                    evidence={"zero_runs": zero_runs},
                )
            )
        else:
            findings.append(
                Finding(
                    module=self.name,
                    check_name="silence_gap_detection",
                    result=FindingResult.PASS,
                    confidence=0.88,
                    explanation="No artificial digital zero gaps or sudden silence insertions detected.",
                    evidence={"zero_runs_count": 0},
                )
            )

        # -------------------------------------------------------------
        # 2. Electric Network Frequency (ENF 50 Hz) Analysis
        # -------------------------------------------------------------
        # Bandpass filter around 48 Hz - 52 Hz (50 Hz power grid hum) using stable SOS
        try:
            sos = butter(2, [48.0, 52.0], btype="band", fs=sample_rate, output="sos")
            enf_filtered = sosfiltfilt(sos, audio)

            enf_power = float(np.mean(enf_filtered ** 2))
            total_power = float(np.mean(audio ** 2)) + 1e-9
            snr_enf = 10.0 * np.log10(max(enf_power / total_power, 1e-12))

            if snr_enf < -40.0:
                findings.append(
                    Finding(
                        module=self.name,
                        check_name="enf_continuity",
                        result=FindingResult.INCONCLUSIVE,
                        confidence=0.55,
                        explanation=(
                            f"ENF signal energy is too weak ({snr_enf:.1f} dB relative to stream). "
                            "Device was battery-operated or lacked acoustic/electromagnetic coupling to the 50 Hz power grid."
                        ),
                        evidence={"snr_enf_db": round(snr_enf, 1)},
                    )
                )
            else:
                # Analytic signal via Hilbert transform to extract instantaneous phase
                analytic = hilbert(enf_filtered)
                phase = np.unwrap(np.angle(analytic))
                t = np.arange(len(phase)) / sample_rate
                expected_phase = 2.0 * np.pi * 50.0 * t
                phase_diff = np.unwrap(phase - expected_phase)
                dp = np.abs(np.diff(phase_diff))

                # Discard 0.2s filter boundary transients
                edge_trim = int(sample_rate * 0.2)
                core_dp = dp[edge_trim:-edge_trim] if len(dp) > 2 * edge_trim else dp

                # Threshold: normal continuous grid ENF phase drift < 0.0005 per sample
                # A cut or splice causes phase jumps > 0.002
                jump_mask = core_dp > 0.002
                jump_indices = np.where(jump_mask)[0]

                enf_anomalies = []
                if len(jump_indices) > 0:
                    split_jumps = np.where(np.diff(jump_indices) > sample_rate // 2)[0]
                    cur_jump = jump_indices[0]
                    for sj in split_jumps:
                        j_time = round((cur_jump + edge_trim) / sample_rate, 2)
                        enf_anomalies.append({"timestamp_s": j_time, "phase_jump": round(float(core_dp[cur_jump]), 5)})
                        suspicious_intervals.append((max(0.0, j_time - 0.2), j_time + 0.2, "ENF Phase Discontinuity"))
                        cur_jump = jump_indices[sj + 1]

                    j_time = round((cur_jump + edge_trim) / sample_rate, 2)
                    enf_anomalies.append({"timestamp_s": j_time, "phase_jump": round(float(core_dp[cur_jump]), 5)})
                    suspicious_intervals.append((max(0.0, j_time - 0.2), j_time + 0.2, "ENF Phase Discontinuity"))

                if enf_anomalies:
                    findings.append(
                        Finding(
                            module=self.name,
                            check_name="enf_continuity",
                            result=FindingResult.TAMPERED,
                            confidence=0.94,
                            explanation=(
                                f"Detected {len(enf_anomalies)} Electric Network Frequency (50 Hz ENF) phase discontinuity jump(s). "
                                f"The power grid reference wave was abruptly disrupted at t={enf_anomalies[0]['timestamp_s']}s, confirming an edit/splice cut."
                            ),
                            evidence={"anomalies": enf_anomalies, "snr_enf_db": round(snr_enf, 1)},
                        )
                    )
                else:
                    findings.append(
                        Finding(
                            module=self.name,
                            check_name="enf_continuity",
                            result=FindingResult.PASS,
                            confidence=0.92,
                            explanation="50 Hz Electric Network Frequency (ENF) maintains smooth, uninterrupted phase continuity.",
                            evidence={"snr_enf_db": round(snr_enf, 1), "max_phase_deviation": round(float(np.max(core_dp)), 6)},
                        )
                    )
        except Exception as e:
            logger.warning(f"ENF analysis failed: {e}")
            findings.append(
                Finding(
                    module=self.name,
                    check_name="enf_continuity",
                    result=FindingResult.INCONCLUSIVE,
                    confidence=0.5,
                    explanation=f"ENF filtering encounter: {str(e)}",
                )
            )


        # -------------------------------------------------------------
        # 3. Waveform & Spectrogram Forensic Artifact Generation
        # -------------------------------------------------------------
        fig, (ax_wave, ax_spec) = plt.subplots(2, 1, figsize=(10, 5), sharex=True, dpi=120)
        time_axis = np.linspace(0, duration_s, total_samples)

        # Downsample waveform for plotting speed if long
        downsample_factor = max(1, total_samples // 10000)
        ax_wave.plot(time_axis[::downsample_factor], audio[::downsample_factor], color="#2c3e50", linewidth=0.8)
        ax_wave.set_title("Audio Waveform & Forensically Shaded Tamper Intervals", fontsize=10, fontweight="bold")
        ax_wave.set_ylabel("Amplitude", fontsize=8)
        ax_wave.grid(True, linestyle=":", alpha=0.5)

        for t_s, t_e, label in suspicious_intervals:
            ax_wave.axvspan(t_s, t_e, color="#e74c3c", alpha=0.35, label=label)
            ax_spec.axvspan(t_s, t_e, color="#e74c3c", alpha=0.35)

        # Spectrogram panel (adding 1e-9 epsilon to prevent log10 zero on digital silence runs)
        spec_audio = audio + 1e-9 * np.random.randn(len(audio))
        Pxx, freqs, bins, im = ax_spec.specgram(spec_audio, NFFT=512, Fs=sample_rate, noverlap=256, cmap="magma")
        ax_spec.set_title("Frequency Spectrogram (0 - 8 kHz)", fontsize=10, fontweight="bold")
        ax_spec.set_xlabel("Time (seconds)", fontsize=9)
        ax_spec.set_ylabel("Frequency (Hz)", fontsize=8)
        ax_spec.set_ylim(0, min(8000, sample_rate // 2))

        # Handle unique labels in legend
        handles, labels = ax_wave.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        if by_label:
            ax_wave.legend(by_label.values(), by_label.keys(), loc="upper right", fontsize=8)

        fig.tight_layout()
        spec_buf = Path(storage.scratch_dir / f"{case_id}_{file_id}_audio_spec.png")
        fig.savefig(str(spec_buf))
        plt.close(fig)

        artifact_path = storage.save_artifact(
            case_id=case_id,
            file_id=file_id,
            artifact_name="audio_spectrogram_tamper.png",
            content=spec_buf.read_bytes(),
        )
        if spec_buf.exists():
            spec_buf.unlink()

        # Attach artifact to primary finding
        if findings:
            findings[0].artifact_paths = [artifact_path]

        return findings
