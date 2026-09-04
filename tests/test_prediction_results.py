from prediction_results import archive_predictions, build_performance, settle_predictions


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
