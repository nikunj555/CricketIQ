# CricketIQ — Biomechanical & Machine Learning Methodology

This document details the mathematical formulations, coordinate system conventions, normalization techniques, and algorithmic foundations implemented in CricketIQ.

---

## 1. Coordinate Systems & Image Plane Conventions

* **Image Dimensions:** Normalized coordinates $x \in [0.0, 1.0]$ (left to right) and $y \in [0.0, 1.0]$ (top to bottom).
* **Vertical Reference Axis:** $\vec{V}_{\text{up}} = [0.0, -1.0]$, representing the direction pointing upward toward the sky.
* **Horizontal Reference Axis:** $\vec{H}_{\text{right}} = [1.0, 0.0]$, representing the horizontal plane parallel to the pitch surface.

---

## 2. Joint Angle Vector Formulations

### 2.1 Lead Knee Interior Flexion Angle ($\theta_{\text{knee}}$)
Let $\vec{P}_{\text{hip}}$, $\vec{P}_{\text{knee}}$, and $\vec{P}_{\text{ankle}}$ denote the 2D coordinates of the hip, knee, and ankle joints respectively for the lead leg (left leg for right-handed batter, right leg for left-handed batter):

$$\vec{u} = \vec{P}_{\text{hip}} - \vec{P}_{\text{knee}}$$

$$\vec{v} = \vec{P}_{\text{ankle}} - \vec{P}_{\text{knee}}$$

The interior joint angle $\theta_{\text{knee}} \in [0^\circ, 180^\circ]$ is calculated via the Euclidean dot product:

$$\cos \theta_{\text{knee}} = \frac{\vec{u} \cdot \vec{v}}{\|\vec{u}\|_2 \|\vec{v}\|_2}$$

$$\theta_{\text{knee}} = \arccos\left(\text{clip}\left(\cos \theta_{\text{knee}}, -1.0, 1.0\right)\right) \times \frac{180}{\pi}$$

* A fully extended straight leg yields $\theta_{\text{knee}} \approx 180^\circ$.
* A textbook front-foot cover drive at the contact window typically produces $\theta_{\text{knee}} \in [115^\circ, 135^\circ]$.

### 2.2 Torso Forward Inclination from Vertical ($\theta_{\text{torso}}$)
Let $\vec{M}_{\text{shoulder}} = \frac{\vec{P}_{\text{left\_shoulder}} + \vec{P}_{\text{right\_shoulder}}}{2}$ and $\vec{M}_{\text{hip}} = \frac{\vec{P}_{\text{left\_hip}} + \vec{P}_{\text{right\_hip}}}{2}$.

The spine direction vector is:

$$\vec{T} = \vec{M}_{\text{shoulder}} - \vec{M}_{\text{hip}} = [\Delta x_T, \Delta y_T]$$

The inclination angle from vertical is computed with respect to $\vec{V}_{\text{up}} = [0, -1]$:

$$\cos \theta_{\text{torso}} = \frac{-\Delta y_T}{\|\vec{T}\|_2}$$

$$\theta_{\text{torso}} = \arccos\left(\text{clip}\left(\cos \theta_{\text{torso}}, -1.0, 1.0\right)\right) \times \frac{180}{\pi}$$

* $\theta_{\text{torso}} = 0^\circ$ corresponds to a perfectly vertical spine.
* Front-foot driving technique targets $\theta_{\text{torso}} \in [20^\circ, 32^\circ]$.

### 2.3 Elbow Interior Flexion Angle ($\theta_{\text{elbow}}$)
For the lead or rear arm (mapped dynamically by batter handedness):
Let $\vec{P}_{\text{shoulder}}$, $\vec{P}_{\text{elbow}}$, and $\vec{P}_{\text{wrist}}$ denote the joint positions:

$$\vec{u}_{\text{upper}} = \vec{P}_{\text{shoulder}} - \vec{P}_{\text{elbow}}$$
$$\vec{v}_{\text{forearm}} = \vec{P}_{\text{wrist}} - \vec{P}_{\text{elbow}}$$

$$\theta_{\text{elbow}} = \arccos\left(\text{clip}\left(\frac{\vec{u}_{\text{upper}} \cdot \vec{v}_{\text{forearm}}}{\|\vec{u}_{\text{upper}}\|_2 \|\vec{v}_{\text{forearm}}\|_2}, -1.0, 1.0\right)\right) \times \frac{180}{\pi}$$

* A high lead elbow at the point of impact prevents spooning or slicing the ball, with MCC target ranges between $135^\circ$ and $160^\circ$.
* $\theta_{\text{elbow}} < 120^\circ$ triggers the "Collapsed Lead Elbow" observation.

### 2.4 Arm Extension Ratio ($R_{\text{arm}}$)
Quantifies whether the player's arms reach through the line of the delivery:

$$R_{\text{arm}} = \frac{\|\vec{P}_{\text{shoulder}} - \vec{P}_{\text{wrist}}\|_2}{\|\vec{P}_{\text{shoulder}} - \vec{P}_{\text{elbow}}\|_2 + \|\vec{P}_{\text{elbow}} - \vec{P}_{\text{wrist}}\|_2}$$

* $R_{\text{arm}} = 1.0$ indicates a completely straight arm.
* Standard drive extension targets $R_{\text{arm}} \in [0.85, 0.96]$.

### 2.5 Head-Over-Lead-Knee Normalization ($\Delta_{\text{head-knee}}$)
Horizontal alignment between the batter's head and the front knee apex:

$$\Delta_{\text{head-knee}} = \frac{x_{\text{nose}} - x_{\text{lead\_knee}}}{L_{\text{torso}}}$$

* Negative values indicate the head is trailing behind the lead knee (falling away).
* Values near zero ($|\Delta_{\text{head-knee}}| \le 0.15$) demonstrate proper body weight committed over the ball at contact.

### 2.6 Dynamic Weight Distribution Proxy ($W_{\text{front}}$)
Coronal projection of the center-of-mass (represented by the mid-hip landmark) across the base of support:

$$W_{\text{front}} = \text{clip}\left(\frac{x_{\text{mid\_hip}} - x_{\text{rear\_ankle}}}{x_{\text{lead\_ankle}} - x_{\text{rear\_ankle}} + \epsilon}, 0.0, 1.0\right)$$

* $W_{\text{front}} \in [0.70, 0.85]$ indicates positive front-foot weight commitment during forward drives.
* $W_{\text{front}} < 0.45$ during forward execution indicates the player is trapped on the back foot.

---

## 3. Anthropometric Body-Scale Normalization

Camera distances vary across user recordings. To ensure cross-player invariance:
1. **Torso Reference Length ($L_{\text{torso}}$):**
   $$L_{\text{torso}} = \|\vec{M}_{\text{shoulder}} - \vec{M}_{\text{hip}}\|_2$$
2. **Normalized Stance Width ($W_{\text{stance}}$):**
   $$W_{\text{stance}} = \frac{\|\vec{P}_{\text{lead\_ankle}} - \vec{P}_{\text{rear\_ankle}}\|_2}{L_{\text{torso}}}$$
3. **Normalized Head Displacement ($D_{\text{head}}$):**
   $$D_{\text{head}}(t) = \frac{\|\vec{P}_{\text{nose}}(t) - \vec{M}_{\text{hip}}(t)\|_2}{L_{\text{torso}}}$$
   The **Head Stability Index** is the temporal standard deviation across the downswing and impact window:
   $$\text{HSI} = \sigma\left(\{D_{\text{head}}(t)\}_{t \in \text{Execution}}\right)$$

---

## 4. Dynamic Time Warping (DTW) Sequence Alignment

Let $\mathbf{X} = [\mathbf{x}_1, \dots, \mathbf{x}_N] \in \mathbb{R}^{N \times 5}$ and $\mathbf{Y} = [\mathbf{y}_1, \dots, \mathbf{y}_M] \in \mathbb{R}^{M \times 5}$ be the normalized feature sequences of the query attempt and benchmark reference respectively, where each feature vector is:

$$\mathbf{x}_t = \left[ \frac{\theta_{\text{lead\_knee}}}{180}, \frac{\theta_{\text{rear\_knee}}}{180}, \frac{\theta_{\text{torso}}}{90}, \frac{W_{\text{stance}}}{3}, y_{\text{head}} \right]$$

### 4.1 Cost Matrix Recurrence
The cumulative distance matrix $\mathbf{D} \in \mathbb{R}^{(N+1) \times (M+1)}$ is computed via dynamic programming:

$$\mathbf{D}(0, 0) = 0, \quad \mathbf{D}(i, 0) = \infty, \quad \mathbf{D}(0, j) = \infty$$

$$\mathbf{D}(i, j) = \|\mathbf{x}_i - \mathbf{y}_j\|_2 + \min\begin{cases} \mathbf{D}(i-1, j) & (\text{insertion}) \\ \mathbf{D}(i, j-1) & (\text{deletion}) \\ \mathbf{D}(i-1, j-1) & (\text{match}) \end{cases}$$

### 4.2 Kinematic Trajectory Similarity Score
Following backtracking of the optimal warping path $W = \{(i_k, j_k)\}_{k=1}^K$, the normalized path distance is:

$$\bar{d} = \frac{\mathbf{D}(N, M)}{K}$$

The kinematic trajectory similarity $S \in [0, 100]$ is scaled via exponential decay with $\tau = 0.28$:

$$S = 100 \times \exp\left(-\frac{\bar{d}}{\tau}\right)$$

*Note:* $S$ quantifies kinematic trajectory alignment, not overall subjective cricketing talent or tactical effectiveness.

---

## 5. Dedicated Hand & Finger Tracking (21-Point Landmark Model)

CricketIQ integrates Google MediaPipe's Hand Landmarker (`hand_landmarker.task`) to analyze grip biomechanics:
* **Grip Closure Score ($G_{\text{closure}}$):** Computed by evaluating the Euclidean distance between the fingertip landmarks (Index: 8, Middle: 12, Ring: 16, Pinky: 20) and the wrist anchor (0), normalized by palm scale (distance between landmarks 0 and 9):
  $$G_{\text{closure}} = 1.0 - \text{clip}\left(\frac{\frac{1}{4}\sum_{i \in \{8,12,16,20\}} \|\vec{P}_i - \vec{P}_0\|_2}{2.2 \times \|\vec{P}_9 - \vec{P}_0\|_2}, 0.0, 1.0\right)$$
  * $G_{\text{closure}} > 0.65$: Indicates a firm, enclosed batting grip around the handle.
  * $G_{\text{closure}} < 0.40$: Indicates loose or open fingers.
* **Two-Hand Separation:** Evaluates wrist landmark distance relative to torso length ($D_{\text{wrists}} = \|\vec{P}_{\text{lead\_wrist}} - \vec{P}_{\text{rear\_wrist}}\|_2 / L_{\text{torso}}$). A separation $> 0.35$ triggers the split-grip technique observation.
* **Occlusion & Blur Fallbacks:** When batting gloves or high-speed downswing velocities cause low landmark resolution (< 30x30 px), the service logs hand presence as untracked rather than fabricating coordinates.

---

## 6. Modular Bat & Ball Tracking Pipeline

* **Region of Interest (ROI) Anchor:** Bat blade detection is anchored at the batter's wrist landmarks ($\vec{P}_{\text{wrist}}$) extending downward and outward into the expected swing arc, reducing false positives from background clutter and boundary fences.
* **Hough Line Blade Extraction:** Canny edge maps are processed with the Probabilistic Hough Line Transform (`HoughLinesP`). Lines are filtered by minimum length (> 40px) and angular proximity to the wrist.
* **Bat Angle from Vertical ($\theta_{\text{bat}}$):**
  $$\theta_{\text{bat}} = \arctan2(|\Delta x|, |\Delta y|) \times \frac{180}{\pi}$$
  For vertical-bat drives (Cover Drive, Straight Drive), target impact alignment is $\theta_{\text{bat}} \le 25^\circ$. Cross-bat angles $> 45^\circ$ during a drive stroke trigger coaching alerts.
* **Ball Corridor Tracking:** Hough Circle Transform (`HoughCircles`) filters spherical objects along the incoming delivery corridor.
* **Explicit Untracked Telemetry:** If no reliable bat line or ball circle is verified above confidence thresholds, the system explicitly returns `bat_detected: false` and `ball_detected: false` rather than guessing.

---

## 7. Grounded Coaching Knowledge Base & MCC Tolerance Bands

| Biomechanical Metric | Target Shot | MCC Benchmark | Threshold Alert | Triggered Observation |
|---|---|---|---|---|
| Lead Knee Flexion | Cover Drive | $115^\circ - 135^\circ$ | $> 140^\circ$ | Insufficient Front Knee Bend (`obs_knee_01`) |
| Lead Elbow Flexion | Drives | $135^\circ - 160^\circ$ | $< 120^\circ$ | Collapsed Lead Elbow (`obs_elbow_01`) |
| Head Over Lead Knee | Drives | $|\Delta| \le 0.15$ | $\Delta < -0.20$ | Head Falling Away from Contact (`obs_head_knee_01`) |
| Bat Blade Angle | Straight / Cover Drive | $5^\circ - 25^\circ$ | $> 45^\circ$ | Cross-Bat Presentation (`obs_bat_01`) |
| Weight Transfer Proxy | Forward Drives | $70\% - 85\%$ | $< 50\%$ | Weight Trapped on Rear Foot (`obs_weight_01`) |
| Wrist Separation | All Shots | $\le 0.25$ | $> 0.35$ | Two-Hand Split Grip (`obs_grip_01`) |
| Head Stability Index | All Shots | $< 0.08$ | $> 0.12$ | Head Bobbing During Downswing (`obs_head_01`) |
| Torso Forward Lean | Drives | $20^\circ - 32^\circ$ | $< 15^\circ$ | Overly Upright Spine (`obs_torso_01`) |

