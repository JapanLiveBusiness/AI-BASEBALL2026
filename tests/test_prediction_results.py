import json

from prediction_results import (
    archive_predictions,
    build_performance,
    merge_prediction_archives,
    settle_predictions,
    sync_prediction_results,
)


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_settlement_uses_each_cached_game_date_and_not_envelope_date():
    predictions = {"date": "2026-09-05", "games": [
        {"home": "A", "away": "B", "pick": "A", "win_probability": 60}]}
    archive, _ = archive_predictions([], predictions, {"date": "2026-09-05", "games": []})
    cache = {"date": "2026-09-06", "games": [
        {"date": "2026-09-05", "home": "A", "away": "B", "status": "final",
         "home_score": 2, "away_score": 0},
        {"date": "2026-09-06", "home": "A", "away": "B", "status": "live",
         "home_score": 0, "away_score": 1}]}
    settled, count = settle_predictions(archive, cache)
    assert count == 1
    assert settled[0]["hit"] is True
    assert settled[0]["actual_home_score"] == 2
    assert settled[0]["win_probability"] == 60
    assert archive[0]["status"] == "pending"
    assert settle_predictions(settled, cache)[1] == 0


def test_settlement_maps_scores_to_archived_home_away_order():
    archive = [{"date": "2026-09-05", "home": "A", "away": "B", "pick": "A",
                "home_win_probability": 60, "status": "pending"}]
    cache = {"games": [{"date": "2026-09-05", "home": "B", "away": "A",
                         "status": "final", "home_score": 0, "away_score": 2}]}
    settled, count = settle_predictions(archive, cache)
    assert count == 1
    assert settled[0]["hit"] is True
    assert settled[0]["actual_home_score"] == 2


def test_sync_settles_previous_day_from_results_cache(tmp_path):
    _write_json(tmp_path / "ai_prediction_history.json", [
        {"game_id": "2026-09-05_A_B", "date": "2026-09-05", "home": "A",
         "away": "B", "pick": "A", "win_probability": 60, "status": "pending"}])
    _write_json(tmp_path / "npb_today.json", {"date": "2026-09-06", "games": []})
    _write_json(tmp_path / "npb_results_cache.json", {"games": [
        {"date": "2026-09-05", "home": "A", "away": "B", "status": "final",
         "home_score": 2, "away_score": 0}]})
    result = sync_prediction_results(tmp_path, None)
    saved = json.loads((tmp_path / "ai_prediction_history.json").read_text(encoding="utf-8"))
    assert result["settled"] == 1
    assert saved[0]["status"] == "final"
    assert saved[0]["win_probability"] == 60


def test_all_predictions_are_locked_and_settled_from_final_schedule():
    predictions = {
        "date": "2026-09-04",
        "model": "test-model",
        "games": [
            {"home": "阪神", "away": "巨人", "pick": "阪神", "win_probability": 60, "predicted_score": "4-2", "confidence": "HIGH"},
            {"home": "西武", "away": "楽天", "pick": "楽天", "win_probability": 55, "predicted_score": "2-3", "confidence": "LOW"},
        ],
    }
    schedule = {
        "date": "2026-09-04",
        "games": [
            {"home": "阪神", "away": "巨人", "time": "18:00", "status": "final", "home_score": 5, "away_score": 1},
            {"home": "西武", "away": "楽天", "time": "18:00", "status": "final", "home_score": 4, "away_score": 3},
        ],
    }

    archive, added = archive_predictions([], predictions, schedule)
    assert added == 2
    assert archive[0]["home_win_probability"] == 45.0 or archive[1]["home_win_probability"] == 45.0
    settled, settled_count = settle_predictions(archive, schedule)
    performance = build_performance(settled)

    assert settled_count == 2
    assert performance["settled_games"] == 2
    assert performance["hits"] == 1
    assert performance["hit_rate"] == 50.0
    assert all(row["locked"] for row in settled)


def test_locked_prediction_is_not_overwritten_and_draw_is_excluded():
    predictions = {"date": "2026-09-04", "games": [{"home": "A", "away": "B", "pick": "A", "win_probability": 70}]}
    schedule = {"date": "2026-09-04", "games": [{"home": "A", "away": "B", "status": "final", "home_score": 2, "away_score": 2}]}
    archive, _ = archive_predictions([], predictions, schedule)
    changed_predictions = {"date": "2026-09-04", "games": [{"home": "A", "away": "B", "pick": "B", "win_probability": 90}]}
    archive, added = archive_predictions(archive, changed_predictions, schedule)
    settled, _ = settle_predictions(archive, schedule)

    assert added == 0
    assert settled[0]["pick"] == "A"
    assert settled[0]["status"] == "draw"
    assert build_performance(settled)["settled_games"] == 0


def test_shared_final_prediction_replaces_local_pending_copy():
    local = [{"game_id": "g1", "date": "2026-09-04", "status": "pending", "pick": "A"}]
    shared = [
        {
            "game_id": "g1",
            "date": "2026-09-04",
            "status": "final",
            "pick": "A",
            "actual_winner": "A",
            "hit": True,
        },
        {"game_id": "g2", "date": "2026-09-05", "status": "pending", "pick": "B"},
    ]

    merged = merge_prediction_archives(local, shared)

    assert len(merged) == 2
    assert merged[0]["status"] == "final"
    assert merged[0]["hit"] is True


def test_sync_archives_current_research_prediction(tmp_path):
    production = tmp_path / "production"
    research = tmp_path / "research"
    production.mkdir()
    research.mkdir()
    _write_json(production / "today_ai_predictions.json", {})
    _write_json(production / "npb_today.json", {})
    _write_json(
        research / "today_ai_predictions.json",
        {"date": "2026-09-05", "games": [{"home": "A", "away": "B", "pick": "A", "win_probability": 60}]},
    )
    _write_json(
        research / "npb_today.json",
        {"date": "2026-09-05", "games": [{"home": "A", "away": "B", "status": "scheduled", "time": "18:00"}]},
    )

    result = sync_prediction_results(production, research)
    saved = json.loads((production / "ai_prediction_history.json").read_text(encoding="utf-8"))

    assert result["added"] == 1
    assert result["shared"] == 1
    assert saved[0]["game_id"] == "2026-09-05_A_B"
