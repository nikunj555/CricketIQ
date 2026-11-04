import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.data.shot_catalogue import (
    SHOT_CATALOGUE,
    CRICKET_SHOT_CATEGORIES,
    get_shot_by_id_or_slug,
    resolve_shot_category
)

client = TestClient(app)

def test_shot_catalogue_completeness():
    # Exactly 25 named shots across the 7 recognized categories as defined in specification
    assert len(SHOT_CATALOGUE) == 25, f"Expected 25 shots, got {len(SHOT_CATALOGUE)}"

def test_unique_ids_and_slugs():
    ids = [s["id"] for s in SHOT_CATALOGUE]
    slugs = [s["slug"] for s in SHOT_CATALOGUE]
    names = [s["name"] for s in SHOT_CATALOGUE]

    assert len(ids) == len(set(ids)), "Duplicate shot IDs found!"
    assert len(slugs) == len(set(slugs)), "Duplicate shot slugs found!"
    assert len(names) == len(set(names)), "Duplicate shot names found!"

def test_all_categories_represented():
    catalogue_cats = {s["category"] for s in SHOT_CATALOGUE}
    for expected_cat in CRICKET_SHOT_CATEGORIES:
        assert expected_cat in catalogue_cats, f"Category '{expected_cat}' missing from catalogue"

def test_search_and_alias_resolution():
    # Search by alias
    sweep_shot = get_shot_by_id_or_slug("Traditional Sweep")
    assert sweep_shot is not None
    assert sweep_shot["slug"] == "sweep"

    # Search by name
    cut_shot = get_shot_by_id_or_slug("Square Cut")
    assert cut_shot is not None
    assert cut_shot["slug"] == "square-cut"

    # Search by slug
    pull_shot = get_shot_by_id_or_slug("pull-shot")
    assert pull_shot is not None
    assert pull_shot["name"] == "Pull Shot"

def test_category_resolution():
    assert resolve_shot_category("Cover Drive") == "Drives"
    assert resolve_shot_category("Square Cut") == "Back-foot and Cut Shots"
    assert resolve_shot_category("Slog Sweep") == "Sweep-family Strokes"
    assert resolve_shot_category("Forward Defensive") == "Defensive Strokes"
    assert resolve_shot_category("Helicopter Shot") == "Power and Innovative Shots"
    assert resolve_shot_category("Unknown Weird Stroke") == "Other"

def test_api_list_shots():
    res = client.get("/api/shots")
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] == 25
    assert len(data["shots"]) == 25
    assert len(data["categories"]) == 7

def test_api_filter_shots_by_category():
    res = client.get("/api/shots?category=Drives")
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] == 5
    for s in data["shots"]:
        assert s["category"] == "Drives"

def test_api_search_shots():
    # Searching "cut" should match Square Cut, Late Cut, Upper Cut
    res = client.get("/api/shots?search=cut")
    assert res.status_code == 200
    data = res.json()
    slugs = [s["slug"] for s in data["shots"]]
    assert "square-cut" in slugs
    assert "late-cut" in slugs
    assert "upper-cut" in slugs

def test_api_get_single_shot():
    res = client.get("/api/shots/cover-drive")
    assert res.status_code == 200
    s = res.json()
    assert s["name"] == "Cover Drive"
    assert s["category"] == "Drives"
    assert s["reference_status"] == "available"
    assert "lead_knee_flexion" in s["analysis_features"]

def test_api_get_nonexistent_shot():
    res = client.get("/api/shots/imaginary-stroke-999")
    assert res.status_code == 404

def test_reference_status_distinction():
    # Shots with authentic benchmark sequences
    cover_drive = get_shot_by_id_or_slug("cover-drive")
    assert cover_drive["reference_status"] == "available"
    assert cover_drive["reference_id"] == "ref_cover_drive_kohli"

    reverse_sweep = get_shot_by_id_or_slug("reverse-sweep")
    assert reverse_sweep["reference_status"] == "available"
    assert reverse_sweep["reference_id"] == "ref_reverse_sweep_pant"
