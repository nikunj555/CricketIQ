import cv2
import numpy as np
import os
import glob
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS_RAW = os.path.join(BASE_DIR, 'storage', 'annotated', 'shots_raw')
OUT_DIR = os.path.join(BASE_DIR, 'storage', 'annotated')
REF_JSON = os.path.join(BASE_DIR, 'frontend', 'src', 'data', 'reference_shots.json')

with open(REF_JSON, 'r', encoding='utf-8') as f:
    ref_data = json.load(f)

shot_names = list(ref_data.keys())

def create_grid(phase_suffix, output_name, title_text):
    cells = []
    cell_w, cell_h = 320, 200

    for name in shot_names:
        slug = name.lower().replace(' ', '-').replace('_', '-')
        # Look for matching file
        path = os.path.join(SHOTS_RAW, f"{slug}_{phase_suffix}.png")
        if not os.path.exists(path):
            # Try alternate matching
            candidates = glob.glob(os.path.join(SHOTS_RAW, f"*{slug}*{phase_suffix}.png"))
            if candidates:
                path = candidates[0]

        if os.path.exists(path):
            img = cv2.imread(path)
            img = cv2.resize(img, (cell_w, cell_h))
        else:
            img = np.zeros((cell_h, cell_w, 3), dtype=np.uint8)
            cv2.putText(img, "MISSING", (cell_w//4, cell_h//2), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)

        # Overlay shot name banner
        banner = img.copy()
        cv2.rectangle(banner, (0, 0), (cell_w, 28), (15, 17, 19), -1)
        cv2.addWeighted(banner, 0.85, img, 0.15, 0, img)
        cv2.putText(img, name, (8, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (127, 234, 53), 1, cv2.LINE_AA)

        cells.append(img)

    # 5 rows x 5 cols
    rows = []
    for r in range(5):
        row_imgs = cells[r*5 : (r+1)*5]
        row_concat = np.hstack(row_imgs)
        rows.append(row_concat)

    grid = np.vstack(rows)

    # Add master title header
    header_h = 60
    header = np.full((header_h, grid.shape[1], 3), 15, dtype=np.uint8)
    cv2.putText(header, f"CricketIQ 25-Shot Kinematics Contact Sheet: {title_text}", (20, 38),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(header, "Unique Authored Biomechanics · 2-Bone Inverse Kinematics · Ground-Clamped Blade", (grid.shape[1] - 680, 38),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (127, 234, 53), 1, cv2.LINE_AA)

    final_image = np.vstack([header, grid])
    out_path = os.path.join(OUT_DIR, output_name)
    cv2.imwrite(out_path, final_image)
    print(f"Generated contact sheet: {out_path} ({final_image.shape[1]}x{final_image.shape[0]})")

create_grid('impact', 'contact_sheet_impact.jpg', 'Phase 5 Impact Window')
create_grid('finish', 'contact_sheet_follow_through.jpg', 'Phase 6 Follow-Through')
print("Contact sheets generated successfully!")
