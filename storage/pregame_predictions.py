from datetime import datetime
from pathlib import Path
from typing import Any

from .json_store import load_json, save_json_atomic


def load_pregame_predictions(path: Path) -> list[dict[str, Any]]:
    try:
        data = load_json(path, [])
    except (OSError, UnicodeError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def save_pregame_prediction(
    path: Path,
    date_value: Any,
    opponent: Any,
    probability_value: Any,
    model: str = "V8 FINAL",
) -> float:
    data = load_pregame_predictions(path)
    game_id = f"{date_value}_{opponent}"

    for row in data:
        if row.get("game_id") == game_id:
            try:
                return float(row["probability"])
            except (KeyError, TypeError, ValueError):
                break

    probability = round(float(probability_value), 1)
    data.append(
        {
            "game_id": game_id,
            "date": date_value,
            "opponent": opponent,
            "probability": probability,
            "model": model,
            "locked": True,
            "saved_at": datetime.now().isoformat(),
        }
    )
    save_json_atomic(path, data)
    return probability


def get_pregame_probability(path: Path, date_value: Any, opponent: Any) -> float | None:
    game_id = f"{date_value}_{opponent}"
    for row in load_pregame_predictions(path):
        if row.get("game_id") == game_id:
            try:
                return float(row.get("probability"))
            except (TypeError, ValueError):
                return None
    return None
