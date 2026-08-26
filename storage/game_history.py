from pathlib import Path
from typing import Any

from .json_store import load_json, save_json_atomic


def load_game_history(path: Path) -> list[dict[str, Any]]:
    try:
        data = load_json(path, [])
    except (OSError, UnicodeError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def save_game_history(path: Path, game: dict[str, Any]) -> None:
    history = load_game_history(path)
    game_id = game.get("game_id")
    updated = False

    for index, old in enumerate(history):
        if old.get("game_id") != game_id:
            continue

        locked_pregame = old.get("pregame_probability")
        if locked_pregame is None:
            locked_pregame = old.get("ai_probability")

        merged = dict(old)
        merged.update(game)

        if locked_pregame is not None:
            merged["pregame_probability"] = locked_pregame
            merged["ai_probability"] = locked_pregame

        history[index] = merged
        updated = True
        break

    if not updated:
        history.append(game)

    history.sort(key=lambda item: item.get("date", ""), reverse=True)
    save_json_atomic(path, history)
