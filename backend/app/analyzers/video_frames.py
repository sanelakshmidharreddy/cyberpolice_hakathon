import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image
import imagehash
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from app.analyzers.base import BaseAnalyzer
from app.core.models import Finding, FindingResult, MediaType
from app.core.storage import storage

logger = logging.getLogger("forge.analyzers.video_frames")


class VideoFramesAnalyzer(BaseAnalyzer):
    """Forensic CCTV and video frame continuity analyzer.
    
    Detects dropped frames, inserted loops/duplicates, and abrupt optical-flow cut points.
    """

    name: str = "video_frames"
    version: str = "1.0.0"
    supported_media: List[MediaType] = [MediaType.VIDEO]

    def analyze(self, file_path: Path, case_id: str, file_id: str) -> List[Finding]:
        findings: List[Finding] = []

        cap = cv2.VideoCapture(str(file_path))
        if not cap.isOpened():
            return [
                Finding(
                    module=self.name,
                    check_name="video_open",
                    result=FindingResult.INCONCLUSIVE,
                    confidence=0.5,
                    explanation=f"Cannot open video container: {file_path.name}",
                )
            ]

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        if fps <= 0:
            fps = 25.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration_sec = total_frames / fps if total_frames > 0 else 0.0

        # Adaptive sampling: For clips < 2 minutes (3000 frames), evaluate every frame.
        # For longer files, sample every k-th frame.
        sample_step = 1 if total_frames <= 3000 else int(np.ceil(total_frames / 3000))

        frame_indices = []
        timestamps = []
        phashes = []
        motion_scores = []  # Mean absolute difference between consecutive sampled frames

        prev_gray = None
        current_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if current_idx % sample_step == 0:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                # Compute pHash for duplicate detection
                pil_sub = Image.fromarray(cv2.resize(gray, (64, 64)))
                ph = imagehash.phash(pil_sub)
                phashes.append(ph)

                t_sec = current_idx / fps
                frame_indices.append(current_idx)
                timestamps.append(t_sec)

                if prev_gray is not None:
                    # Calculate optical motion score via frame difference
                    diff = cv2.absdiff(gray, prev_gray)
                    motion = float(np.mean(diff))
                    motion_scores.append(motion)
                else:
                    motion_scores.append(0.0)

                prev_gray = gray

            current_idx += 1

        cap.release()

        if len(motion_scores) < 5:
            return [
                Finding(
                    module=self.name,
                    check_name="frame_continuity",
                    result=FindingResult.INCONCLUSIVE,
                    confidence=0.5,
                    explanation="Video stream contains too few readable frames for temporal continuity analysis.",
                )
            ]

        # -------------------------------------------------------------
        # 1. Duplicated / Looped Frame Detection
        # -------------------------------------------------------------
        # Identify runs of identical perceptual hashes in non-static clips
        global_avg_motion = float(np.mean(motion_scores))
        duplicated_runs = []
        current_run_start = None

        for i in range(1, len(phashes)):
            # Perceptual hash distance == 0 denotes visually identical frame content
            if phashes[i] == phashes[i-1]:
                if current_run_start is None:
                    current_run_start = i - 1
            else:
                if current_run_start is not None:
                    run_len = i - current_run_start
                    # If identical for >= 15 frames in a dynamic scene, flag as looped/frozen
                    if run_len >= 15 and (global_avg_motion > 0.1 or max(motion_scores) > 0.3):
                        duplicated_runs.append({
                            "start_frame": frame_indices[current_run_start],
                            "end_frame": frame_indices[i-1],
                            "start_time_s": round(timestamps[current_run_start], 2),
                            "end_time_s": round(timestamps[i-1], 2),
                            "duration_s": round(timestamps[i-1] - timestamps[current_run_start], 2),
                        })
                    current_run_start = None

        if current_run_start is not None:
            run_len = len(phashes) - current_run_start
            if run_len >= 15 and (global_avg_motion > 0.1 or max(motion_scores) > 0.3):
                duplicated_runs.append({
                    "start_frame": frame_indices[current_run_start],
                    "end_frame": frame_indices[-1],
                    "start_time_s": round(timestamps[current_run_start], 2),
                    "end_time_s": round(timestamps[-1], 2),
                    "duration_s": round(timestamps[-1] - timestamps[current_run_start], 2),
                })

        if duplicated_runs:
            findings.append(
                Finding(
                    module=self.name,
                    check_name="duplicated_frames",
                    result=FindingResult.TAMPERED,
                    confidence=0.90,
                    explanation=(
                        f"Detected {len(duplicated_runs)} repeated/looped frame sequence(s). Identical visual content "
                        "was artificially injected or looped into the active surveillance timeline."
                    ),
                    evidence={"duplicated_runs": duplicated_runs, "global_avg_motion": round(global_avg_motion, 2)},
                )
            )
        else:
            findings.append(
                Finding(
                    module=self.name,
                    check_name="duplicated_frames",
                    result=FindingResult.PASS,
                    confidence=0.88,
                    explanation="No artificial frame freezes or looping segments detected in timeline.",
                    evidence={"evaluated_frames": len(phashes)},
                )
            )

        # -------------------------------------------------------------
        # 2. Abrupt Motion Cuts & Temporal Discontinuities
        # -------------------------------------------------------------
        # Analyze motion magnitude series with robust z-score
        motion_arr = np.array(motion_scores)
        med_motion = float(np.median(motion_arr))
        mad = float(np.median(np.abs(motion_arr - med_motion)))
        robust_std = max(1.4826 * mad, 0.5)

        cut_points = []
        for i in range(1, len(motion_arr) - 1):
            z_score = (motion_arr[i] - med_motion) / robust_std
            # Sharp isolated spike (at least 3.0 robust z-score, 1.8x neighboring frames, and above 0.8 motion)
            if z_score > 3.0 and motion_arr[i] > 1.8 * max(motion_arr[i-1], motion_arr[i+1], 0.15) and motion_arr[i] > 0.8:
                cut_points.append({
                    "frame_idx": frame_indices[i],
                    "timestamp_s": round(timestamps[i], 2),
                    "motion_score": round(float(motion_arr[i]), 2),
                    "z_score": round(float(z_score), 2),
                })

        # -------------------------------------------------------------
        # 3. Generate Forensic Motion Timeline Chart Artifact
        # -------------------------------------------------------------
        fig, ax = plt.subplots(figsize=(10, 3.5), dpi=120)
        ax.plot(timestamps, motion_scores, color="#007acc", label="Inter-Frame Motion Delta", linewidth=1.2)
        ax.axhline(med_motion + 3.5 * robust_std, color="#ff9900", linestyle="--", alpha=0.7, label="Cut Threshold")

        for cp in cut_points:
            ax.axvline(cp["timestamp_s"], color="#e74c3c", linestyle="-", linewidth=1.8)
            ax.scatter([cp["timestamp_s"]], [cp["motion_score"]], color="#c0392b", zorder=5)

        for dup in duplicated_runs:
            ax.axvspan(dup["start_time_s"], dup["end_time_s"], color="#9b59b6", alpha=0.25, label="Duplicated Loop")

        ax.set_title("CCTV Video Temporal Continuity & Motion Timeline", fontsize=11, fontweight="bold")
        ax.set_xlabel("Timeline (seconds)", fontsize=9)
        ax.set_ylabel("Motion Score (L1 diff)", fontsize=9)
        ax.grid(True, linestyle=":", alpha=0.5)
        # Avoid duplicate legend handles
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(), loc="upper right", fontsize=8)
        fig.tight_layout()

        timeline_buf = Path(storage.scratch_dir / f"{case_id}_{file_id}_timeline.png")
        fig.savefig(str(timeline_buf))
        plt.close(fig)

        timeline_artifact_path = storage.save_artifact(
            case_id=case_id,
            file_id=file_id,
            artifact_name="video_motion_timeline.png",
            content=timeline_buf.read_bytes(),
        )
        if timeline_buf.exists():
            timeline_buf.unlink()

        if cut_points:
            findings.append(
                Finding(
                    module=self.name,
                    check_name="motion_continuity",
                    result=FindingResult.SUSPICIOUS,
                    confidence=0.85,
                    explanation=(
                        f"Detected {len(cut_points)} abrupt temporal discontinuity spike(s) in optical motion flow. "
                        "These indicate potential frame excision, splicing, or edit cut points."
                    ),
                    evidence={"cut_points": cut_points, "median_motion": round(med_motion, 2)},
                    artifact_paths=[timeline_artifact_path],
                )
            )
        else:
            findings.append(
                Finding(
                    module=self.name,
                    check_name="motion_continuity",
                    result=FindingResult.PASS,
                    confidence=0.88,
                    explanation="Optical motion flows smoothly with no anomalous discontinuity spikes.",
                    evidence={"median_motion": round(med_motion, 2)},
                    artifact_paths=[timeline_artifact_path],
                )
            )

        return findings
