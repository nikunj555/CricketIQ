import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.data.shot_catalogue import SHOT_CATALOGUE
from backend.app.services.learning_video_service import learning_video_service
from backend.app.schemas.analysis import AnalysisResult

client = TestClient(app)

def test_learning_videos_file_exists():
    path = Path(__file__).resolve().parent.parent / "app" / "data" / "shot_videos.json"
    assert path.exists(), "backend/app/data/shot_videos.json must exist"

def test_all_shot_names_in_catalogue():
    catalogue_names = {s["name"] for s in SHOT_CATALOGUE}
    assert len(catalogue_names) == 25, "Catalogue must have 25 shots"
    
    video_map = learning_video_service.get_all_videos()
    assert len(video_map) == 25, "shot_videos.json must map all 25 catalogue shots"
    
    for shot_name in video_map.keys():
        assert shot_name in catalogue_names, f"Shot '{shot_name}' in shot_videos.json is not in 25-shot catalogue"

def test_all_urls_start_with_sikana_prefix():
    video_map = learning_video_service.get_all_videos()
    SIKANA_PREFIX = "https://www.sikana.tv/en/sport/cricket/"
    
    total_videos = 0
    for shot_name, vids in video_map.items():
        assert isinstance(vids, list), f"Expected list for {shot_name}"
        for item in vids:
            total_videos += 1
            assert "url" in item, f"Missing url in {shot_name}"
            assert item["url"].startswith(SIKANA_PREFIX), f"URL for {shot_name} does not start with {SIKANA_PREFIX}: {item['url']}"
            assert item.get("provider") == "Sikana"
            assert item.get("channel") == "Sikana Education"
            assert item.get("match") in ("exact", "related")

    assert total_videos > 0, "There should be at least one learning video in the registry"

def test_related_entries_keep_label():
    video_map = learning_video_service.get_all_videos()
    clip_shot_vids = video_map.get("Clip Shot", [])
    assert len(clip_shot_vids) >= 1
    assert clip_shot_vids[0]["match"] == "related"
    
    slog_sweep_vids = video_map.get("Slog Sweep", [])
    assert len(slog_sweep_vids) >= 1
    assert slog_sweep_vids[0]["match"] == "related"

    paddle_sweep_vids = video_map.get("Paddle Sweep", [])
    assert len(paddle_sweep_vids) >= 1
    assert paddle_sweep_vids[0]["match"] == "related"

def test_exact_entries_keep_label():
    video_map = learning_video_service.get_all_videos()
    cover_drive_vids = video_map.get("Cover Drive", [])
    assert len(cover_drive_vids) >= 1
    assert cover_drive_vids[0]["match"] == "exact"
    assert cover_drive_vids[0]["url"] == "https://www.sikana.tv/en/sport/cricket/cover-drive"

def test_empty_entries_for_shots_without_lessons():
    video_map = learning_video_service.get_all_videos()
    assert video_map.get("Hook Shot") == []
    assert video_map.get("Upper Cut") == []
    assert video_map.get("Helicopter Shot") == []

def test_api_get_shot_videos_exact():
    res = client.get("/api/shots/Cover%20Drive/videos")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["title"] == "How to Play a Cover Drive"
    assert data[0]["match"] == "exact"
    assert data[0]["url"] == "https://www.sikana.tv/en/sport/cricket/cover-drive"

def test_api_get_shot_videos_by_slug():
    res = client.get("/api/shots/cover-drive/videos")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["title"] == "How to Play a Cover Drive"

def test_api_get_shot_videos_related():
    res = client.get("/api/shots/Clip%20Shot/videos")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["match"] == "related"
    assert data[0]["url"] == "https://www.sikana.tv/en/sport/cricket/flick-shot"

def test_api_get_shot_videos_empty():
    res = client.get("/api/shots/Hook%20Shot/videos")
    assert res.status_code == 200
    data = res.json()
    assert data == []

def test_api_get_shot_videos_not_found():
    res = client.get("/api/shots/non-existent-stroke-xyz/videos")
    assert res.status_code == 404

def test_analysis_result_schema_includes_learning_videos():
    res = AnalysisResult(
        session_id="test_sess",
        video_filename="test.mp4",
        shot_type="Cover Drive",
        learning_videos=[
            {
                "title": "How to Play a Cover Drive",
                "provider": "Sikana",
                "channel": "Sikana Education",
                "url": "https://www.sikana.tv/en/sport/cricket/cover-drive",
                "match": "exact"
            }
        ]
    )
    dumped = res.model_dump()
    assert "learning_videos" in dumped
    assert len(dumped["learning_videos"]) == 1
    assert dumped["learning_videos"][0]["match"] == "exact"
