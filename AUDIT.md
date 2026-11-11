# CricketIQ Comprehensive Hardening & Pipeline Audit (Phase 0)

Date: November 2026  
Target Environment: Windows, Python 3.12, FastAPI, Node 20+, React 18, Vite  
Repository Root: `E:\CricketIQ`

---

## 1. Feature Existence & Verification Status

| Feature | Audit Status | Implementation Evidence (File & Line) | Verification Command & Output | Notes / Technical Assessment |
|---|---|---|---|---|
| **Striker Selection** | **Working** | `backend/app/services/pose_service.py:52-300` (`MultiPersonTracker`)<br>`frontend/src/pages/UploadPage.tsx:224-295` | `pytest backend/tests/test_striker_isolation_and_classifier.py`<br>Result: `6 passed in 4.35s` | Implements 4-factor heuristic: batting stance landmark ratios, movement anchor stability, bat swing velocity vs linear run-up, and temporal bounding consistency. User can visually select candidate bounding boxes on frame 0 in UI. |
| **Full-Length Annotated Video with Skeleton** | **Working** | `backend/app/services/video_service.py:200-380`<br>`backend/app/services/annotation_service.py:1-420` | `pytest backend/tests/test_master_acceptance.py`<br>Result: `7 passed in 96.82s` | MediaPipe Landmarker runs frame-by-frame; FFmpeg encodes annotated frames with skeleton overlay, phase tags, and angles at original video FPS and resolution. |
| **Per-Shot Avatar Keyframes** | **Working** | `frontend/src/data/shotAnimations.json:1-1250`<br>`frontend/src/components/RealisticBatterVisualizer.tsx:1-1350` | `node scripts/verify_avatar.cjs`<br>Result: `2843 checks passed across 25 shots, 0 errors`<br>`npx vite build`<br>Result: `built in 1.43s` | All 25 shots in the catalogue possess 7 biomechanically distinct kinematic phases. Grip derivation mathematically anchors hands strictly on the handle with blade pointing to toe. Contact sheet visual proofs stored in `docs/avatar-proof/`. |
| **Calibrated Shot Confidence** | **Working** | `backend/app/services/confidence_service.py:20-185` | `pytest backend/tests/test_shot_recognition.py`<br>Result: `Passed` | Computes confidence as a composite score: classifier probability margin, landmark visibility (occlusion penalization), and camera angle calibration penalty. |
| **Plain-English Feedback with Proof Layer** | **Working** | `backend/app/services/feedback_service.py:30-220`<br>`backend/app/services/plain_language_service.py:20-160` | `pytest backend/tests/test_master_acceptance.py::test_master_e2e_kohli_cover_drive_full_pipeline`<br>Result: `PASSED` | Generates diagnostic feedback linking observed biomechanics (e.g. lead knee angle at impact) directly to target ranges with drill recommendations, strictly adhering to plain English rules. |
| **Shot-Wise Progress Tracking** | **Partial** | `backend/app/services/progress_service.py:15-180`<br>`frontend/src/pages/ProgressPage.tsx:40-210` | `pytest backend/tests/test_master_acceptance.py::test_5_progress_trend_across_three_attempts`<br>Result: `FAILED (AssertionError: assert 'same' in ['improving', 'maintained'])` | Historical session aggregation logic exists, but delta classification threshold marked a 1.5° improvement as `'same'` rather than `'improving'`. |
| **Per-Shot Reference Catalogue (`reference_shots.json`)** | **Partial** | `backend/app/data/reference_shots.json:1-850`<br>`backend/app/data/reference_catalogue.py:20-205` | Verified file structure: contains 25 shots with 7 phases. | Angle trajectories in `reference_catalogue.py` are generated using mathematical synthetic curves (`np.sin(phase_ratio * np.pi)`) rather than empirical marker-tracked pro player data. |

---

## 2. Inventory of Hardcoded, Fake, or Seeded Values

| Location (File:Line) | User-Facing Element | Reality / Source | Remediation Plan |
|---|---|---|---|
| `backend/app/repositories/session_repository.py:112-156` | Seeded session `'virat_kohli_cover_drive'` with score `92.7` | Injected into SQLite on every startup if missing. Fake benchmark. | Remove auto-seeding. Database starts with user-created data only. |
| `backend/app/data/reference_catalogue.py:209-1105` | `AUTHENTIC_REFERENCE_REGISTRY` claiming BCCI/Star Sports archival footage for 25 shots | 22 out of 25 video files do not exist or are synthetic test clips; claim of player attribution (e.g., line 614 references `real_gilchrist_pull.mp4` under player "Rohit Sharma") is unverified/fabricated. | Remove misleading player endorsements; mark video sources accurately. |
| `frontend/src/pages/DashboardPage.tsx:189` | `<div className="text-lg font-bold font-mono text-[#F5F5F5]">Active & Ready</div>` | Static string unlinked to backend system state. | Bind to `/api/health` status response (`healthInfo?.status`). |
| `frontend/src/pages/EvaluationPage.tsx:106-146` | Accuracy `98.7%`, Macro F1 `0.98`, Latency `38ms` | Loaded from `evaluation_report.json`, which was trained on synthetic sine-wave generated sequences (`generate_batting_sequence`), not real video. | Display empty evaluation state until real clip cross-validation is performed. |
| `frontend/src/pages/DashboardPage.tsx:37` vs `backend/app/data/shot_catalogue.py:3-48` | Catalogue shot count displays "27 shots" in certain copy/docs, but catalogue has 25 shots. | Inconsistent documentation and UI copy strings. | Unify to single dynamic source of truth (`/api/shots` length = 25). |
| `frontend/src/pages/AboutPage.tsx:140`, `DashboardPage.tsx:535` | "Side-On (90 degrees)" fixed recommendation | Static UI text suggesting only 90° view is supported. | State supported camera angle tolerance (e.g. 70°–110° side-on). |

---

## 3. Third-Party and Copyrighted Media Audit

| File Path | Size | Origin / Provenance | Usage in Codebase | Copyright / Licensing Risk |
|---|---|---|---|---|
| `storage/uploads/virat_kohli_cover_drive.mp4`<br>`storage/uploads/real_cricketer_cover_drive.mp4`<br>`backend/tests/fixtures/cover_drive.mp4`<br>`backend/tests/fixtures/two_batters.mp4`<br>`storage/uploads/410f6d56_cover_drive.mp4`<br>`storage/uploads/7fb61800_cover_drive.mp4` | 154.5 KB (all identical SHA-256) | Broadcast snippet of Virat Kohli batting. | Seeded DB session (`session_repository.py:118`), E2E test fixtures (`test_core_loop_e2e.py:31`, `test_improvements.py:59`). | **HIGH RISK**: Unlicensed broadcast copyright material. Must be removed from production/distribution. |
| `storage/uploads/adam_gilchrist_raw.ogv`<br>`storage/uploads/real_gilchrist_pull.mp4`<br>`storage/uploads/test_gilchrist.mp4` | 127.2 KB – 588.9 KB | Broadcast footage of Adam Gilchrist playing pull shot. | Seeded in reference registry (`reference_catalogue.py:614`) and test fixtures. | **HIGH RISK**: Unlicensed broadcast footage. Must be removed. |
| `storage/uploads/this_is_batting_raw.ogv`<br>`storage/uploads/9b1a802c_Recording_2026-11-04_022556.mp4`<br>`storage/uploads/ba332080_Recording_2026-11-04_022556.mp4` | 17.1 MB – 17.8 MB | Unverified net practice / YouTube footage. | Upload storage residue. | **MEDIUM RISK**: Unknown provenance; unnecessary clutter. |
| `backend/app/models/assets/pose_landmarker_full.task` | 9.4 MB | Google MediaPipe official model asset. | `backend/app/services/pose_service.py` | **CLEAR**: Apache 2.0 / Google MediaPipe terms. Download script provided (`scripts/download_models.py`). |
| `backend/app/models/assets/hand_landmarker.task` | 7.8 MB | Google MediaPipe official model asset. | `backend/app/services/hand_service.py` | **CLEAR**: Apache 2.0 / Google MediaPipe terms. |
| `backend/app/models/assets/phase_bilstm.pt` | 710 KB | PyTorch weights trained on synthetic curves in `train_phase_model.py`. | Loaded in `phase_service.py`, but bypassed in inference. | **CLEAR** (Internal synthetic, but unused). |

---

## 4. Labelled Clips & Classifier Cross-Validation

```powershell
# Command:
Test-Path "backend/tests/fixtures/labeled"
# Output:
False
```

- **Clips per shot in `backend/tests/fixtures/labeled/<shot>/`:** **0 clips**. Directory does not exist.
- **Current cross-validation accuracy on real footage:** **Unvalidated**.
- **Assessment:** The shot classifier (`classifier_service.py`) relies on rules and DTW against synthetic templates. It has never undergone rigorous clip-level $k$-fold cross-validation on an empirical multi-batter dataset. Under the proposed tiering system, shots without verified empirical clips must be designated `preview_only`.

---

## 5. Active vs. Dead / Unvalidated Services

| Service Name | File Location | Executed in Video Pipeline? | Affects User Scoring or Feedback? | Status & Recommendation |
|---|---|---|---|---|
| **`bat_ball_service`** | `backend/app/services/bat_ball_service.py` | Yes (`video_service.py:332, 573`) | **NO**. Zero metrics, feedback rules, or scores use bat edge or ball proximity. Only draws debug overlay. | **DEAD / UNVALIDATED**. Consumes significant CPU per frame without user benefit. Gate behind `ENABLE_EXPERIMENTAL_BAT_BALL=false` flag. |
| **`hand_service`** | `backend/app/services/hand_service.py` | Yes (`video_service.py:231, 571`) | **NO**. Runs MediaPipe hand landmarker on every frame, but no coaching feedback rules consume hand/wrist closures. | **DEAD / UNVALIDATED**. Gate behind `ENABLE_HAND_LANDMARKER=false` flag to drastically speed up video processing. |
| **`BiLSTM Phase Model`** | `backend/app/services/phase_service.py` | Weights loaded on startup (`_load_model`), but bypassed at line 136 (`_detect_kinematic_phases()`). | **NO**. Replaced entirely by rule-based kinematic detection. | **DEAD IN PRODUCTION**. Formally deprecate synthetic BiLSTM; establish rule-based kinematic detector as primary production engine. |
| **`TensorFlow Import`** | Repo-wide | Not imported in any python file. | **NO**. | **CONFIRMED CLEAN**. No lingering TensorFlow dependencies. |
| **`DTW Service`** | `backend/app/services/dtw_service.py` | Yes (`comparison_service.py:117`) | **YES**. Computes temporal alignment score between input kinematics and reference curves. | **ACTIVE / VALIDATED**. Retain as primary trajectory alignment engine. |

---

## 6. Upload Path Security Review

| Security Area | Current Vulnerability | Exact Code Location | Severity |
|---|---|---|---|
| **Path Traversal** | Raw `file.filename` is concatenated directly into paths: `settings.UPLOADS_DIR / f"temp_inspect_{temp_id}_{file.filename}"` and `safe_filename = f"{session_id}_{file.filename.replace(' ', '_')}"`. Does not strip `../` or null bytes. | `backend/app/api/routes/video.py:27`<br>`backend/app/api/routes/video.py:93` | **CRITICAL** |
| **Magic-Byte Validation** | Only file extension is checked: `ext in ALLOWED_EXTENSIONS`. An attacker can upload arbitrary binaries or scripts named `.mp4`. | `backend/app/api/routes/video.py:20, 85` | **HIGH** |
| **Streaming Size Limit** | Uses unbounded `shutil.copyfileobj(file.file, buffer)`. An attacker can stream hundreds of gigabytes until disk exhaustion (DoS). | `backend/app/api/routes/video.py:30, 96` | **HIGH** |
| **Unauthenticated File Access & Probing** | Endpoints `/api/video/original/{filename}`, `/annotated/{filename}`, `/thumbnail/{filename}` serve raw files to the public with no auth. Line 152 performs `settings.UPLOADS_DIR.glob(f"*{filename}")`, allowing partial pattern matching. | `backend/app/api/routes/video.py:146-193` | **HIGH** |
| **Permissive CORS Configuration** | `BACKEND_CORS_ORIGINS = ["*"]` combined with `allow_credentials=True` in `main.py`. | `backend/app/core/config.py:53`<br>`backend/app/main.py:28` | **MEDIUM** |
| **Information / Path Leaks** | Returns raw Python exception string containing server filesystem paths directly to the client: `detail=f"Failed to save uploaded video: {str(e)}"`. | `backend/app/api/routes/video.py:101` | **MEDIUM** |
| **Rate Limiting** | Completely absent across all video upload and analysis endpoints. | `backend/app/api/routes/video.py` | **MEDIUM** |

---

## 7. Execution Model & Crash Resilience

- **Worker Architecture:** Analysis is dispatched via FastAPI `BackgroundTasks.add_task(video_service.process_video_session, session_id)` in `backend/app/api/routes/video.py:110`. It executes in-process on a worker thread in the same Uvicorn instance.
- **Crash Behavior:**
  - *Pipeline-level errors:* Handled via `try...except Exception as e` inside `process_video_session()`; updates database status to `'failed'` and writes error details.
  - *Process-level crashes / Server restarts:* If Uvicorn crashes, runs out of memory, or is restarted while sessions are processing, those sessions remain permanently frozen with `status = "processing"`.
  - *Remediation Plan:* Implement a startup recovery sweep that queries `SELECT session_id FROM sessions WHERE status = 'processing'` and marks them as `'failed'` (with note: "Worker interrupted during restart") to unblock the UI.

---

## Conclusion & Gate Check

Phase 0 Audit is complete with empirical evidence across all 7 points. **No code or file edits have been made.**

Awaiting user confirmation before proceeding to **PHASE 1: REMOVE OR HIDE WHAT IS FAKE OR UNPROVEN**.
