import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from .json_store import load_json, save_json_atomic

logger = logging.getLogger(__name__)


def _backup_corrupt_file(path: Path) -> Path | None:
    if not path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(f"{path.stem}.corrupt_{timestamp}{path.suffix}")
    try:
        shutil.copy2(path, backup_path)
        return backup_path
    except OSError:
        logger.exception("Failed to back up corrupt game history: %s", path)
        return None


def load_game_history(path: Path) -> list[dict[str, Any]]:
    try:
        data = load_json(path, [])
    except (OSError, UnicodeError, ValueError):
        backup_path = _backup_corrupt_file(path)
        logger.exception(
            "Failed to load game history from %s; backup=%s",
            path,
            backup_path,
        )
        return []
    if not isinstance(data, list):
        backup_path = _backup_corrupt_file(path)
        logger.error(
            "Game history root must be a list: %s; backup=%s",
            path,
            backup_path,
        )
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
