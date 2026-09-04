"""Pure helpers for the lightweight AI detail dashboard."""

from __future__ import annotations

from typing import Any


def hawks_probability(game: dict[str, Any] | None) -> float:
    """Convert a winning-pick probability into a Hawks win probability."""
    if not game:
        return 50.0
    try:
        probability = float(game.get("win_probability"))
    except (TypeError, ValueError):
        return 50.0
    probability = max(0.0, min(100.0, probability))
    return probability if game.get("pick") == "ソフトバンク" else 100 - probability


def simulate_hawks_win_probability(
    base_probability: float,
    *,
    mode: str = "live",
    handicap_score: float = 0.0,
    hawks_score: int = 0,
    opponent_score: int = 0,
    inning: int = 1,
    attack_side: str = "ホークス攻撃中",
    outs: int = 0,
    runners: tuple[int, ...] = (),
    context_adjustment: float = 0.0,
) -> dict[str, float]:
    """Calculate the migrated score and base-state adjustments from V8."""
    base = max(0.0, min(100.0, float(base_probability)))
    inning = max(1, min(9, int(inning)))
    outs = max(0, min(2, int(outs)))

    if mode == "pregame":
        score_adjustment = max(-55.0, min(55.0, float(handicap_score) * 8.0))
        wpa_adjustment = 0.0
    else:
        point_value = 8.0 + ((inning - 1) * 1.25)
        out_pressure = 1.0 + (outs * 0.10 if inning >= 7 else 0.0)
        score_difference = int(hawks_score) - int(opponent_score)
        score_adjustment = max(
            -55.0,
            min(55.0, score_difference * point_value * out_pressure),
        )

        runner_state = sum(
            bit for bit in runners if bit in {1, 2, 4}
        )
        raw_wpa = {
            0: 0.0,
            1: 1.5,
            2: 2.5,
            3: 4.0,
            4: 3.5,
            5: 5.0,
            6: 6.0,
            7: 8.0,
        }.get(runner_state, 0.0)
        late_factor = max(0.0, min(1.0, (inning - 4) / 5.0))
        inning_factor = 0.65 + (0.70 * late_factor)
        out_multiplier = (1.0, 0.72, 0.42)[outs]
        wpa_adjustment = raw_wpa * out_multiplier * inning_factor
        if attack_side == "相手攻撃中":
            wpa_adjustment = -wpa_adjustment

    context_adjustment = max(-25.0, min(25.0, float(context_adjustment)))
    final = max(
        0.5,
        min(
            99.5,
            base + score_adjustment + wpa_adjustment + context_adjustment,
        ),
    )
    return {
        "base_probability": round(base, 1),
        "score_adjustment": round(score_adjustment, 1),
        "wpa_adjustment": round(wpa_adjustment, 1),
        "context_adjustment": round(context_adjustment, 1),
        "final_probability": round(final, 1),
    }


def calculate_context_adjustments(
    *,
    inning: int = 1,
    venue: str = "中立",
    hawks_era: float = 3.5,
    opponent_era: float = 3.5,
    recent_wins: int = 3,
    compatibility: str = "普通",
    weather: str = "通常",
    reliever_8th: bool = True,
    reliever_9th: bool = True,
    reliever_fatigue: bool = False,
    keyman_available: bool = True,
    bench_boost: bool = False,
) -> dict[str, float]:
    """Calculate the remaining V8 context modifiers independently."""
    inning = max(1, min(9, int(inning)))
    venue_adjustment = {
        "ホーム": 3.0,
        "ビジター": -3.0,
        "中立": 0.0,
    }.get(venue, 0.0)
    pitcher_adjustment = max(
        -7.0,
        min(7.0, (float(opponent_era) - float(hawks_era)) * 2.0),
    )
    momentum_adjustment = {
        5: 5.0,
        4: 3.5,
        3: 1.5,
        2: -1.0,
        1: -3.0,
        0: -5.0,
    }.get(max(0, min(5, int(recent_wins))), 0.0)
    compatibility_adjustment = {
        "非常に得意": 5.0,
        "得意": 3.0,
        "普通": 0.0,
        "苦手": -3.0,
        "天敵": -5.0,
    }.get(compatibility, 0.0)
    weather_adjustment = {
        "追い風": 1.5,
        "ルーフオープン": 1.0,
        "通常": 0.0,
        "向かい風": -1.0,
    }.get(weather, 0.0)

    late_factor = max(0.0, min(1.0, (inning - 4) / 5.0))
    reliever_raw = (
        (2.5 if reliever_8th else 0.0)
        + (3.0 if reliever_9th else 0.0)
        - (4.0 if reliever_fatigue else 0.0)
    )
    reliever_adjustment = reliever_raw * (0.35 + 0.65 * late_factor)
    keyman_raw = (
        (2.5 if keyman_available else 0.0)
        + (1.5 if bench_boost else 0.0)
    )
    keyman_adjustment = keyman_raw * (0.60 + 0.40 * late_factor)
    values = {
        "venue": venue_adjustment,
        "pitcher": pitcher_adjustment,
        "momentum": momentum_adjustment,
        "compatibility": compatibility_adjustment,
        "weather": weather_adjustment,
        "reliever": reliever_adjustment,
        "keyman": keyman_adjustment,
    }
    values["total"] = sum(values.values())
    return {key: round(value, 1) for key, value in values.items()}


def find_team_prediction(
    schedule: dict[str, Any],
    predictions: dict[str, Any],
    team: str = "ソフトバンク",
) -> dict[str, Any] | None:
    prediction_index = {
        (str(row.get("home") or ""), str(row.get("away") or "")): row
        for row in predictions.get("games") or []
        if isinstance(row, dict)
    }
    for game in schedule.get("games") or []:
        if not isinstance(game, dict) or team not in {
            game.get("home"), game.get("away"),
        }:
            continue
        result = dict(game)
        result.update(
            prediction_index.get(
                (str(game.get("home") or ""), str(game.get("away") or "")),
                {},
            )
        )
        result["opponent"] = (
            game.get("away") if game.get("home") == team else game.get("home")
        )
        return result
    return None


def hawks_history_summary(history: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [
        row for row in history
        if isinstance(row, dict) and row.get("result") in {"勝", "敗", "分"}
    ]
    rows.sort(key=lambda row: str(row.get("date") or ""), reverse=True)
    wins = sum(row.get("result") == "勝" for row in rows)
    losses = sum(row.get("result") == "敗" for row in rows)
    draws = sum(row.get("result") == "分" for row in rows)
    return {
        "played": len(rows),
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "recent": rows[:5],
    }
