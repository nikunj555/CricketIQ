import os, sys, glob, json
sys.path.insert(0, os.path.abspath("."))

from backend.app.services.shot_classifier_service import shot_classifier_service
from backend.app.services.geometry_service import geometry_service

files = sorted(glob.glob("storage/uploads/*groundtruth.json"))
print("=== GROUND TRUTH FIXTURE EVALUATION ===")
for f in files:
    base = os.path.basename(f).replace("_groundtruth.json", "")
    with open(f, "r") as fp:
        gt_data = json.load(fp)
    frame_metrics = []
    for fr in gt_data:
        m = geometry_service.extract_frame_metrics(fr["landmarks"])
        m["landmarks"] = fr["landmarks"]
        frame_metrics.append(m)
    frame_metrics = geometry_service.enrich_time_series_with_derivatives(frame_metrics, fps=30.0)
    res = shot_classifier_service.classify_sequence(frame_metrics)
    pred = res["predicted_shot"]
    conf = res["confidence"]
    fam = res["family"]
    uns = res["is_uncertain"]
    print(f"{base:<30} -> {pred:<20} (Conf: {int(conf*100)}%, Fam: {fam}, Unsure: {uns})")
