import io
import logging
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageEnhance
from scipy.fftpack import dct

from app.analyzers.base import BaseAnalyzer
from app.core.models import Finding, FindingResult, MediaType
from app.core.storage import storage

logger = logging.getLogger("forge.analyzers.image_ela")


def compute_dct_periodicity(gray_img: np.ndarray) -> Tuple[bool, float]:
    """Detects double JPEG compression by analyzing DCT coefficient histogram periodicity.
    
    Returns:
        Tuple of (is_double_compressed: bool, periodicity_strength: float)
    """
    h, w = gray_img.shape
    h_blocks = (h // 8) * 8
    w_blocks = (w // 8) * 8
    if h_blocks < 16 or w_blocks < 16:
        return False, 0.0

    cropped = gray_img[:h_blocks, :w_blocks].astype(np.float32) - 128.0

    # Collect selected AC coefficients across all 8x8 blocks (e.g., frequencies (1,2) and (2,1))
    coeffs = []
    for y in range(0, h_blocks, 8):
        for x in range(0, w_blocks, 8):
            block = cropped[y:y+8, x:x+8]
            # 2D DCT on 8x8 block
            block_dct = cv2.dct(block)
            coeffs.append(block_dct[1, 2])
            coeffs.append(block_dct[2, 1])

    if not coeffs:
        return False, 0.0

    coeffs_arr = np.array(coeffs, dtype=np.int32)
    # Restrict to meaningful range [-50, 50]
    filtered = coeffs_arr[(coeffs_arr >= -50) & (coeffs_arr <= 50)]
    if len(filtered) < 100:
        return False, 0.0

    counts, _ = np.histogram(filtered, bins=101, range=(-50, 50))
    # Autocorrelation of histogram to detect periodic gaps/peaks
    norm_counts = counts - np.mean(counts)
    autocorr = np.correlate(norm_counts, norm_counts, mode="full")
    autocorr = autocorr[len(autocorr)//2:]

    if len(autocorr) > 10 and autocorr[0] > 0:
        # Check secondary peaks (lag 2 to 8)
        norm_autocorr = autocorr / autocorr[0]
        peak_score = float(np.max(norm_autocorr[2:8])) if len(norm_autocorr) > 8 else 0.0
        return peak_score > 0.45, peak_score

    return False, 0.0


class ImageELAAnalyzer(BaseAnalyzer):
    """Error Level Analysis (ELA) and DCT Double Compression Detector."""

    name: str = "image_ela"
    version: str = "1.0.0"
    supported_media: List[MediaType] = [MediaType.IMAGE]

    def analyze(self, file_path: Path, case_id: str, file_id: str) -> List[Finding]:
        findings: List[Finding] = []

        try:
            with Image.open(file_path) as original_img:
                is_jpeg = original_img.format == "JPEG"
                img_rgb = original_img.convert("RGB")
                quant_tables = getattr(original_img, "quantization", None)
        except Exception as e:
            return [
                Finding(
                    module=self.name,
                    check_name="image_open",
                    result=FindingResult.INCONCLUSIVE,
                    confidence=0.5,
                    explanation=f"Failed to open image for ELA: {str(e)}",
                )
            ]

        # -------------------------------------------------------------
        # 1. Error Level Analysis (ELA) Computation
        # -------------------------------------------------------------
        if not is_jpeg:
            findings.append(
                Finding(
                    module=self.name,
                    check_name="ela_heatmap",
                    result=FindingResult.NOT_APPLICABLE,
                    confidence=0.90,
                    explanation="Error Level Analysis applies specifically to lossy JPEG formats. The provided input is lossless or non-JPEG.",
                    evidence={"format": original_img.format},
                )
            )
        else:
            # Resave in-memory at quality 90
            buffer = io.BytesIO()
            img_rgb.save(buffer, "JPEG", quality=90)
            buffer.seek(0)
            resaved_img = Image.open(buffer)

            # Compute absolute difference and amplify
            ela_diff = ImageChops.difference(img_rgb, resaved_img)
            # Find extrema across bands
            extrema = ela_diff.getextrema()
            max_diff = max([ex[1] for ex in extrema]) if extrema else 1
            scale = 255.0 / max(max_diff, 1)

            # Enhanced difference image
            ela_enhanced = ImageEnhance.Brightness(ela_diff).enhance(scale)

            # Generate Color Heatmap using OpenCV for visualization
            ela_cv = cv2.cvtColor(np.array(ela_diff), cv2.COLOR_RGB2GRAY)
            # Normalize to 0-255
            norm_ela = cv2.normalize(ela_cv, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
            heatmap_color = cv2.applyColorMap(norm_ela, cv2.COLORMAP_JET)

            # Save heatmap artifact
            _, encoded_png = cv2.imencode(".png", heatmap_color)
            artifact_path = storage.save_artifact(
                case_id=case_id,
                file_id=file_id,
                artifact_name="ela_heatmap.png",
                content=encoded_png.tobytes(),
            )

            # Regional Error Level Statistics
            mean_error = float(np.mean(norm_ela))
            std_error = float(np.std(norm_ela))

            # Threshold for high error regions (mean + 2.5 * std)
            thresh_val = mean_error + 2.5 * max(std_error, 1.0)
            _, thresh_mask = cv2.threshold(norm_ela, min(thresh_val, 240), 255, cv2.THRESH_BINARY)

            contours, _ = cv2.findContours(thresh_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            suspicious_regions = []
            img_area = norm_ela.shape[0] * norm_ela.shape[1]

            for cnt in contours:
                area = cv2.contourArea(cnt)
                # Filter out tiny noise dots (< 0.05% of image) and global background (> 40% of image)
                if 0.0005 * img_area < area < 0.40 * img_area:
                    x, y, w, h = cv2.boundingRect(cnt)
                    roi = norm_ela[y:y+h, x:x+w]
                    roi_mean = float(np.mean(roi))
                    z_score = (roi_mean - mean_error) / max(std_error, 0.001)
                    if z_score > 2.5:
                        suspicious_regions.append({
                            "bbox": [x, y, w, h],
                            "area_pixels": int(area),
                            "z_score": round(z_score, 2),
                            "regional_mean_error": round(roi_mean, 2),
                        })

            if suspicious_regions:
                # Sort by highest z-score
                suspicious_regions.sort(key=lambda r: r["z_score"], reverse=True)
                top_regions = suspicious_regions[:5]
                findings.append(
                    Finding(
                        module=self.name,
                        check_name="ela_regional_anomaly",
                        result=FindingResult.SUSPICIOUS,
                        confidence=0.85,
                        explanation=(
                            f"Detected {len(suspicious_regions)} localized region(s) with significantly higher compression "
                            f"error levels (top regional z-score: {top_regions[0]['z_score']}). This indicates content with a "
                            f"different compression history (e.g. pasted or spliced elements)."
                        ),
                        evidence={
                            "global_mean_error": round(mean_error, 2),
                            "global_std_error": round(std_error, 2),
                            "suspicious_regions_count": len(suspicious_regions),
                            "top_regions": top_regions,
                        },
                        artifact_paths=[artifact_path],
                    )
                )
            else:
                findings.append(
                    Finding(
                        module=self.name,
                        check_name="ela_regional_anomaly",
                        result=FindingResult.PASS,
                        confidence=0.88,
                        explanation="Error levels across image regions are uniformly distributed with no anomalous high-error clusters.",
                        evidence={"global_mean_error": round(mean_error, 2), "global_std_error": round(std_error, 2)},
                        artifact_paths=[artifact_path],
                    )
                )

        # -------------------------------------------------------------
        # 2. Quantization Table & DCT Double Compression Check
        # -------------------------------------------------------------
        gray = cv2.cvtColor(np.array(img_rgb), cv2.COLOR_RGB2GRAY)
        is_double, peak_score = compute_dct_periodicity(gray)

        if is_double:
            findings.append(
                Finding(
                    module=self.name,
                    check_name="dct_double_compression",
                    result=FindingResult.TAMPERED,
                    confidence=0.87,
                    explanation=(
                        f"DCT coefficient histogram exhibits strong periodicity (peak score: {peak_score:.2f} > 0.45). "
                        "This indicates that the image was compressed, edited or modified, and re-saved at a secondary JPEG quality."
                    ),
                    evidence={"dct_periodicity_score": round(peak_score, 3), "has_quantization_tables": bool(quant_tables)},
                )
            )
        else:
            findings.append(
                Finding(
                    module=self.name,
                    check_name="dct_double_compression",
                    result=FindingResult.PASS,
                    confidence=0.82,
                    explanation="No significant periodic DCT coefficient histogram modulation detected.",
                    evidence={"dct_periodicity_score": round(peak_score, 3), "has_quantization_tables": bool(quant_tables)},
                )
            )

        return findings
