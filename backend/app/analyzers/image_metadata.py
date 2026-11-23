import io
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ExifTags
import piexif
import imagehash

from app.analyzers.base import BaseAnalyzer
from app.core.models import Finding, FindingResult, MediaType

logger = logging.getLogger("forge.analyzers.image_metadata")

KNOWN_EDITORS = [
    "photoshop", "gimp", "snapseed", "lightroom", "canva", "picsart",
    "corel", "paint.net", "vsco", "inshot", "pixlr", "aftershot",
    "affinity", "phoxo", "fotor", "facetune", "retouch", "meitu"
]


def parse_exif_date(date_str: str) -> Optional[datetime]:
    """Parses standard EXIF date format 'YYYY:MM:DD HH:MM:SS'."""
    if not date_str or not isinstance(date_str, str):
        return None
    date_str = date_str.strip()
    # Replace non-digit separators in date part
    match = re.match(r"^(\d{4})[:\-\/](\d{2})[:\-\/](\d{2})\s+(\d{2}):(\d{2}):(\d{2})", date_str)
    if match:
        try:
            y, m, d, H, M, S = [int(v) for v in match.groups()]
            return datetime(y, m, d, H, M, S, tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def get_decimal_from_dms(dms, ref: str) -> Optional[float]:
    """Converts EXIF degrees, minutes, seconds tuple to decimal degrees."""
    if not dms or len(dms) < 3:
        return None
    try:
        def to_float(val):
            if isinstance(val, tuple) and len(val) == 2 and val[1] != 0:
                return float(val[0]) / float(val[1])
            return float(val)

        degrees = to_float(dms[0])
        minutes = to_float(dms[1])
        seconds = to_float(dms[2])
        decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
        if ref in ["S", "W"]:
            decimal = -decimal
        return decimal
    except Exception:
        return None


class ImageMetadataAnalyzer(BaseAnalyzer):
    """Forensic metadata inspection: EXIF anomalies, editing artifacts, thumbnail mismatch."""

    name: str = "image_metadata"
    version: str = "1.0.0"
    supported_media: List[MediaType] = [MediaType.IMAGE]

    def analyze(self, file_path: Path, case_id: str, file_id: str) -> List[Finding]:
        findings: List[Finding] = []

        try:
            with Image.open(file_path) as img:
                img_format = img.format
                actual_width, actual_height = img.size
                exif_data = img.getexif()
                exif_dict = {}
                gps_dict = {}

                # Attempt raw piexif extraction for thumbnail
                raw_piexif = None
                try:
                    raw_piexif = piexif.load(str(file_path))
                except Exception:
                    pass

                # Parse standard EXIF tags
                if exif_data:
                    for tag_id, value in exif_data.items():
                        tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                        exif_dict[tag_name] = value

                    # Check nested Exif IFD
                    for ifd_id in (ExifTags.IFD.Exif, ExifTags.IFD.GPSInfo):
                        try:
                            ifd_data = exif_data.get_ifd(ifd_id)
                            tag_map = ExifTags.GPSTAGS if ifd_id == ExifTags.IFD.GPSInfo else ExifTags.TAGS
                            for k, v in ifd_data.items():
                                name = tag_map.get(k, str(k))
                                if ifd_id == ExifTags.IFD.GPSInfo:
                                    gps_dict[name] = v
                                else:
                                    exif_dict[name] = v
                        except Exception:
                            pass
        except Exception as exc:
            return [
                Finding(
                    module=self.name,
                    check_name="image_read",
                    result=FindingResult.INCONCLUSIVE,
                    confidence=0.5,
                    explanation=f"Unable to read image header: {str(exc)}",
                )
            ]

        # -------------------------------------------------------------
        # 1. EXIF Presence Check
        # -------------------------------------------------------------
        if not exif_dict:
            findings.append(
                Finding(
                    module=self.name,
                    check_name="exif_presence",
                    result=FindingResult.SUSPICIOUS,
                    confidence=0.70,
                    explanation="EXIF metadata is completely absent or stripped. This is characteristic of social media processing, messaging platforms, or intentional forensic sanitization.",
                    evidence={"format": img_format, "has_exif": False},
                )
            )
            return findings

        findings.append(
            Finding(
                module=self.name,
                check_name="exif_presence",
                result=FindingResult.PASS,
                confidence=0.90,
                explanation="EXIF header structure is present.",
                evidence={"tags_found_count": len(exif_dict)},
            )
        )

        # -------------------------------------------------------------
        # 2. Software Tag / Editing Signature Check
        # -------------------------------------------------------------
        software = str(exif_dict.get("Software", "")).lower()
        processing = str(exif_dict.get("ProcessingSoftware", "")).lower()
        combined_software = f"{software} {processing}".strip()

        editor_detected = None
        for editor in KNOWN_EDITORS:
            if editor in combined_software:
                editor_detected = editor
                break

        if editor_detected:
            findings.append(
                Finding(
                    module=self.name,
                    check_name="editing_software",
                    result=FindingResult.TAMPERED,
                    confidence=0.95,
                    explanation=f"Software tag explicitly identifies post-processing editor: '{editor_detected.upper()}'. Original camera pipeline was altered.",
                    evidence={"software_tag": exif_dict.get("Software"), "detected_editor": editor_detected},
                )
            )
        else:
            findings.append(
                Finding(
                    module=self.name,
                    check_name="editing_software",
                    result=FindingResult.PASS,
                    confidence=0.85,
                    explanation="No known image editing or post-processing software signatures detected in metadata tags.",
                    evidence={"software_tag": exif_dict.get("Software", "Not set")},
                )
            )

        # -------------------------------------------------------------
        # 3. Timestamp Consistency Check
        # -------------------------------------------------------------
        date_original_str = str(exif_dict.get("DateTimeOriginal") or exif_dict.get("CreateDate") or "")
        date_modify_str = str(exif_dict.get("DateTime") or exif_dict.get("ModifyDate") or "")

        dt_orig = parse_exif_date(date_original_str)
        dt_mod = parse_exif_date(date_modify_str)

        if dt_orig and dt_orig > datetime.now(timezone.utc):
            findings.append(
                Finding(
                    module=self.name,
                    check_name="timestamp_validity",
                    result=FindingResult.TAMPERED,
                    confidence=0.98,
                    explanation=f"DateTimeOriginal ({date_original_str}) is in the future relative to UTC analysis time.",
                    evidence={"date_original": date_original_str},
                )
            )
        elif dt_orig and dt_mod:
            delta_seconds = abs((dt_mod - dt_orig).total_seconds())
            if delta_seconds > 60:
                findings.append(
                    Finding(
                        module=self.name,
                        check_name="timestamp_consistency",
                        result=FindingResult.SUSPICIOUS,
                        confidence=0.80,
                        explanation=f"Modification timestamp ({date_modify_str}) differs from capture timestamp ({date_original_str}) by {int(delta_seconds)}s.",
                        evidence={
                            "date_original": date_original_str,
                            "date_modified": date_modify_str,
                            "delta_seconds": delta_seconds,
                        },
                    )
                )
            else:
                findings.append(
                    Finding(
                        module=self.name,
                        check_name="timestamp_consistency",
                        result=FindingResult.PASS,
                        confidence=0.90,
                        explanation="Capture and modification timestamps are synchronized.",
                        evidence={"date_original": date_original_str, "date_modified": date_modify_str},
                    )
                )
        else:
            findings.append(
                Finding(
                    module=self.name,
                    check_name="timestamp_consistency",
                    result=FindingResult.NOT_APPLICABLE,
                    confidence=0.50,
                    explanation="Insufficient timestamp fields available for cross-comparison.",
                    evidence={"found_dates": {"original": date_original_str, "modified": date_modify_str}},
                )
            )

        # -------------------------------------------------------------
        # 4. GPS Geolocation Validity
        # -------------------------------------------------------------
        if gps_dict:
            lat = get_decimal_from_dms(gps_dict.get("GPSLatitude"), str(gps_dict.get("GPSLatitudeRef", "N")))
            lon = get_decimal_from_dms(gps_dict.get("GPSLongitude"), str(gps_dict.get("GPSLongitudeRef", "E")))

            if lat is not None and lon is not None:
                if (lat == 0.0 and lon == 0.0) or not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
                    findings.append(
                        Finding(
                            module=self.name,
                            check_name="gps_validity",
                            result=FindingResult.SUSPICIOUS,
                            confidence=0.85,
                            explanation=f"GPS coordinates ({lat}, {lon}) are out of valid bounds or set to Null Island (0, 0).",
                            evidence={"latitude": lat, "longitude": lon},
                        )
                    )
                else:
                    findings.append(
                        Finding(
                            module=self.name,
                            check_name="gps_validity",
                            result=FindingResult.PASS,
                            confidence=0.95,
                            explanation=f"Valid GPS coordinates captured: {lat:.6f}, {lon:.6f}.",
                            evidence={
                                "latitude": lat,
                                "longitude": lon,
                                "osm_url": f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=16/{lat}/{lon}",
                            },
                        )
                    )
        else:
            findings.append(
                Finding(
                    module=self.name,
                    check_name="gps_validity",
                    result=FindingResult.NOT_APPLICABLE,
                    confidence=0.50,
                    explanation="No GPS geolocation coordinates recorded in image EXIF tags.",
                )
            )

        # -------------------------------------------------------------
        # 5. Embedded Thumbnail Discrepancy Check
        # -------------------------------------------------------------
        thumb_bytes = None
        if raw_piexif and isinstance(raw_piexif.get("thumbnail"), (bytes, bytearray)) and len(raw_piexif["thumbnail"]) > 100:
            thumb_bytes = raw_piexif["thumbnail"]

        if thumb_bytes:
            try:
                with Image.open(io.BytesIO(thumb_bytes)) as thumb_img, Image.open(file_path) as full_img:
                    hash_thumb = imagehash.phash(thumb_img)
                    hash_full = imagehash.phash(full_img)
                    phash_distance = hash_thumb - hash_full

                    if phash_distance > 15:
                        findings.append(
                            Finding(
                                module=self.name,
                                check_name="thumbnail_discrepancy",
                                result=FindingResult.TAMPERED,
                                confidence=0.88,
                                explanation=(
                                    f"Embedded thumbnail perceptual hash differs significantly from main image "
                                    f"(Hamming distance: {phash_distance} > 15). The full-resolution image was edited "
                                    f"without updating the embedded preview thumbnail."
                                ),
                                evidence={"phash_distance": phash_distance, "threshold": 15},
                            )
                        )
                    else:
                        findings.append(
                            Finding(
                                module=self.name,
                                check_name="thumbnail_discrepancy",
                                result=FindingResult.PASS,
                                confidence=0.92,
                                explanation=f"Embedded thumbnail matches main image content (Hamming distance: {phash_distance}).",
                                evidence={"phash_distance": phash_distance},
                            )
                        )
            except Exception as e:
                findings.append(
                    Finding(
                        module=self.name,
                        check_name="thumbnail_discrepancy",
                        result=FindingResult.INCONCLUSIVE,
                        confidence=0.50,
                        explanation=f"Error parsing embedded thumbnail: {str(e)}",
                    )
                )
        else:
            findings.append(
                Finding(
                    module=self.name,
                    check_name="thumbnail_discrepancy",
                    result=FindingResult.NOT_APPLICABLE,
                    confidence=0.50,
                    explanation="No embedded EXIF thumbnail present in container.",
                )
            )

        # -------------------------------------------------------------
        # 6. Dimensions Consistency Check
        # -------------------------------------------------------------
        exif_w = exif_dict.get("PixelXDimension") or exif_dict.get("ExifImageWidth")
        exif_h = exif_dict.get("PixelYDimension") or exif_dict.get("ExifImageHeight")

        if exif_w and exif_h:
            try:
                ew, eh = int(exif_w), int(exif_h)
                # Allow orientation swap (portrait vs landscape)
                matches = (ew == actual_width and eh == actual_height) or (ew == actual_height and eh == actual_width)
                if not matches:
                    findings.append(
                        Finding(
                            module=self.name,
                            check_name="dimension_consistency",
                            result=FindingResult.SUSPICIOUS,
                            confidence=0.80,
                            explanation=f"Actual pixel dimensions ({actual_width}x{actual_height}) differ from EXIF recorded dimensions ({ew}x{eh}), suggesting crop or resize.",
                            evidence={"actual": [actual_width, actual_height], "exif": [ew, eh]},
                        )
                    )
                else:
                    findings.append(
                        Finding(
                            module=self.name,
                            check_name="dimension_consistency",
                            result=FindingResult.PASS,
                            confidence=0.90,
                            explanation="Pixel dimensions match camera recorded sensor dimensions.",
                            evidence={"dimensions": [actual_width, actual_height]},
                        )
                    )
            except ValueError:
                pass

        return findings
