import logging
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np
from PIL import Image

from app.analyzers.base import BaseAnalyzer
from app.core.models import Finding, FindingResult, MediaType
from app.core.storage import storage

logger = logging.getLogger("forge.analyzers.image_splicing")


class ImageSplicingAnalyzer(BaseAnalyzer):
    """CPU-friendly copy-move detection and noise-inconsistency residual analysis."""

    name: str = "image_splicing"
    version: str = "1.0.0"
    supported_media: List[MediaType] = [MediaType.IMAGE]

    def analyze(self, file_path: Path, case_id: str, file_id: str) -> List[Finding]:
        findings: List[Finding] = []

        try:
            img_bgr = cv2.imread(str(file_path))
            if img_bgr is None:
                raise ValueError("cv2.imread failed to load image")
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape
        except Exception as e:
            return [
                Finding(
                    module=self.name,
                    check_name="image_load",
                    result=FindingResult.INCONCLUSIVE,
                    confidence=0.5,
                    explanation=f"Failed to load image for splicing analysis: {str(e)}",
                )
            ]

        # -------------------------------------------------------------
        # 1. Copy-Move Forgery Detection (ORB + Spatial Clustering)
        # -------------------------------------------------------------
        orb = cv2.ORB_create(nfeatures=1500)
        keypoints, descriptors = orb.detectAndCompute(gray, None)

        copy_move_detected = False
        confirmed_matches = []
        copymove_artifact_path = None

        if descriptors is not None and len(keypoints) >= 20:
            matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
            # Find 3 nearest neighbors for each descriptor
            try:
                raw_matches = matcher.knnMatch(descriptors, descriptors, k=3)
                candidate_pairs = []
                min_spatial_distance = 25.0  # Avoid matching adjacent pixels in smooth texture

                for m_group in raw_matches:
                    for m in m_group:
                        if m.queryIdx == m.trainIdx:
                            continue
                        pt1 = np.array(keypoints[m.queryIdx].pt)
                        pt2 = np.array(keypoints[m.trainIdx].pt)
                        dist = np.linalg.norm(pt1 - pt2)

                        if dist > min_spatial_distance and m.distance < 45:
                            # Avoid duplicate reverse matches
                            if m.queryIdx < m.trainIdx:
                                candidate_pairs.append((m.queryIdx, m.trainIdx, dist, pt1, pt2))

                # Cluster candidate matches by translation vector (dx, dy)
                if len(candidate_pairs) >= 6:
                    vectors = np.array([(pt2[0] - pt1[0], pt2[1] - pt1[1]) for _, _, _, pt1, pt2 in candidate_pairs])
                    
                    # Bin vectors in 2D space (bin size 30px)
                    bins = {}
                    for idx, vec in enumerate(vectors):
                        key = (int(vec[0] // 30), int(vec[1] // 30))
                        bins.setdefault(key, []).append(idx)

                    # Find largest coherent motion cluster
                    largest_bin = max(bins.values(), key=len) if bins else []
                    if len(largest_bin) >= 6:
                        # Validate cluster consistency with RANSAC affine transform
                        src_pts = np.float32([candidate_pairs[i][3] for i in largest_bin]).reshape(-1, 1, 2)
                        dst_pts = np.float32([candidate_pairs[i][4] for i in largest_bin]).reshape(-1, 1, 2)

                        _, inliers = cv2.estimateAffinePartial2D(src_pts, dst_pts, method=cv2.RANSAC, ransacReprojThreshold=15.0)
                        inlier_count = int(np.sum(inliers)) if inliers is not None else 0

                        if inlier_count >= 5:
                            copy_move_detected = True
                            confirmed_matches = [candidate_pairs[largest_bin[i]] for i in range(len(largest_bin)) if inliers is not None and inliers[i][0]]

                            # Draw copy-move overlay
                            vis_img = img_bgr.copy()
                            for _, _, _, pt1, pt2 in confirmed_matches:
                                p1 = (int(pt1[0]), int(pt1[1]))
                                p2 = (int(pt2[0]), int(pt2[1]))
                                cv2.circle(vis_img, p1, 5, (0, 0, 255), -1)
                                cv2.circle(vis_img, p2, 5, (255, 0, 0), -1)
                                cv2.line(vis_img, p1, p2, (0, 255, 255), 2)

                            _, enc = cv2.imencode(".png", vis_img)
                            copymove_artifact_path = storage.save_artifact(
                                case_id=case_id,
                                file_id=file_id,
                                artifact_name="copymove_overlay.png",
                                content=enc.tobytes(),
                            )
            except Exception as e:
                logger.warning(f"Copy-move matching failed: {e}")

        if copy_move_detected:
            findings.append(
                Finding(
                    module=self.name,
                    check_name="copy_move_forgery",
                    result=FindingResult.TAMPERED,
                    confidence=0.92,
                    explanation=(
                        f"Detected {len(confirmed_matches)} geometric keypoint pairs demonstrating coherent spatial duplication. "
                        "A region of the image was copied and cloned to another location."
                    ),
                    evidence={
                        "matched_pairs_count": len(confirmed_matches),
                        "cluster_size": len(confirmed_matches),
                    },
                    artifact_paths=[copymove_artifact_path] if copymove_artifact_path else [],
                )
            )
        else:
            findings.append(
                Finding(
                    module=self.name,
                    check_name="copy_move_forgery",
                    result=FindingResult.PASS,
                    confidence=0.85,
                    explanation="No duplicated regions or clone-stamp patterns detected via keypoint clustering.",
                    evidence={"evaluated_keypoints": len(keypoints)},
                )
            )

        # -------------------------------------------------------------
        # 2. Noise Inconsistency Residual Analysis (Median High-Pass)
        # -------------------------------------------------------------
        # High-pass noise residual: R = Image - MedianFiltered(Image)
        denoised = cv2.medianBlur(gray, 3)
        residual = cv2.absdiff(gray, denoised).astype(np.float32)

        # Compute local variance in 32x32 blocks
        block_size = 32
        h_blocks = h // block_size
        w_blocks = w // block_size

        if h_blocks >= 4 and w_blocks >= 4:
            var_map = np.zeros((h_blocks, w_blocks), dtype=np.float32)
            for by in range(h_blocks):
                for bx in range(w_blocks):
                    block = residual[by*block_size:(by+1)*block_size, bx*block_size:(bx+1)*block_size]
                    var_map[by, bx] = float(np.var(block))

            median_var = float(np.median(var_map))
            q75, q25 = np.percentile(var_map, [75, 25])
            iqr = max(float(q75 - q25), 0.05)

            # Detect outlier blocks (> 3.5 IQR from median)
            outlier_mask = np.abs(var_map - median_var) > (3.5 * iqr)
            outlier_count = int(np.sum(outlier_mask))
            total_blocks = h_blocks * w_blocks
            outlier_ratio = outlier_count / total_blocks

            # Visualize noise map
            norm_var = cv2.normalize(var_map, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
            var_heatmap = cv2.applyColorMap(norm_var, cv2.COLORMAP_VIRIDIS)
            var_heatmap_resized = cv2.resize(var_heatmap, (w, h), interpolation=cv2.INTER_NEAREST)

            # Draw rectangles on outlier blocks
            for by in range(h_blocks):
                for bx in range(w_blocks):
                    if outlier_mask[by, bx]:
                        x1, y1 = bx * block_size, by * block_size
                        cv2.rectangle(var_heatmap_resized, (x1, y1), (x1 + block_size, y1 + block_size), (0, 0, 255), 2)

            _, enc_noise = cv2.imencode(".png", var_heatmap_resized)
            noise_artifact_path = storage.save_artifact(
                case_id=case_id,
                file_id=file_id,
                artifact_name="noise_variance_map.png",
                content=enc_noise.tobytes(),
            )

            # Suspicious if between 1% and 15% of blocks are anomalous (compact localized splice)
            if 0.01 <= outlier_ratio <= 0.20:
                findings.append(
                    Finding(
                        module=self.name,
                        check_name="noise_inconsistency",
                        result=FindingResult.SUSPICIOUS,
                        confidence=0.80,
                        explanation=(
                            f"Detected localized noise variance anomalies in {outlier_count} block(s) ({outlier_ratio*100:.1f}% of image). "
                            "Local high-frequency sensor noise is inconsistent with the global background noise floor, indicating spliced foreign content."
                        ),
                        evidence={
                            "anomalous_blocks": outlier_count,
                            "outlier_ratio": round(outlier_ratio, 3),
                            "median_variance": round(median_var, 2),
                        },
                        artifact_paths=[noise_artifact_path],
                    )
                )
            else:
                findings.append(
                    Finding(
                        module=self.name,
                        check_name="noise_inconsistency",
                        result=FindingResult.PASS,
                        confidence=0.85,
                        explanation="High-frequency sensor noise floor is statistically uniform across all image blocks.",
                        evidence={"median_variance": round(median_var, 2), "outlier_ratio": round(outlier_ratio, 3)},
                        artifact_paths=[noise_artifact_path],
                    )
                )
        else:
            findings.append(
                Finding(
                    module=self.name,
                    check_name="noise_inconsistency",
                    result=FindingResult.NOT_APPLICABLE,
                    confidence=0.50,
                    explanation="Image resolution too low for 32x32 block noise variance profiling.",
                )
            )

        return findings
