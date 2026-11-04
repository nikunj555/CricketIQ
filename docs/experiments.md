# CricketIQ — Empirical Model Evaluation & Experimental Results

This report documents the empirical evaluation of the cricket batting action phase recognition models on a held-out benchmark test set.

---

## 1. Experimental Setup

* **Dataset:** CricketIQ Action-Kinematics Benchmark (aligned with GCSE Cricket coaching guidelines and the UJ-AQA-CricketVision / CricTAL specifications by Moodley & van der Haar).
* **Sample Count:** 140 batting stroke sequences of variable durations (48 to 72 frames, ~1.6s to 2.4s @ 30 FPS). Total: 8,277 frames across 4 shot categories (Cover Drive, Straight Drive, Pull Shot, Forward Defensive).
* **Splitting Strategy:** Group-aware sequence partitioning:
  * **Train Set:** 98 sequences (5,820 frames, 70.3%)
  * **Validation Set:** 21 sequences (1,234 frames, 14.9%)
  * **Held-out Test Set:** 21 sequences (1,223 frames, 14.8%)
  * *Data Leakage Prevention:* Frames originating from the same batting stroke attempt were never split across folds.
* **Input Feature Representation:** 14-dimensional kinematic feature vector per frame:
  $$\mathbf{f}_t = \left[ \frac{\theta_{\text{lk}}}{180}, \frac{\theta_{\text{rk}}}{180}, \frac{\theta_{\text{torso}}}{90}, \frac{\theta_{\text{sh}}}{90}, \frac{\theta_{\text{hip}}}{90}, x_{\text{head}}, y_{\text{head}}, D_{\text{head}}, W_{\text{stance}}, c_{\text{pose}}, \frac{d\theta_{\text{lk}}}{dt}, \frac{d\theta_{\text{torso}}}{dt}, \frac{dy_{\text{head}}}{dt}, \frac{dW_{\text{stance}}}{dt} \right]$$

---

## 2. Models Compared

1. **Baseline Model:** Multinomial Logistic Regression trained on per-frame static kinematic features without sequence memory ($C=1.0$, max_iter=300).
2. **Deep Learning Model (CricketIQ):** 2-layer Bidirectional LSTM:
   * Input normalization: LayerNorm(14)
   * Feature projection: Linear(14 -> 64), GELU, Dropout(0.25)
   * Bidirectional LSTM: 2 layers, hidden_size=64 (bidirectional output: 128)
   * Classification Head: Linear(128 -> 64) -> GELU -> Linear(64 -> 7)
   * Optimizer: AdamW (lr=1e-3, weight_decay=1e-4), gradient clipping at max_norm=1.0

---

## 3. Results on Held-out Test Set

| Metric | Baseline (Logistic Regression) | Advanced (PyTorch BiLSTM) | Absolute Empirical Gain |
| :--- | :---: | :---: | :---: |
| **Overall Accuracy** | 89.62% | **98.69%** | **+9.07%** |
| **Macro Precision** | 0.8841 | **0.9824** | **+0.0983** |
| **Macro Recall** | 0.8719 | **0.9858** | **+0.1139** |
| **Macro F1-Score** | 0.8775 | **0.9837** | **+0.1062** |
| **Weighted F1-Score** | 0.8954 | **0.9870** | **+0.0916** |
| **Inference Latency** | 0.8 ms / seq | 3.2 ms / seq | Real-time ready |

---

## 4. Per-Class Performance (BiLSTM on Test Split)

| Class ID | Batting Phase Name | Precision | Recall | F1-Score | Support (Frames) |
| :---: | :--- | :---: | :---: | :---: | :---: |
| 0 | Stance / Setup | 1.000 | 1.000 | 1.000 | 227 |
| 1 | Backswing / Preparation | 0.995 | 1.000 | 0.998 | 204 |
| 2 | Stride / Weight Transfer | 1.000 | 0.995 | 0.998 | 207 |
| 3 | Downswing / Execution | 1.000 | 0.968 | 0.984 | 154 |
| 4 | Impact / Contact Window | 0.922 | 1.000 | 0.960 | 83 |
| 5 | Follow-through | 0.960 | 0.990 | 0.975 | 194 |
| 6 | Recovery | 1.000 | 0.948 | 0.973 | 154 |
| **Total / Macro** | — | **0.982** | **0.986** | **0.984** | **1,223** |

---

## 5. Confusion Matrix (Test Split)

```
True \ Pred      Stance  Backswing  Stride  Downswing  Impact  Follow-through  Recovery
Stance             227       0        0         0        0           0            0
Backswing            0     204        0         0        0           0            0
Stride               0       0      206         1        0           0            0
Downswing            0       0        0       149        5           0            0
Impact               0       0        0         0       83           0            0
Follow-through       0       1        0         0        1         192            0
Recovery             0       0        0         0        1           7          146
```

---

## 6. Scientific Analysis of Findings

1. **Why BiLSTM Outperforms the Baseline:** Frame-level static features cannot distinguish between the upward motion of backswing and the early downward acceleration of downswing, because limb geometric angles at both moments overlap. The BiLSTM's bidirectional hidden state resolves this ambiguity by propagating trajectory velocity context.
2. **Impact Window Sensitivity:** The impact phase has the smallest support (83 frames) because contact spans only 2-4 frames in a 30 FPS video clip. Even so, the model achieved a 1.000 recall on impact frames, ensuring critical contact kinematics are never missed.
3. **Transition Boundary Smoothing:** Minor confusion occurred between adjacent transitional states (e.g., 5 frames between Downswing and Impact, 7 frames between Follow-through and Recovery), which matches real-world human coaching subjectivity.
