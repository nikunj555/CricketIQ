# CricketIQ — System Architecture & Data Flow

## 1. High-Level Architecture

CricketIQ is structured as a decoupled full-stack sports analytics application comprising two complementary modes:
- **Mode A: Live Batting Coach (Real-Time)** — Connects to device camera via `getUserMedia`, runs lightweight pose tracking & state machine, detecting shots in real time and providing concise feedback cards immediately after each shot.
- **Mode B: Detailed Video Analysis (XAI)** — Comprehensive workspace providing skeleton video overlays, Recharts time-series, 7-phase timeline breakdown, Dynamic Time Warping (DTW) reference comparison, and longitudinal progress tracking.

```mermaid
flowchart TD
    User["User / Athlete (Web Browser)"] -->|"Live Camera Feed (getUserMedia)"| ModeA["Mode A: Live Batting Coach (Port 5173)"]
    User -->|"Uploads video (MP4/MOV)"| ModeB["Mode B: Detailed Analysis Workspace"]
    
    ModeA -->|"Frames / WebSockets"| LiveAPI["Live Coach Router (/api/live)"]
    LiveAPI --> LiveService["LiveCoachService (State Machine & Burst Detector)"]
    LiveService --> PoseService["PoseService (MediaPipe Pose Landmarker)"]
    LiveService --> GeometryService["GeometryService (Vector Calculations & Scale Normalization)"]
    LiveService --> PhaseService["PhaseService (PyTorch BiLSTM Classifier)"]
    LiveService --> FeedbackService["FeedbackService (Post-Shot Evidence Drills)"]
    
    ModeB --> VideoService["VideoService (Frame Decoding & Sampling)"]
    VideoService --> PoseService
    VideoService --> GeometryService
    GeometryService --> PhaseService
    PhaseService --> DTWService["DTWService (Dynamic Time Warping Alignment)"]
    DTWService --> FeedbackService
    
    FeedbackService --> SessionRepo["SessionRepository (SQLite 3 Storage)"]
    SessionRepo -->|"Attempt Telemetry & Video Data"| Backend["FastAPI Backend (Port 8000)"]
    Backend -->|"Live Sync & Visualizations"| Frontend["React + TypeScript UI"]
```

---

## 2. Component Responsibilities

| Component | Technology | Primary Responsibility |
| :--- | :--- | :--- |
| **Frontend UI** | React 18, Vite, TypeScript, Tailwind CSS, Recharts, Lucide | User interaction, video playback with synchronized frame scrubber, interactive kinematic curves, 7x7 confusion matrix visualization, progress tracking |
| **API Layer** | FastAPI, Pydantic v2, Uvicorn | Request validation, asynchronous background processing, video streaming, session persistence endpoints |
| **Pose Estimator** | Google MediaPipe Pose Landmarker Full | Monocular image extraction of 33 human joint coordinates $(x, y, z)$ and visibility confidence |
| **Kinematics Engine** | NumPy, Vector Geometry | Scale-normalized calculations: Lead/rear knee flexion, torso inclination from vertical, head stability, normalized stance width |
| **Temporal Phase Classifier** | PyTorch BiLSTM (2-layer, hidden 64, bidirectional) | Temporal sequence classification into 7 distinct batting action phases (Stance, Backswing, Stride, Downswing, Impact, Follow-through, Recovery) |
| **Sequence Comparator** | Pure NumPy Vectorized DTW | Dynamic Time Warping alignment of multivariate temporal trajectories between player attempts and MCC benchmark standards |
| **Coaching Feedback Engine** | Rule-Based XAI Engine | Evaluates observed metrics against coaching tolerance bands and generates structured, evidence-grounded drill suggestions with technical limitations |
| **Data Persistence** | SQLite | Session metadata, summary metrics, phase boundaries, and frame-level time series |

---

## 3. Asynchronous Video Processing Flow

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Frontend
    participant API as FastAPI Router
    participant Repo as SQLite Database
    participant Worker as Background VideoService
    participant MediaPipe as MediaPipe Landmarker
    participant BiLSTM as PyTorch BiLSTM

    User->>Frontend: Selects video and shot type ("Cover Drive")
    Frontend->>API: POST /api/video/upload (Multipart)
    API->>Repo: Creates session with status='queued'
    API-->>Frontend: Returns session_id ("demo_cd1")
    API->>Worker: Dispatches background processing task

    loop Status Polling
        Frontend->>API: GET /api/video/status/{session_id}
        API-->>Frontend: progress: 15% -> 50% -> 90%
    end

    Worker->>Worker: Decodes video frames (OpenCV)
    Worker->>MediaPipe: Extracts 33 landmarks per frame
    Worker->>Worker: Calculates joint angles & normalized kinematics
    Worker->>BiLSTM: Inferences temporal feature matrix (T x 14)
    BiLSTM-->>Worker: Frame-level phase predictions & confidences
    Worker->>Worker: Renders skeleton overlay & writes annotated MP4
    Worker->>Repo: Saves final analysis JSON & sets status='completed'

    Frontend->>API: GET /api/analysis/{session_id}
    API-->>Frontend: Full AnalysisResult payload
    Frontend->>User: Displays interactive workspace with synchronized video & charts
```
