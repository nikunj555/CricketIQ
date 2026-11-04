# CricketIQ — REST API Documentation

The CricketIQ backend runs on FastAPI with interactive OpenAPI documentation accessible at `http://127.0.0.1:8000/docs`.

---

## Base URL
```
http://127.0.0.1:8000/api
```

---

## Endpoints

### 1. System Health
* **`GET /api/health`**
  * Description: Verifies backend uptime and loaded ML model status.
  * Response:
    ```json
    {
      "status": "healthy",
      "service": "CricketIQ — Explainable AI Cricket Batting Technique Analyzer",
      "version": "1.0.0",
      "device": "cpu",
      "models": {
        "pose_estimator": { "name": "MediaPipe Pose Landmarker Full", "loaded": true },
        "phase_classifier": { "name": "BiLSTM Temporal Action Phase Classifier", "loaded": true }
      }
    }
    ```

### 2. Live Batting Coach (Real-Time Mode A)
* **`POST /api/live/process-frame`**
  * Description: Ingests sampled webcam frames (base64) at ~10-15 FPS. Runs MediaPipe Pose inference, computes instantaneous joint angles (knee, torso, head), and steps the temporal state machine (`waiting_for_player` -> `ready_for_shot` -> `shot_in_progress` -> `shot_completed`).
  * Request Body:
    ```json
    {
      "image_base64": "data:image/jpeg;base64,...",
      "timestamp_ms": 1729900000.0,
      "session_id": "live_sess_102",
      "handedness": "Right",
      "shot_hint": "Cover Drive",
      "manual_trigger": null
    }
    ```
  * Response includes:
    * `state`: Current state ("ready_for_shot", "shot_in_progress", "shot_completed", etc.)
    * `landmarks_normalized`: 33 normalized coordinates for real-time canvas HUD overlay
    * `current_lead_knee`, `current_torso_lean`, `latency_ms`

* **`POST /api/live/analyze-attempt`**
  * Description: Evaluates a completed live batting attempt. Applies PyTorch BiLSTM temporal phase classification, identifies impact window, generates an explainable feedback card with practical drill recommendations, computes previous-attempt deltas, and saves the attempt to SQLite.
  * Response includes:
    * `attempt_id`, `shot_type`, `main_observation`, `evidence`, `why_it_matters`, `next_action_drill`, `confidence_score`, `processing_latency_ms`, `previous_attempt_comparison`.

* **`WebSocket /api/live/ws/{session_id}`**
  * Description: Real-time bidirectional WebSocket stream for frame capture and immediate post-shot feedback push notifications.

### 3. Video Ingestion & Streaming (Mode B)
* **`POST /api/video/upload`** (Multipart/Form-Data)
  * Parameters:
    * `file`: Binary video file (.mp4, .mov, .avi, .webm)
    * `shot_type`: "Cover Drive" | "Straight Drive" | "Pull Shot" | "Cut Shot" | "Forward Defensive" | "Unknown"
    * `handedness`: "Right" | "Left"
    * `camera_angle`: "Side View" | "Oblique View" | "Front View"
  * Response:
    ```json
    {
      "session_id": "demo_cd1",
      "filename": "sample_cover_drive.mp4",
      "shot_type": "Cover Drive",
      "handedness": "Right",
      "camera_angle": "Side View",
      "message": "Video uploaded successfully. Biomechanical analysis in progress.",
      "video_url": "/api/video/original/demo_cd1_sample_cover_drive.mp4"
    }
    ```

* **`GET /api/video/status/{session_id}`**
  * Description: Polling endpoint for background processing progress.
  * Response:
    ```json
    {
      "session_id": "demo_cd1",
      "status": "completed",
      "progress": 100.0,
      "current_step": "Analysis complete",
      "error": null
    }
    ```

* **`GET /api/video/annotated/{filename}`**
  * Returns: MP4 stream of skeleton-annotated video with HUD overlay.

* **`GET /api/video/thumbnail/{filename}`**
  * Returns: JPEG thumbnail captured at the impact window.

### 3. Biomechanical Analysis
* **`GET /api/analysis/{session_id}`**
  * Description: Retrieves full kinematic telemetry, 7-phase timeline, and explainable coaching feedback.
  * Response includes:
    * `summary`: Lead knee flexion at impact, torso forward lean, head stability index, stance width ratio, smoothness score, tracking rate.
    * `phases`: Contiguous list of phase segments with start/end frames and keyframes.
    * `time_series`: Frame-by-frame joint angles and normalized metrics.
    * `coaching_feedback`: Structured evidence-grounded observations with practical drills and disclaimers.
    * `limitations`: System boundary declarations.

### 4. Reference Comparison
* **`GET /api/comparison/references`**
  * Returns list of pre-calibrated MCC benchmark strokes.
* **`POST /api/comparison/compare`**
  * Body: `{ "session_id": "demo_cd1", "reference_id": "ref_cover_drive_01", "target_session_id": null }`
  * Returns: DTW normalized distance, trajectory similarity score (0-100%), aligned time series, and key moment differences.

### 5. Session Persistence
* **`GET /api/sessions`**
  * Returns list of past sessions with shot-type breakdown counts.
* **`DELETE /api/sessions/{session_id}`**
  * Removes session record and associated media storage files.

### 6. Research Benchmarks
* **`GET /api/evaluation/report`**
  * Returns actual experimental test metrics: accuracy, macro F1, confusion matrix, per-class metrics, baseline comparison, loss curves.
