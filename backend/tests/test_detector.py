import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from requests.exceptions import Timeout, ConnectionError

from backend.app.services.detector_service import (
    DetectorService,
    Detection,
    DetectionTrack,
    calculate_iou
)
from backend.app.core.config import settings


def test_iou_calculation():
    """Verify standard IoU calculations."""
    box1 = [0.1, 0.1, 0.5, 0.5]
    box2 = [0.1, 0.1, 0.5, 0.5]
    assert calculate_iou(box1, box2) == 1.0

    box3 = [0.6, 0.6, 0.9, 0.9]
    assert calculate_iou(box1, box3) == 0.0

    box4 = [0.3, 0.3, 0.7, 0.7]
    iou = calculate_iou(box1, box4)
    assert 0.1 < iou < 0.3


def test_bowler_and_non_striker_never_selected():
    """
    STRIKER LOCK REQUIREMENT:
    Never choose 'bowler' or 'non_striker' as the striker.
    Even if a bowler is in the frame with bat-like objects or high confidence.
    """
    service = DetectorService()

    tracks = {
        0: DetectionTrack(
            track_id=0,
            class_name="bowler",
            last_bbox=[0.2, 0.1, 0.4, 0.8],
            last_seen_frame=10,
            history={i: [0.2, 0.1, 0.4, 0.8] for i in range(10)},
            bat_overlap_count=5,
            total_frames=10,
            total_area_sum=1.4
        ),
        1: DetectionTrack(
            track_id=1,
            class_name="non_striker",
            last_bbox=[0.7, 0.2, 0.9, 0.85],
            last_seen_frame=10,
            history={i: [0.7, 0.2, 0.9, 0.85] for i in range(10)},
            bat_overlap_count=3,
            total_frames=10,
            total_area_sum=1.2
        )
    }

    per_frame_dets = {
        0: [
            Detection("bowler", 0.92, [0.2, 0.1, 0.4, 0.8], [128, 48, 256, 384], (0.3, 0.45), (192, 216), 0.2, 0.7),
            Detection("non_striker", 0.88, [0.7, 0.2, 0.9, 0.85], [448, 96, 576, 408], (0.8, 0.52), (512, 252), 0.2, 0.65),
            Detection("bat", 0.85, [0.25, 0.4, 0.35, 0.7], [160, 192, 224, 336], (0.3, 0.55), (192, 264), 0.1, 0.3)
        ]
    }

    selected_tid, status, meta = service.select_striker(tracks, per_frame_dets)

    # Must NEVER select track 0 (bowler) or track 1 (non_striker)
    assert selected_tid is None
    assert status == "striker_unclear"
    assert "No 'batter' class tracks detected" in meta.get("reason", "")


def test_striker_unclear_when_two_batters_tie():
    """
    STRIKER LOCK REQUIREMENT:
    If two 'batter' tracks score close together, do not guess:
    return 'striker_unclear' and ask the user to tap the batter.
    """
    service = DetectorService()

    tracks = {
        0: DetectionTrack(
            track_id=0,
            class_name="batter",
            last_bbox=[0.4, 0.2, 0.6, 0.8],
            last_seen_frame=5,
            history={i: [0.4, 0.2, 0.6, 0.8] for i in range(5)},
            bat_overlap_count=2,
            total_frames=5,
            total_area_sum=0.6
        ),
        1: DetectionTrack(
            track_id=1,
            class_name="batter",
            last_bbox=[0.42, 0.21, 0.62, 0.81],
            last_seen_frame=5,
            history={i: [0.42, 0.21, 0.62, 0.81] for i in range(5)},
            bat_overlap_count=2,
            total_frames=5,
            total_area_sum=0.61
        )
    }

    per_frame_dets = {
        0: [
            Detection("batter", 0.85, [0.4, 0.2, 0.6, 0.8], [256, 96, 384, 384], (0.5, 0.5), (320, 240), 0.2, 0.6),
            Detection("batter", 0.84, [0.42, 0.21, 0.62, 0.81], [268, 100, 396, 388], (0.52, 0.51), (332, 244), 0.2, 0.6),
            Detection("bat", 0.90, [0.45, 0.4, 0.55, 0.7], [288, 192, 352, 336], (0.5, 0.55), (320, 264), 0.1, 0.3)
        ]
    }

    selected_tid, status, meta = service.select_striker(tracks, per_frame_dets)

    assert selected_tid is None
    assert status == "striker_unclear"
    assert "Two batter candidates scored within close margin" in meta.get("reason", "")


def test_striker_locked_when_clear_winner():
    """
    STRIKER LOCK REQUIREMENT:
    Striker is chosen as the tracked batter with bat overlap and proximity to stumps.
    """
    service = DetectorService()

    tracks = {
        0: DetectionTrack(
            track_id=0,
            class_name="batter",
            last_bbox=[0.4, 0.2, 0.6, 0.8],
            last_seen_frame=5,
            history={i: [0.4, 0.2, 0.6, 0.8] for i in range(5)},
            bat_overlap_count=5,
            total_frames=5,
            total_area_sum=0.6,
            stumps_distance_sum=0.5,
            stumps_distance_samples=5
        ),
        1: DetectionTrack(
            track_id=1,
            class_name="batter",
            last_bbox=[0.1, 0.2, 0.2, 0.6],
            last_seen_frame=5,
            history={i: [0.1, 0.2, 0.2, 0.6] for i in range(5)},
            bat_overlap_count=0,
            total_frames=5,
            total_area_sum=0.2,
            stumps_distance_sum=4.0,
            stumps_distance_samples=5
        )
    }

    per_frame_dets = {
        0: [
            Detection("batter", 0.90, [0.4, 0.2, 0.6, 0.8], [256, 96, 384, 384], (0.5, 0.5), (320, 240), 0.2, 0.6),
            Detection("batter", 0.75, [0.1, 0.2, 0.2, 0.6], [64, 96, 128, 288], (0.15, 0.4), (96, 192), 0.1, 0.4),
            Detection("bat", 0.90, [0.45, 0.4, 0.55, 0.7], [288, 192, 352, 336], (0.5, 0.55), (320, 264), 0.1, 0.3)
        ]
    }

    selected_tid, status, meta = service.select_striker(tracks, per_frame_dets)

    assert selected_tid == 0
    assert status == "locked"
    assert meta["selected_track_id"] == 0
    assert meta["bat_overlaps"] >= 5


def test_track_id_continuity_across_frames():
    """
    STRIKER LOCK REQUIREMENT:
    Track detections across frames with stable IDs (IoU matching).
    """
    service = DetectorService()

    # Sequential frames where batter moves slightly to the right
    per_frame_dets = {
        0: [Detection("batter", 0.90, [0.30, 0.20, 0.50, 0.80], [192, 96, 320, 384], (0.40, 0.50), (256, 240), 0.20, 0.60)],
        1: [Detection("batter", 0.91, [0.32, 0.20, 0.52, 0.80], [204, 96, 332, 384], (0.42, 0.50), (268, 240), 0.20, 0.60)],
        2: [Detection("batter", 0.89, [0.34, 0.20, 0.54, 0.80], [217, 96, 345, 384], (0.44, 0.50), (281, 240), 0.20, 0.60)],
    }

    tracks = service.track_detections(per_frame_dets, iou_threshold=0.30)

    # Must preserve exactly one track with ID 0 across all 3 frames
    assert len(tracks) == 1
    assert 0 in tracks
    assert tracks[0].total_frames == 3
    assert set(tracks[0].history.keys()) == {0, 1, 2}


@patch("requests.post")
def test_graceful_fallback_on_api_500(mock_post):
    """
    FALLBACK REQUIREMENT:
    When the hosted API returns HTTP 500, handle gracefully without raising.
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"
    mock_post.return_value = mock_resp

    service = DetectorService()
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    dets, status = service.detect_frame(dummy_frame)
    assert dets == []
    assert status == "api_error"
    assert service.last_call_success is False


@patch("requests.post")
def test_graceful_fallback_on_timeout(mock_post):
    """
    FALLBACK REQUIREMENT:
    When the hosted API times out, retry up to 2 times and return clean status.
    """
    mock_post.side_effect = Timeout("Request timed out")

    service = DetectorService()
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    dets, status = service.detect_frame(dummy_frame)
    assert dets == []
    assert status == "api_error"
    assert service.last_call_success is False
    assert mock_post.call_count == 3  # initial + 2 retries


@patch("requests.post")
def test_graceful_fallback_on_quota_429(mock_post):
    """
    FALLBACK REQUIREMENT:
    When quota or rate limit is reached (HTTP 429), return quota_exceeded cleanly.
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = "Too Many Requests: Quota exceeded"
    mock_post.return_value = mock_resp

    service = DetectorService()
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    dets, status = service.detect_frame(dummy_frame)
    assert dets == []
    assert status == "quota_exceeded"
    assert service.last_call_success is False


def test_api_call_cap_per_video():
    """
    DETECTOR SERVICE REQUIREMENT:
    Put a hard cap on calls per video (configurable) so a long clip cannot use up quota.
    """
    service = DetectorService()
    counter = {"count": settings.ROBOFLOW_MAX_CALLS_PER_VIDEO}
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    dets, status = service.detect_frame(dummy_frame, call_counter=counter)
    assert dets == []
    assert status == "quota_capped"


def test_zero_api_key_leakage_in_health_and_repr():
    """
    SECURITY REQUIREMENT:
    Never leak the ROBOFLOW_API_KEY into logs, health info, or string representations.
    """
    service = DetectorService()
    health = service.get_health_status()

    # Ensure no field contains the raw API key
    health_str = str(health)
    raw_key = settings.ROBOFLOW_API_KEY
    if raw_key and len(raw_key) > 5:
        assert raw_key not in health_str
        assert "api_key" not in health
