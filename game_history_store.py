import json
import logging
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

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
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
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


def _atomic_write_json(path: Path, data: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, indent=2)

    fd, temp_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        text=True,
    )
    temp_path = Path(temp_name)

    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as temp_file:
            temp_file.write(payload)
            temp_file.write("\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_path, path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


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
    _atomic_write_json(path, history)
