"""Pure helpers for the lightweight AI detail dashboard."""

from __future__ import annotations

from typing import Any


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

