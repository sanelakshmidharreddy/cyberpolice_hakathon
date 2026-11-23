"""FORGE Demo & Test Sample Generator.

Generates strictly non-copyrighted synthetic forensic samples (originals + tampered variants)
for images, CCTV video streams, and audio recordings.
Cyber Hackathon 2026 | PS-05 | Digital Forensics
"""

import math
import os
import struct
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import piexif

SAMPLES_DIR = Path(__file__).resolve().parent


def ensure_samples_dir():
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)


# ==============================================================================
# 1. IMAGE SAMPLE GENERATION
# ==============================================================================

def generate_image_samples() -> List[Tuple[str, str, str, str]]:
    ensure_samples_dir()
    records = []

    # 1.1 image_original.jpg: Authentic camera capture with clean EXIF
    orig_path = SAMPLES_DIR / "image_original.jpg"
    w, h = 640, 480
    img_orig = Image.new("RGB", (w, h), color=(130, 160, 190))
    draw = ImageDraw.Draw(img_orig)
    # Natural landscape-like geometric shapes
    draw.ellipse([450, 40, 530, 120], fill=(255, 230, 100))  # Sun
    draw.polygon([(0, 320), (200, 140), (420, 320)], fill=(70, 90, 70))  # Mountain 1
    draw.polygon([(250, 320), (450, 170), (640, 320)], fill=(90, 110, 90))  # Mountain 2
    draw.rectangle([0, 320, 640, 480], fill=(50, 120, 60))  # Grass

    zeroth_ifd = {
        piexif.ImageIFD.Make: "Sony",
        piexif.ImageIFD.Model: "ILCE-7RM4",
        piexif.ImageIFD.Software: "ILCE-7RM4 v1.20",
        piexif.ImageIFD.DateTime: "2024:05:10 11:22:33",
    }
    exif_ifd = {
        piexif.ExifIFD.DateTimeOriginal: "2024:05:10 11:22:33",
        piexif.ExifIFD.DateTimeDigitized: "2024:05:10 11:22:33",
        piexif.ExifIFD.PixelXDimension: w,
        piexif.ExifIFD.PixelYDimension: h,
    }
    gps_ifd = {
        piexif.GPSIFD.GPSLatitudeRef: "N",
        piexif.GPSIFD.GPSLatitude: ((25, 1), (35, 1), (42, 1)),  # 25 deg 35' 42" N (Patna, Bihar)
        piexif.GPSIFD.GPSLongitudeRef: "E",
        piexif.GPSIFD.GPSLongitude: ((85, 1), (8, 1), (20, 1)),   # 85 deg 8' 20" E
    }
    exif_bytes = piexif.dump({"0th": zeroth_ifd, "Exif": exif_ifd, "GPS": gps_ifd, "1st": {}, "thumbnail": None})
    img_orig.save(str(orig_path), "JPEG", quality=95, exif=exif_bytes)
    records.append(("image_original.jpg", "Image", "Authentic camera capture with valid EXIF & GPS", "AUTHENTIC"))

    # 1.2 image_spliced.jpg: Pasted foreign region with distinct noise, Photoshop software tag
    spliced_path = SAMPLES_DIR / "image_spliced.jpg"
    img_spliced = img_orig.copy()
    # Paste a high-noise object
    np.random.seed(99)
    foreign_patch = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    cv2.circle(foreign_patch, (50, 50), 40, (255, 0, 0), -1)
    img_spliced.paste(Image.fromarray(foreign_patch), (100, 180))

    zeroth_spliced = {
        piexif.ImageIFD.Make: "Sony",
        piexif.ImageIFD.Model: "ILCE-7RM4",
        piexif.ImageIFD.Software: "Adobe Photoshop 2024 (Windows)",
        piexif.ImageIFD.DateTime: "2024:05:12 18:30:00",
    }
    exif_spliced = {
        piexif.ExifIFD.DateTimeOriginal: "2024:05:10 11:22:33",
    }
    exif_spliced_bytes = piexif.dump({"0th": zeroth_spliced, "Exif": exif_spliced, "GPS": {}, "1st": {}, "thumbnail": None})
    img_spliced.save(str(spliced_path), "JPEG", quality=85, exif=exif_spliced_bytes)
    records.append(("image_spliced.jpg", "Image", "Spliced region + Photoshop software signature", "LIKELY_TAMPERED"))

    # 1.3 image_copymove.jpg: Region duplicated within same image
    copymove_path = SAMPLES_DIR / "image_copymove.jpg"
    cv_canvas = np.array(img_orig)
    # Draw textured target at (80, 80)
    for rad in range(8, 30, 4):
        cv2.circle(cv_canvas, (100, 100), rad, (180, 40, 20), 2)
    for i in range(12):
        cv2.circle(cv_canvas, (85 + (i * 7) % 30, 85 + (i * 5) % 30), 2, (0, 0, 0), -1)
    # Clone patch to (340, 240)
    cv_canvas[240:310, 340:410] = cv_canvas[65:135, 65:135]
    Image.fromarray(cv_canvas).save(str(copymove_path), "JPEG", quality=92)
    records.append(("image_copymove.jpg", "Image", "Cloned region duplicated within image (copy-move)", "LIKELY_TAMPERED"))

    # 1.4 image_stripped.jpg: Image with all metadata stripped
    stripped_path = SAMPLES_DIR / "image_stripped.jpg"
    img_orig.save(str(stripped_path), "JPEG", quality=90)
    records.append(("image_stripped.jpg", "Image", "Clean visual content but stripped metadata", "SUSPICIOUS"))

    return records


# ==============================================================================
# 2. CCTV VIDEO SAMPLE GENERATION
# ==============================================================================

def draw_cctv_frame(frame_idx: int, timestamp_sec: int, base_time: datetime, fps: int = 25, total_period: int = 200) -> np.ndarray:
    """Renders a synthetic CCTV surveillance frame with smooth continuous motion and burned-in clock."""
    h, w = 360, 480
    frame = np.ones((h, w, 3), dtype=np.uint8) * 45  # Dark surveillance background
    # Background perspective lines (corridor)
    cv2.line(frame, (60, 360), (180, 160), (80, 80, 80), 2)
    cv2.line(frame, (420, 360), (300, 160), (80, 80, 80), 2)
    cv2.rectangle(frame, (180, 120), (300, 240), (70, 70, 70), -1)

    # Smooth continuous sinusoidal movement across the surveillance field
    angle = (2.0 * math.pi * frame_idx) / total_period
    pos_x = int(240 + 160 * math.sin(angle))
    cv2.circle(frame, (pos_x, 280), 18, (0, 215, 255), -1)
    cv2.circle(frame, (pos_x, 260), 8, (200, 200, 200), -1)

    # Burned-in CCTV timestamp: e.g. "CAM-01 [LIVE] 2026-03-15 10:00:00"
    current_time = datetime.fromtimestamp(base_time.timestamp() + timestamp_sec, tz=timezone.utc)
    clock_str = f"CAM-01 [LIVE]  {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
    cv2.rectangle(frame, (10, 10), (470, 40), (0, 0, 0), -1)
    cv2.putText(frame, clock_str, (15, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2, cv2.LINE_AA)

    return frame


def generate_video_samples() -> List[Tuple[str, str, str, str]]:
    ensure_samples_dir()
    records = []
    fps = 25
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    start_time = datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc)

    # 2.1 cctv_original.mp4 (8 seconds duration, smooth motion, regular clock advance)
    orig_vid_path = SAMPLES_DIR / "cctv_original.mp4"
    out = cv2.VideoWriter(str(orig_vid_path), fourcc, fps, (480, 360))
    total_frames = 8 * fps  # 200 frames
    for f in range(total_frames):
        ts_sec = f // fps
        frame = draw_cctv_frame(f, ts_sec, start_time, fps, total_period=total_frames)
        out.write(frame)
    out.release()
    records.append(("cctv_original.mp4", "Video", "Continuous CCTV stream with smooth 1s/s clock", "AUTHENTIC"))

    # 2.2 cctv_cut.mp4 (Frame excision: cut 4 seconds in the middle -> abrupt position jump & clock jump)
    cut_vid_path = SAMPLES_DIR / "cctv_cut.mp4"
    out_cut = cv2.VideoWriter(str(cut_vid_path), fourcc, fps, (480, 360))
    # First 2 seconds (frames 0 to 50)
    for f in range(2 * fps):
        ts_sec = f // fps
        frame = draw_cctv_frame(f, ts_sec, start_time, fps, total_period=total_frames)
        out_cut.write(frame)
    # Jump 4 seconds ahead (frames 150 to 200) -> creates sharp optical flow jump and clock skip
    for f in range(6 * fps, 8 * fps):
        ts_sec = f // fps
        frame = draw_cctv_frame(f, ts_sec, start_time, fps, total_period=total_frames)
        out_cut.write(frame)
    out_cut.release()
    records.append(("cctv_cut.mp4", "Video", "Abrupt 4-second gap deleted (clock jumps forward)", "LIKELY_TAMPERED"))

    # 2.3 cctv_dup.mp4 (Duplicated/frozen frames: 2 seconds of freeze frame inserted)
    dup_vid_path = SAMPLES_DIR / "cctv_dup.mp4"
    out_dup = cv2.VideoWriter(str(dup_vid_path), fourcc, fps, (480, 360))
    # First 2 seconds normal
    for f in range(2 * fps):
        ts_sec = f // fps
        frame = draw_cctv_frame(f, ts_sec, start_time, fps, total_period=total_frames)
        out_dup.write(frame)
    # 2 seconds (50 frames) frozen on the same frame (duplicate injection)
    freeze_frame = draw_cctv_frame(2 * fps, 2, start_time, fps, total_period=total_frames)
    for _ in range(2 * fps):
        out_dup.write(freeze_frame)
    # Remaining 2 seconds normal
    for f in range(2 * fps, 4 * fps):
        ts_sec = (f // fps) + 2
        frame = draw_cctv_frame(f, ts_sec, start_time, fps, total_period=total_frames)
        out_dup.write(frame)
    out_dup.release()
    records.append(("cctv_dup.mp4", "Video", "Duplicated/looped segment injected into surveillance", "LIKELY_TAMPERED"))
    return records



# ==============================================================================
# 3. AUDIO SAMPLE GENERATION
# ==============================================================================

def generate_audio_samples() -> List[Tuple[str, str, str, str]]:
    ensure_samples_dir()
    records = []
    sample_rate = 16000
    duration_sec = 6

    # 3.1 audio_original.wav: Speech-like formant frequency + 50 Hz power line hum + steady noise
    orig_wav_path = SAMPLES_DIR / "audio_original.wav"
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    # Fundamental voice tone (150 Hz with harmonics)
    signal = 0.4 * np.sin(2 * np.pi * 150 * t) + 0.2 * np.sin(2 * np.pi * 300 * t)
    # Continuous 50 Hz Electrical Network Frequency (ENF) hum
    enf = 0.15 * np.sin(2 * np.pi * 50.0 * t)
    # Steady background acoustic floor
    noise = np.random.normal(0, 0.02, len(t))
    audio_orig = signal + enf + noise
    audio_orig_int16 = (audio_orig / np.max(np.abs(audio_orig)) * 32767).astype(np.int16)

    with wave.open(str(orig_wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_orig_int16.tobytes())
    records.append(("audio_original.wav", "Audio", "Continuous acoustic signal with continuous 50Hz ENF", "AUTHENTIC"))

    # 3.2 audio_spliced.wav: Splice in middle with inverted ENF phase and different noise floor
    spliced_wav_path = SAMPLES_DIR / "audio_spliced.wav"
    splice_start = int(2.5 * sample_rate)
    splice_end = int(4.0 * sample_rate)

    audio_spliced = audio_orig.copy()
    # Invert 50Hz phase and boost noise floor in spliced window
    t_sub = t[splice_start:splice_end]
    audio_spliced[splice_start:splice_end] = (
        0.4 * np.sin(2 * np.pi * 220 * t_sub)  # Different pitch
        - 0.15 * np.sin(2 * np.pi * 50.0 * t_sub)  # Phase discontinuity
        + np.random.normal(0, 0.08, len(t_sub))  # Substantially elevated noise floor
    )
    audio_spliced_int16 = (audio_spliced / np.max(np.abs(audio_spliced)) * 32767).astype(np.int16)

    with wave.open(str(spliced_wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_spliced_int16.tobytes())
    records.append(("audio_spliced.wav", "Audio", "Spliced audio window with ENF phase jump & noise floor change", "LIKELY_TAMPERED"))

    # 3.3 audio_cut.wav: Sudden deletion leaving digital silence / abrupt cut
    cut_wav_path = SAMPLES_DIR / "audio_cut.wav"
    audio_cut = audio_orig.copy()
    audio_cut[int(2.0 * sample_rate):int(3.0 * sample_rate)] = 0.0  # Digital zero run
    audio_cut_int16 = (audio_cut / np.max(np.abs(audio_cut)) * 32767).astype(np.int16)

    with wave.open(str(cut_wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_cut_int16.tobytes())
    records.append(("audio_cut.wav", "Audio", "Abrupt 1.0s digital zero silence cut", "LIKELY_TAMPERED"))

    return records


# ==============================================================================
# MAIN RUNNER & MANIFEST TABLE
# ==============================================================================

def main():
    print("=" * 80)
    print("  FORGE DIGITAL EVIDENCE FIXTURE GENERATOR")
    print("  Cyber Hackathon 2026 | PS-05 | Track: Digital Forensics")
    print("=" * 80)

    all_records = []
    print("\n[+] Generating synthetic image samples...")
    all_records.extend(generate_image_samples())

    print("[+] Generating synthetic CCTV surveillance video streams...")
    all_records.extend(generate_video_samples())

    print("[+] Generating synthetic audio recordings with 50Hz ENF signals...")
    all_records.extend(generate_audio_samples())

    print("\n" + "=" * 80)
    print(f"{'Filename':<22} | {'Media':<6} | {'Description':<38} | {'Expected Verdict'}")
    print("-" * 80)
    for filename, media, desc, verdict in all_records:
        print(f"{filename:<22} | {media:<6} | {desc:<38} | {verdict}")
    print("=" * 80)
    print(f"[OK] Generated {len(all_records)} fixtures successfully in {SAMPLES_DIR}\n")


if __name__ == "__main__":
    main()
