#!/usr/bin/env python3
"""
CricketIQ — Automated Model Asset Downloader and Integrity Verifier.
Downloads MediaPipe vision models with SHA256 validation and retry logic.
"""

import os
import sys
import hashlib
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT_DIR / "backend" / "app" / "models" / "assets"

MODELS = {
    "pose_landmarker_full.task": {
        "url": "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task",
        "sha256": "4eaa5eb7a98365221087693fcc286334cf0858e2eb6e15b506aa4a7ecdcec4ad",
        "size_bytes": 9398198,
        "description": "MediaPipe Pose Landmarker Full (33 3D body landmarks)"
    },
    "hand_landmarker.task": {
        "url": "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task",
        "sha256": "fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1",
        "size_bytes": 7819105,
        "description": "MediaPipe Hand Landmarker (21 3D hand/grip landmarks)"
    }
}


def compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def download_file(url: str, dest_path: Path, expected_sha256: str, description: str) -> bool:
    print(f"\n[MODEL] Verifying {dest_path.name} ({description})...")
    if dest_path.exists():
        actual_sha = compute_sha256(dest_path)
        if actual_sha == expected_sha256:
            print(f"  [OK] Already exists and matches SHA256: {actual_sha[:16]}...")
            return True
        else:
            print(f"  [WARN] Checksum mismatch for {dest_path.name}. Re-downloading...")
            dest_path.unlink()

    print(f"  Downloading from {url} ...")
    temp_path = dest_path.with_suffix(".tmp")
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "CricketIQ-Setup/1.0"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp, open(temp_path, "wb") as out_file:
                total_size = int(resp.headers.get("content-length", 0))
                downloaded = 0
                block_size = 65536
                while True:
                    buffer = resp.read(block_size)
                    if not buffer:
                        break
                    downloaded += len(buffer)
                    out_file.write(buffer)
                    if total_size > 0:
                        pct = (downloaded / total_size) * 100
                        print(f"\r  Progress: {pct:5.1f}% ({downloaded / 1024 / 1024:.1f} MB)", end="", flush=True)

            print()
            actual_sha = compute_sha256(temp_path)
            if actual_sha == expected_sha256:
                temp_path.rename(dest_path)
                print(f"  [OK] Verified SHA256: {actual_sha[:16]}... Saved to {dest_path.name}")
                return True
            else:
                print(f"  [FAIL] Downloaded file SHA256 mismatch: {actual_sha} vs expected {expected_sha256}")
                temp_path.unlink(missing_ok=True)
        except Exception as e:
            print(f"  [FAIL] Attempt {attempt} failed: {e}")
            temp_path.unlink(missing_ok=True)

    return False


def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    all_ok = True
    print("=" * 60)
    print("CricketIQ Model Asset Download & Checksum Verification")
    print("=" * 60)
    for filename, meta in MODELS.items():
        dest = MODELS_DIR / filename
        ok = download_file(meta["url"], dest, meta["sha256"], meta["description"])
        if not ok:
            all_ok = False

    print("\n" + "=" * 60)
    if all_ok:
        print("[SUCCESS] All model assets are present and cryptographically verified.")
        sys.exit(0)
    else:
        print("[ERROR] Some model assets failed to download or verify.")
        sys.exit(1)


if __name__ == "__main__":
    main()
