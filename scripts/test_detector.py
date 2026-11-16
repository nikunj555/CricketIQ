#!/usr/bin/env python3
"""
Test script for Roboflow hosted object detection inference.
Sends a single frame from user_cover_drive.mp4 and prints raw predictions.
Never logs or prints the API key.
"""

import os
import sys
import json
from pathlib import Path
import cv2
from dotenv import load_dotenv

# Load local environment if available
load_dotenv()

def main():
    api_key = os.getenv("ROBOFLOW_API_KEY")
    if not api_key or not api_key.strip():
        print("ERROR: ROBOFLOW_API_KEY environment variable is missing or empty.", file=sys.stderr)
        print("Set ROBOFLOW_API_KEY in your environment or .env file before running.", file=sys.stderr)
        sys.exit(1)

    model_id = os.getenv("ROBOFLOW_MODEL_ID", "nikunjs-workspace-a3ulh/cricketiq-1-rfdetr-small-t1")
    base_url = os.getenv("ROBOFLOW_BASE_URL", "https://serverless.roboflow.com").rstrip("/")
    conf_thresh = float(os.getenv("ROBOFLOW_CONFIDENCE_THRESHOLD", "0.35"))

    print(f"Roboflow Detector Configuration:")
    print(f"  Model ID   : {model_id}")
    print(f"  Base URL   : {base_url}")
    print(f"  Confidence : {conf_thresh}")
    print(f"  API Key    : [REDACTED - length {len(api_key.strip())} chars]")

    # Find fixture video
    repo_root = Path(__file__).resolve().parent.parent
    video_path = repo_root / "backend" / "tests" / "fixtures" / "user_cover_drive.mp4"
    if not video_path.exists():
        video_path = repo_root / "storage" / "uploads" / "user_cover_drive.mp4"

    if not video_path.exists():
        print(f"ERROR: Video fixture not found at {video_path}", file=sys.stderr)
        sys.exit(1)

    print(f"\nLoading video frame from: {video_path.name}")
    cap = cv2.VideoCapture(str(video_path))
    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        print("ERROR: Could not decode frame 0 from video.", file=sys.stderr)
        sys.exit(1)

    h, w = frame.shape[:2]
    print(f"Frame shape: {w}x{h} (BGR)")

    # Downscale if wider than 640px to respect memory / network efficiency
    if w > 640:
        scale = 640.0 / w
        frame = cv2.resize(frame, (640, int(h * scale)), interpolation=cv2.INTER_AREA)
        print(f"Downscaled frame to {frame.shape[1]}x{frame.shape[0]} for inference")

    # Run inference using official inference-sdk
    try:
        from inference_sdk import InferenceHTTPClient, InferenceConfiguration
        client = InferenceHTTPClient(
            api_url=base_url,
            api_key=api_key.strip()
        )
        client.configure(InferenceConfiguration(api_key_transport="header"))
        raw_result = client.infer(frame, model_id=model_id)
    except ImportError:
        # Fallback to direct HTTP API if inference-sdk is not installed
        import base64
        import requests
        success, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not success:
            print("ERROR: Failed to encode JPEG frame.", file=sys.stderr)
            sys.exit(1)
        img_b64 = base64.b64encode(buffer).decode("ascii")
        url = f"{base_url}/{model_id}"
        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        resp = requests.post(
            url,
            data=img_b64,
            headers=headers,
            timeout=15.0
        )
        if resp.status_code == 401 or resp.status_code == 403:
            print(f"ERROR (API Key): Unauthorized. Invalid ROBOFLOW_API_KEY. (HTTP {resp.status_code})", file=sys.stderr)
            sys.exit(1)
        elif resp.status_code == 404:
            print(f"ERROR (Model ID): Model '{model_id}' not found on {base_url}. (HTTP 404)", file=sys.stderr)
            sys.exit(1)
        elif resp.status_code == 429:
            print(f"ERROR (Quota): Roboflow inference quota or rate limit exceeded. (HTTP 429)", file=sys.stderr)
            sys.exit(1)
        resp.raise_for_status()
        raw_result = resp.json()
    except Exception as e:
        err_str = str(e)
        if "401" in err_str or "403" in err_str or "Unauthorized" in err_str or "Invalid API Key" in err_str:
            print(f"ERROR (API Key): Roboflow rejected API key (Unauthorized).", file=sys.stderr)
        elif "404" in err_str or "not found" in err_str.lower():
            print(f"ERROR (Model ID): Model '{model_id}' not found on endpoint.", file=sys.stderr)
        elif "429" in err_str or "quota" in err_str.lower() or "rate limit" in err_str.lower():
            print(f"ERROR (Quota): Roboflow inference quota or rate limit exceeded.", file=sys.stderr)
        else:
            print(f"ERROR (Endpoint/Network): Inference request failed: {type(e).__name__}: {err_str}", file=sys.stderr)
        sys.exit(1)

    print("\nInference Response Received:")
    inference_id = raw_result.get("inference_id")
    latency = raw_result.get("time")
    if latency:
        print(f"  Latency    : {latency * 1000:.1f} ms")
    if inference_id:
        print(f"  InferenceID: {inference_id}")

    predictions = raw_result.get("predictions", [])
    print(f"\nRaw Predictions Count: {len(predictions)}")

    filtered = []
    for p in predictions:
        cls_name = p.get("class", "unknown")
        confidence = float(p.get("confidence", 0.0))
        cx = float(p.get("x", 0.0))
        cy = float(p.get("y", 0.0))
        bw = float(p.get("width", 0.0))
        bh = float(p.get("height", 0.0))

        xmin = max(0.0, cx - bw / 2.0)
        ymin = max(0.0, cy - bh / 2.0)
        xmax = cx + bw / 2.0
        ymax = cy + bh / 2.0

        item = {
            "class": cls_name,
            "confidence": round(confidence, 4),
            "box_center": {"x": round(cx, 1), "y": round(cy, 1), "width": round(bw, 1), "height": round(bh, 1)},
            "box_xyxy": [round(xmin, 1), round(ymin, 1), round(xmax, 1), round(ymax, 1)],
            "class_id": p.get("class_id")
        }
        if confidence >= conf_thresh:
            filtered.append(item)

        print(f"  - Class: {cls_name:<12} | Conf: {confidence:.4f} | Center: ({cx:.1f}, {cy:.1f}, w={bw:.1f}, h={bh:.1f}) | Box: [{xmin:.1f}, {ymin:.1f}, {xmax:.1f}, {ymax:.1f}]")

    print(f"\nDetections meeting threshold >= {conf_thresh}: {len(filtered)}")
    print(json.dumps(filtered, indent=2))
    print("\nVERIFICATION COMPLETE: Connection and inference successful.")

if __name__ == "__main__":
    main()
