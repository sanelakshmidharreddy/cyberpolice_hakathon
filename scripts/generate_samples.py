"""FORGE Reproducible Forensic Sample Generator.
Cyber Hackathon 2026 | PS-05 | Track: Digital Forensics

Generates strictly non-copyrighted, realistic authentic and tampered media pairs
under 3 MB each for images, CCTV video streams, and audio recordings:
- samples/demo_authentic_scene.jpg & samples/demo_tampered_splice.jpg
- samples/demo_authentic_voice.wav & samples/demo_tampered_splice.wav
- samples/demo_authentic_cctv.mp4 & samples/demo_tampered_cctv.mp4
Also updates legacy sample files for full backward compatibility.
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
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
import piexif

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
SAMPLES_DIR = WORKSPACE_ROOT / "samples"


def ensure_samples_dir():
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)


# ==============================================================================
# 1. IMAGE SAMPLES: SCENE VS SPLICED REGION WITH EXIF ARTIFACTS
# ==============================================================================

def generate_image_samples() -> List[Tuple[str, str, str]]:
    ensure_samples_dir()
    records = []

    # Authentic camera capture scene: 800x600 resolution with rich natural texture
    w, h = 800, 600
    img_orig = Image.new("RGB", (w, h), color=(135, 175, 210))  # Sky gradient base
    draw = ImageDraw.Draw(img_orig)

    # Realistic architectural scene: building facade + entrance
    draw.rectangle([0, 420, w, h], fill=(60, 65, 70))  # Pavement
    draw.rectangle([100, 180, 700, 420], fill=(210, 200, 185))  # Wall
    draw.rectangle([120, 200, 680, 240], fill=(160, 140, 120))  # Cornice banner

    # Windows
    for wx in range(160, 660, 120):
        draw.rectangle([wx, 260, wx + 70, 360], fill=(40, 60, 90))
        draw.line([wx + 35, 260, wx + 35, 360], fill=(230, 230, 230), width=2)
        draw.line([wx, 310, wx + 70, 310], fill=(230, 230, 230), width=2)

    # Add realistic sensor photon noise
    np_img = np.array(img_orig, dtype=np.float32)
    np.random.seed(42)
    noise = np.random.normal(0, 3.5, np_img.shape)
    np_img = np.clip(np_img + noise, 0, 255).astype(np.uint8)
    img_textured = Image.fromarray(np_img)

    # Camera EXIF tags (Nikon D850 DSLR, unedited)
    camera_date = "2026:02:18 14:35:10"
    zeroth_ifd = {
        piexif.ImageIFD.Make: "Nikon",
        piexif.ImageIFD.Model: "NIKON D850",
        piexif.ImageIFD.Software: "D850 Ver.1.20",
        piexif.ImageIFD.DateTime: camera_date,
    }
    exif_ifd = {
        piexif.ExifIFD.DateTimeOriginal: camera_date,
        piexif.ExifIFD.DateTimeDigitized: camera_date,
        piexif.ExifIFD.PixelXDimension: w,
        piexif.ExifIFD.PixelYDimension: h,
        piexif.ExifIFD.ExposureTime: (1, 250),
        piexif.ExifIFD.FNumber: (56, 10),
        piexif.ExifIFD.ISOSpeedRatings: 200,
    }
    gps_ifd = {
        piexif.GPSIFD.GPSLatitudeRef: "N",
        piexif.GPSIFD.GPSLatitude: ((25, 1), (36, 1), (12, 1)),  # Patna, Bihar
        piexif.GPSIFD.GPSLongitudeRef: "E",
        piexif.GPSIFD.GPSLongitude: ((85, 1), (8, 1), (45, 1)),
    }
    exif_bytes = piexif.dump({"0th": zeroth_ifd, "Exif": exif_ifd, "GPS": gps_ifd, "1st": {}, "thumbnail": None})

    # Save demo_authentic_scene.jpg
    auth_path = SAMPLES_DIR / "demo_authentic_scene.jpg"
    img_textured.save(str(auth_path), "JPEG", quality=96, exif=exif_bytes)
    # Also save legacy image_original.jpg
    img_textured.save(str(SAMPLES_DIR / "image_original.jpg"), "JPEG", quality=96, exif=exif_bytes)
    records.append(("demo_authentic_scene.jpg", "Image", "Authentic camera capture with intact Nikon EXIF & GPS"))

    # Tampered image: Splice foreign object with different noise profile + editing software tag
    img_tampered = img_textured.copy()
    tampered_cv = np.array(img_tampered)

    # Foreign patch with distinct high-frequency noise and saturation
    patch_w, patch_h = 140, 110
    foreign_patch = np.zeros((patch_h, patch_w, 3), dtype=np.uint8)
    foreign_patch[:] = (180, 45, 30)  # Red warning placard
    cv2.rectangle(foreign_patch, (8, 8), (patch_w - 8, patch_h - 8), (255, 255, 255), 2)
    cv2.putText(foreign_patch, "RESTRICTED", (15, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

    # Add different noise distribution (salt-and-pepper / high variance)
    patch_noise = np.random.normal(0, 12.0, foreign_patch.shape)
    foreign_patch = np.clip(foreign_patch.astype(np.float32) + patch_noise, 0, 255).astype(np.uint8)

    # Paste spliced patch on building entrance
    tampered_cv[280:280 + patch_h, 330:330 + patch_w] = foreign_patch
    img_spliced_pil = Image.fromarray(tampered_cv)

    # Tampered EXIF: Software tag changed to Photoshop, ModifyDate 2 days later
    zeroth_tampered = {
        piexif.ImageIFD.Make: "Nikon",
        piexif.ImageIFD.Model: "NIKON D850",
        piexif.ImageIFD.Software: "Adobe Photoshop 25.4 (Windows)",
        piexif.ImageIFD.DateTime: "2026:02:20 18:42:00",  # Modified date mismatch
    }
    exif_tampered = {
        piexif.ExifIFD.DateTimeOriginal: camera_date,  # Original capture date remains earlier
        piexif.ExifIFD.PixelXDimension: w,
        piexif.ExifIFD.PixelYDimension: h,
    }
    tampered_exif_bytes = piexif.dump({"0th": zeroth_tampered, "Exif": exif_tampered, "GPS": {}, "1st": {}, "thumbnail": None})

    tamp_path = SAMPLES_DIR / "demo_tampered_splice.jpg"
    img_spliced_pil.save(str(tamp_path), "JPEG", quality=82, exif=tampered_exif_bytes)
    # Also save legacy image_spliced.jpg
    img_spliced_pil.save(str(SAMPLES_DIR / "image_spliced.jpg"), "JPEG", quality=82, exif=tampered_exif_bytes)
    records.append(("demo_tampered_splice.jpg", "Image", "Spliced region + Photoshop signature + timestamp mismatch"))

    # Also keep image_copymove.jpg and image_stripped.jpg for backward compatibility
    copymove_cv = np.array(img_textured)
    copymove_cv[240:310, 480:550] = copymove_cv[240:310, 160:230]
    Image.fromarray(copymove_cv).save(str(SAMPLES_DIR / "image_copymove.jpg"), "JPEG", quality=90)
    img_textured.save(str(SAMPLES_DIR / "image_stripped.jpg"), "JPEG", quality=90)

    return records


# ==============================================================================
# 2. AUDIO SAMPLES: 50 HZ INDIAN ENF CONTINUOUS VS PHASE-JUMP SPLICE
# ==============================================================================

def generate_audio_samples() -> List[Tuple[str, str, str]]:
    ensure_samples_dir()
    records = []
    sr = 16000
    duration_s = 5.0
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)

    # Authentic Voice: Speech formant harmonics + continuous 50.0 Hz Indian mains hum + steady background
    speech_formant = (
        0.35 * np.sin(2 * np.pi * 160 * t) +
        0.20 * np.sin(2 * np.pi * 320 * t) +
        0.10 * np.sin(2 * np.pi * 850 * t)
    )
    # Continuous 50 Hz Electric Network Frequency (ENF)
    enf_continuous = 0.12 * np.sin(2 * np.pi * 50.0 * t)
    # Natural room ambient acoustic noise
    ambient = np.random.normal(0, 0.018, len(t))
    audio_auth = speech_formant + enf_continuous + ambient
    audio_auth = np.clip(audio_auth / np.max(np.abs(audio_auth)), -0.98, 0.98)
    audio_auth_i16 = (audio_auth * 32767).astype(np.int16)

    auth_wav = SAMPLES_DIR / "demo_authentic_voice.wav"
    with wave.open(str(auth_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(audio_auth_i16.tobytes())
    # Also save legacy audio_original.wav
    with wave.open(str(SAMPLES_DIR / "audio_original.wav"), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(audio_auth_i16.tobytes())
    records.append(("demo_authentic_voice.wav", "Audio", "Authentic recording with continuous 50Hz ENF background"))

    # Tampered Voice: Injected cut/splice with abrupt 50 Hz phase discontinuity and elevated noise floor
    splice_start = int(2.0 * sr)
    splice_end = int(3.5 * sr)
    audio_tampered = audio_auth.copy()

    # Invert ENF phase (pi shift) and insert different speech formant
    t_mid = t[splice_start:splice_end]
    spliced_speech = (
        0.35 * np.sin(2 * np.pi * 260 * t_mid) +
        0.15 * np.sin(2 * np.pi * 520 * t_mid)
    )
    # Discontinuous phase 50 Hz hum (phase flipped by 180 degrees)
    enf_discontinuous = -0.12 * np.sin(2 * np.pi * 50.0 * t_mid)
    tampered_noise = np.random.normal(0, 0.065, len(t_mid))  # noticeably different noise floor

    audio_tampered[splice_start:splice_end] = spliced_speech + enf_discontinuous + tampered_noise
    audio_tampered = np.clip(audio_tampered / np.max(np.abs(audio_tampered)), -0.98, 0.98)
    audio_tampered_i16 = (audio_tampered * 32767).astype(np.int16)

    tamp_wav = SAMPLES_DIR / "demo_tampered_splice.wav"
    with wave.open(str(tamp_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(audio_tampered_i16.tobytes())
    # Also save legacy audio_spliced.wav
    with wave.open(str(SAMPLES_DIR / "audio_spliced.wav"), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(audio_tampered_i16.tobytes())

    # Legacy audio_cut.wav with digital zero gap
    audio_cut = audio_auth.copy()
    audio_cut[int(2.0 * sr):int(3.0 * sr)] = 0.0
    audio_cut_i16 = (audio_cut * 32767).astype(np.int16)
    with wave.open(str(SAMPLES_DIR / "audio_cut.wav"), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(audio_cut_i16.tobytes())

    records.append(("demo_tampered_splice.wav", "Audio", "Spliced audio with 50Hz ENF phase inversion and noise jump"))
    return records


# ==============================================================================
# 3. CCTV VIDEO SAMPLES: CONTINUOUS ON-SCREEN CLOCK VS EXCISED 2-SEC JUMP
# ==============================================================================

def render_cctv_frame(frame_num: int, timestamp_sec: int, base_dt: datetime, w: int = 480, h: int = 360) -> np.ndarray:
    frame = np.ones((h, w, 3), dtype=np.uint8) * 35  # Dark surveillance background
    # Security hallway perspective lines
    cv2.line(frame, (40, h), (160, 150), (70, 70, 70), 2)
    cv2.line(frame, (w - 40, h), (w - 160, 150), (70, 70, 70), 2)
    cv2.rectangle(frame, (160, 110), (w - 160, 230), (60, 60, 60), -1)

    # Smooth movement across surveillance zone
    pos_x = int(240 + 130 * math.sin((frame_num * 2 * math.pi) / 120))
    cv2.circle(frame, (pos_x, 260), 16, (0, 200, 240), -1)
    cv2.circle(frame, (pos_x, 240), 7, (220, 220, 220), -1)

    # Burned-in CCTV timestamp banner: "CAM-01 [LIVE] YYYY-MM-DD HH:MM:SS"
    cur_dt = datetime.fromtimestamp(base_dt.timestamp() + timestamp_sec, tz=timezone.utc)
    ts_str = f"CAM-01 [LIVE]  {cur_dt.strftime('%Y-%m-%d %H:%M:%S')}"
    cv2.rectangle(frame, (10, 10), (w - 10, 42), (0, 0, 0), -1)
    cv2.putText(frame, ts_str, (18, 33), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2, cv2.LINE_AA)

    return frame


def generate_video_samples() -> List[Tuple[str, str, str]]:
    ensure_samples_dir()
    records = []
    fps = 25
    w, h = 480, 360
    base_dt = datetime(2026, 3, 15, 14, 30, 0, tzinfo=timezone.utc)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    # 3.1 demo_authentic_cctv.mp4: 5 continuous seconds (125 frames)
    total_frames = 5 * fps
    auth_vid = SAMPLES_DIR / "demo_authentic_cctv.mp4"
    out_auth = cv2.VideoWriter(str(auth_vid), fourcc, fps, (w, h))
    for f in range(total_frames):
        ts_sec = f // fps
        frame = render_cctv_frame(f, ts_sec, base_dt, w, h)
        out_auth.write(frame)
    out_auth.release()
    # Also save legacy cctv_original.mp4
    cv2.imwrite(str(SAMPLES_DIR / "cctv_frame_thumb.jpg"), render_cctv_frame(25, 1, base_dt, w, h))
    records.append(("demo_authentic_cctv.mp4", "Video", "5-second continuous CCTV stream with 1s clock increments"))

    # 3.2 demo_tampered_cctv.mp4: Frame excision (2 seconds deleted in middle -> abrupt 2-sec clock jump)
    tamp_vid = SAMPLES_DIR / "demo_tampered_cctv.mp4"
    out_tamp = cv2.VideoWriter(str(tamp_vid), fourcc, fps, (w, h))
    # Seconds 0 and 1 (frames 0 to 49)
    for f in range(2 * fps):
        ts_sec = f // fps
        frame = render_cctv_frame(f, ts_sec, base_dt, w, h)
        out_tamp.write(frame)
    # Skip seconds 2 & 3: Jump immediately to second 4 (clock jump from 14:30:01 to 14:30:04)
    for f in range(2 * fps, 3 * fps):
        ts_sec = (f // fps) + 2  # jumps 2 seconds ahead
        frame = render_cctv_frame(f + (2 * fps), ts_sec, base_dt, w, h)
        out_tamp.write(frame)
    out_tamp.release()
    records.append(("demo_tampered_cctv.mp4", "Video", "Excision cut: 2 seconds missing with optical and OCR jump"))

    # Also keep cctv_original.mp4 and cctv_cut.mp4 legacy
    import shutil
    shutil.copyfile(str(auth_vid), str(SAMPLES_DIR / "cctv_original.mp4"))
    shutil.copyfile(str(tamp_vid), str(SAMPLES_DIR / "cctv_cut.mp4"))

    return records


def main():
    print("=" * 76)
    print("  FORGE REPRODUCIBLE FORENSIC SAMPLE GENERATOR")
    print("  Cyber Hackathon 2026 | PS-05 | Digital Forensics")
    print("=" * 76)

    all_recs = []
    print("\n[+] Generating authentic & tampered image pairs...")
    all_recs.extend(generate_image_samples())

    print("[+] Generating authentic & tampered audio pairs (with 50Hz ENF)...")
    all_recs.extend(generate_audio_samples())

    print("[+] Generating authentic & tampered CCTV video pairs (burned-in clock)...")
    all_recs.extend(generate_video_samples())

    print("\n" + "=" * 76)
    print(f"{'Filename':<28} | {'Type':<6} | {'Description'}")
    print("-" * 76)
    for name, mtype, desc in all_recs:
        p = SAMPLES_DIR / name
        size_kb = p.stat().st_size / 1024.0 if p.exists() else 0
        print(f"{name:<28} | {mtype:<6} | {desc} ({size_kb:.1f} KB)")
    print("=" * 76)
    print(f"[OK] Generated {len(all_recs)} sample fixtures inside {SAMPLES_DIR}\n")


if __name__ == "__main__":
    main()
