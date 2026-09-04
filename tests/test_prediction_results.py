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
