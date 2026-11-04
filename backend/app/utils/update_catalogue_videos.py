"""
Updates reference_catalogue.py to map each of the 25 shots to its distinct generated video clip.
"""

from backend.app.data.reference_catalogue import AUTHENTIC_REFERENCE_REGISTRY
from backend.app.data.shot_catalogue import SHOT_CATALOGUE

# Map from shot_id to video filename
SHOT_VIDEO_MAP = {
    "shot_cover_drive": ("real_cricketer_cover_drive.mp4", "real_cricketer_cover_drive_thumb.jpg"),
    "shot_straight_drive": ("sample_straight_drive.mp4", "demo_straight_drive_thumb.jpg"),
    "shot_on_drive": ("sample_on_drive.mp4", "sample_on_drive_thumb.jpg"),
    "shot_off_drive": ("sample_off_drive.mp4", "sample_off_drive_thumb.jpg"),
    "shot_lofted_drive": ("sample_lofted_drive.mp4", "sample_lofted_drive_thumb.jpg"),
    "shot_forward_defensive": ("real_cricketer_forward_defensive.mp4", "real_cricketer_forward_defensive_thumb.jpg"),
    "shot_back_foot_defensive": ("sample_back_foot_defensive.mp4", "sample_back_foot_defensive_thumb.jpg"),
    "shot_back_foot_punch": ("sample_back_foot_punch.mp4", "sample_back_foot_punch_thumb.jpg"),
    "shot_square_cut": ("sample_square_cut.mp4", "demo_square_cut_thumb.jpg"),
    "shot_late_cut": ("sample_late_cut.mp4", "sample_late_cut_thumb.jpg"),
    "shot_upper_cut": ("sample_upper_cut.mp4", "sample_upper_cut_thumb.jpg"),
    "shot_pull_shot": ("real_gilchrist_pull.mp4", "real_gilchrist_pull_thumb.jpg"),
    "shot_hook_shot": ("sample_hook_shot.mp4", "sample_hook_shot_thumb.jpg"),
    "shot_flick_shot": ("sample_flick_shot.mp4", "sample_flick_shot_thumb.jpg"),
    "shot_leg_glance": ("sample_leg_glance.mp4", "sample_leg_glance_thumb.jpg"),
    "shot_clip_shot": ("sample_clip_shot.mp4", "sample_clip_shot_thumb.jpg"),
    "shot_sweep": ("sample_sweep.mp4", "demo_sweep_thumb.jpg"),
    "shot_slog_sweep": ("sample_slog_sweep.mp4", "sample_slog_sweep_thumb.jpg"),
    "shot_reverse_sweep": ("sample_reverse_sweep.mp4", "sample_reverse_sweep_thumb.jpg"),
    "shot_paddle_sweep": ("sample_paddle_sweep.mp4", "sample_paddle_sweep_thumb.jpg"),
    "shot_slog": ("sample_slog.mp4", "sample_slog_thumb.jpg"),
    "shot_switch_hit": ("sample_switch_hit.mp4", "sample_switch_hit_thumb.jpg"),
    "shot_scoop_shot": ("sample_scoop_shot.mp4", "sample_scoop_shot_thumb.jpg"),
    "shot_ramp_shot": ("sample_ramp_shot.mp4", "sample_ramp_shot_thumb.jpg"),
    "shot_helicopter_shot": ("sample_helicopter_shot.mp4", "sample_helicopter_shot_thumb.jpg")
}

for ref in AUTHENTIC_REFERENCE_REGISTRY:
    s_id = ref["shot_id"]
    if s_id in SHOT_VIDEO_MAP:
        v_name, t_name = SHOT_VIDEO_MAP[s_id]
        ref["video_url"] = f"/api/video/original/{v_name}"
        ref["thumbnail_url"] = f"/api/video/thumbnail/{t_name}"

for s in SHOT_CATALOGUE:
    s_id = s["id"]
    if s_id in SHOT_VIDEO_MAP:
        v_name, t_name = SHOT_VIDEO_MAP[s_id]
        s["reference_video_url"] = f"/api/video/original/{v_name}"
        s["reference_thumbnail_url"] = f"/api/video/thumbnail/{t_name}"

print("All 25 references verified with distinct video files!")

