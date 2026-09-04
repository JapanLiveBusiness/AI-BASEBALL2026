from ai_detail_summary import (
    find_team_prediction,
    hawks_history_summary,
    hawks_probability,
    simulate_hawks_win_probability,
)


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


def test_hawks_probability_inverts_opponent_pick():
    assert hawks_probability({
        "pick": "ソフトバンク",
        "win_probability": 63.5,
    }) == 63.5
    assert hawks_probability({
        "pick": "西武",
        "win_probability": 58,
    }) == 42.0


def test_pregame_simulator_applies_handicap_value():
    result = simulate_hawks_win_probability(
        60,
        mode="pregame",
        handicap_score=-1.0,
    )

    assert result["score_adjustment"] == -8.0
    assert result["wpa_adjustment"] == 0.0
    assert result["final_probability"] == 52.0


def test_live_simulator_values_late_scoring_opportunity():
    hawks_attack = simulate_hawks_win_probability(
        50,
        hawks_score=3,
        opponent_score=3,
        inning=9,
        attack_side="ホークス攻撃中",
        outs=0,
        runners=(1, 2, 4),
    )
    opponent_attack = simulate_hawks_win_probability(
        50,
        hawks_score=3,
        opponent_score=3,
        inning=9,
        attack_side="相手攻撃中",
        outs=0,
        runners=(1, 2, 4),
    )

    assert hawks_attack["final_probability"] > 50
    assert opponent_attack["final_probability"] < 50


def test_live_simulator_clamps_extreme_scores():
    result = simulate_hawks_win_probability(
        90,
        hawks_score=20,
        opponent_score=0,
        inning=9,
    )

    assert result["score_adjustment"] == 55.0
    assert result["final_probability"] == 99.5
