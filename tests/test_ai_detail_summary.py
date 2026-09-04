from ai_detail_summary import find_team_prediction, hawks_history_summary


def test_find_team_prediction_merges_schedule_and_prediction():
    schedule = {
        "games": [{
            "date": "2026-09-05",
            "home": "ソフトバンク",
            "away": "西武",
            "time": "14:00",
        }]
    }
    predictions = {
        "games": [{
            "home": "ソフトバンク",
            "away": "西武",
            "pick": "ソフトバンク",
            "win_probability": 63.5,
        }]
    }

    game = find_team_prediction(schedule, predictions)

    assert game["opponent"] == "西武"
    assert game["pick"] == "ソフトバンク"
    assert game["win_probability"] == 63.5


def test_hawks_history_summary_orders_recent_results():
    history = [
        {"date": "2026-08-15", "result": "敗"},
        {"date": "2026-08-18", "result": "勝"},
        {"date": "2026-08-20", "result": "分"},
        {"date": "2026-08-16", "result": "勝"},
        {"date": "", "result": "未確定"},
    ]

    summary = hawks_history_summary(history)

    assert summary["played"] == 4
    assert (summary["wins"], summary["losses"], summary["draws"]) == (2, 1, 1)
    assert [row["date"] for row in summary["recent"]] == [
        "2026-08-20",
        "2026-08-18",
        "2026-08-16",
        "2026-08-15",
    ]
