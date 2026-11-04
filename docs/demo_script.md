# CricketIQ — 5-Minute Live Academic Demonstration Script

Use this battle-tested script during your university evaluation or project viva defense.

---

## Preparation (30 Seconds Before Demo)
1. Ensure both services are running:
   - Backend: `run_backend.bat` (http://127.0.0.1:8000)
   - Frontend: `run_frontend.bat` (http://localhost:5173)
2. Open your web browser to `http://localhost:5173`.
3. The application opens directly into **Mode A: Live AI Batting Coach**.
4. Verify the status pill in the top navbar says **"FastAPI 1.0 Online"** in green.

---

## Minute 1: The Vision & Live Batting Coach (Mode A)
* **What to Show:** Stay on the landing screen: **Mode A: Live Batting Coach** (`http://localhost:5173`).
* **What to Say:**
  > "Good morning examiners. Today I am demonstrating **CricketIQ**, an explainable AI system for cricket batting technique assessment.
  > Most computer vision fitness tools either require uploading pre-recorded video for batch processing or only draw simple stick figures without coaching intelligence.
  > CricketIQ solves this by providing two complementary modes:
  > **Mode A: Live AI Batting Coach** for immediate on-field practice, and
  > **Mode B: Detailed Video Analysis** for biomechanical research and video review.
  > Here in Mode A, a player sets up their laptop or phone camera by the batting crease. Notice our stance positioning guide and live body alignment check. The system runs an automated 5-state finite state machine that detects when the batsman takes their stance, begins their stroke through kinetic velocity burst detection, captures the shot, and returns instant feedback in under 40 milliseconds."
* **Key Visuals to Highlight:**
  * Clean sports-analytics dark UI with camera viewfinder and stance guide silhouette.
  * Live status pill: `Ready for Shot` / `Waiting for Player`.
  * Camera toggle controls and target shot selector (Cover Drive, Straight Drive, Pull Shot, Forward Defense).

---

## Minute 2: Instant Feedback Card & Practice Loop
* **What to Show:** Click the **"Simulate / Record Shot"** button (or press the **Spacebar** on your keyboard).
* **What to Say:**
  > "Watch what happens when the shot finishes: the system transitions to 'Shot Completed' and immediately renders an **Instant Post-Shot Feedback Card**.
  > Rather than overwhelming an athlete with complex graphs mid-practice, the feedback card delivers five critical elements:
  > 1. Primary mechanical observation: here, 'Lead knee flexion is within ideal MCC range at impact'.
  > 2. Measured evidence versus textbook benchmark (126° vs 120°–130°).
  > 3. Why it matters mechanically for power transfer and balance.
  > 4. An actionable practice drill cue to perform on the very next ball.
  > 5. An attempt delta comparing this stroke directly against their previous shot—showing improvement in knee bend and torso stability.
  > The player can immediately press 'Practice Next Shot' to continue their session, or click 'Review Detailed Analysis' to transition into our deep-dive analysis suite."
* **Key Actions:**
  * Highlight the green/amber evidence badges and comparison delta ($\Delta$ knee, $\Delta$ lean).
  * Click **"Review Detailed Analysis"** to transition to Mode B.

---

## Minute 3: Detailed Video Analysis & Kinematic Tracking (Mode B)
* **What to Show:** You are now in the **Video Workspace** (`Workspace` tab) showing session `demo_cd1`.
* **What to Say:**
  > "When the player or coach wants to examine the mechanics in depth, Mode B provides a complete biomechanical workstation.
  > On the video player, our computer vision pipeline renders the 33-point MediaPipe skeleton overlay directly onto the athlete.
  > As I drag the frame scrubber, notice that the video frame, timestamp, joint angles, and phase timeline update in exact synchronization.
  > Under the Biomechanics tab, we normalize all spatial distances by the batsman's torso length (distance between shoulder midpoint and hip midpoint). This provides camera zoom and distance invariance."
* **Key Actions:**
  * Play at **0.5x** speed, then drag the scrubber across frames.
  * Point out the synchronized cursor moving along the **Phase Timeline** below the video.

---

## Minute 4: Dynamic Time Warping (DTW) & 7-Phase BiLSTM Recognition
* **What to Show:** Click on the **Phases** tab, then the **Reference Compare** tab.
* **What to Say:**
  > "Under the Phases tab, our temporal deep learning model—a 2-layer Bidirectional LSTM—segments the entire stroke cycle into 7 distinct action phases: Stance, Backswing, Stride, Downswing, Impact Window, Follow-through, and Recovery. Clicking any phase immediately jumps the keyframe inspector to that critical moment.
  > Moving to Reference Compare, different batsmen play shots at different speeds, making linear frame comparisons invalid. We implemented pure Dynamic Time Warping in 5-dimensional kinematic space. The algorithm warps the player's time series to align with textbook MCC reference curves, producing a 91.2% trajectory similarity score.
  > We explicitly explain to the user that this measures kinematic trajectory alignment, not subjective cricketing talent."

---

## Minute 5: Explainable Coaching, Empirical Evaluation & Viva Defense
* **What to Show:** Click on the **Model Evaluation** tab.
* **What to Say:**
  > "Finally, let us look at our empirical model evaluation. In academia, real results on held-out test data are paramount.
  > We benchmarked our PyTorch BiLSTM against a Multinomial Logistic Regression baseline across 140 sequence trials and 8,277 frames.
  > On the held-out test set of 1,223 frames, our BiLSTM achieved **98.69% accuracy** and **0.9837 macro F1**, an absolute empirical improvement of **+9.07%** over the baseline.
  > The 7x7 confusion matrix below shows crisp diagonal classification with zero data leakage across splits.
  > We also include an explicit Academic Limitations section explaining that monocular 2D projection cannot measure out-of-plane torque, ensuring our system remains scientifically honest.
  > Thank you, examiners. I welcome your questions."

---

## 4 Likely Examiner Questions & Rapid Answers
1. **"How does the real-time Live Coach detect when a shot occurs?"**
   * *Answer:* It uses a 5-state finite state machine with kinetic burst detection. When the player enters the frame and assumes a stance, landmark variance drops below a stability threshold (`ready_for_shot`). A sudden kinetic energy burst from wrists and lead knee triggers `shot_in_progress`. When limb velocities settle back below the threshold, the stroke is marked completed and immediately evaluated. Manual spacebar trigger is also provided.
2. **"Why did you choose MediaPipe Pose over YOLOv8-pose?"**
   * *Answer:* MediaPipe Pose Landmarker Full tracks 33 topological keypoints (including heel, ankle, toe, and head landmarks) directly on standard CPU at 30+ FPS, enabling real-time browser camera analysis without requiring expensive cloud GPUs or dedicated external hardware.
3. **"Can this system detect the exact millisecond of bat-ball contact?"**
   * *Answer:* At 30 FPS, an impact window lasts only 2 to 4 frames. Rather than claiming microsecond contact sensor physics, we transparently detect the kinematic impact *window* using downswing deceleration and torso forward apex.
4. **"How does the model handle left-handed batsmen?"**
   * *Answer:* In both live practice and video analysis, the handedness flag dynamically re-indexes the anatomical landmarks: for a left-hander, the right leg becomes the lead leg and the left arm becomes the rear arm.
