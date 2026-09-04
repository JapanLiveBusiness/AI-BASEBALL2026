"""Pure helpers for selecting and normalizing the match-center gamecast."""

from __future__ import annotations

from typing import Any, Iterable


LIVE_STATUSES = {"live", "in_progress", "playing", "試合中", "開催中"}
FINAL_STATUSES = {"final", "finished", "completed", "終了", "試合終了"}


def _status(game: dict[str, Any]) -> str:
    return str(game.get("status") or "scheduled").strip().lower()


def _is_live(game: dict[str, Any]) -> bool:
    status = _status(game)
    return status in LIVE_STATUSES or any(
        token in status for token in ("live", "progress", "試合中")
    )


def _is_final(game: dict[str, Any]) -> bool:
    status = _status(game)
    return status in FINAL_STATUSES or any(
        token in status for token in ("final", "finish", "終了")
    )


def select_featured_game(games: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    """Prefer a live game, then a Hawks game, then the first scheduled game."""
    rows = list(games)
    if not rows:
        return None
    return next((game for game in rows if _is_live(game)), None) or next(
        (
            game
            for game in rows
            if "ソフトバンク" in {str(game.get("home")), str(game.get("away"))}
        ),
        rows[0],
    )


def _bounded_count(value: Any, maximum: int) -> int:
    try:
        return max(0, min(maximum, int(value)))
    except (TypeError, ValueError):
        return 0


def occupied_bases(game: dict[str, Any]) -> set[int]:
    """Normalize common runner/base payload shapes into occupied base numbers."""
    occupied: set[int] = set()
    raw = game.get("runners")
    if isinstance(raw, dict):
        for key, value in raw.items():
            if not value:
                continue
            token = str(key).lower()
            if "1" in token or "first" in token or "一" in token:
                occupied.add(1)
            elif "2" in token or "second" in token or "二" in token:
                occupied.add(2)
            elif "3" in token or "third" in token or "三" in token:
                occupied.add(3)
    elif isinstance(raw, (list, tuple, set)):
        for item in raw:
            token = str(item).lower()
            if token in {"1", "1b", "first", "一塁"}:
                occupied.add(1)
            elif token in {"2", "2b", "second", "二塁"}:
                occupied.add(2)
            elif token in {"3", "3b", "third", "三塁"}:
                occupied.add(3)

    bases = game.get("bases")
    if isinstance(bases, dict):
        occupied.update(occupied_bases({"runners": bases}))
    for base in (1, 2, 3):
        if game.get(f"base_{base}") or game.get(f"runner_on_{base}"):
            occupied.add(base)
    return occupied


def lineup_names(game: dict[str, Any]) -> list[str]:
    raw = game.get("lineup") or game.get("batters") or []
    if not isinstance(raw, list):
        return []
    names = []
    for item in raw[:9]:
        if isinstance(item, dict):
            name = item.get("name") or item.get("player") or item.get("batter")
        else:
            name = item
        text = str(name or "").strip()
        if text:
            names.append(text)
    return names


def gamecast_snapshot(game: dict[str, Any]) -> dict[str, Any]:
    """Return display-ready state without inventing unavailable live details."""
    live = _is_live(game)
    final = _is_final(game)
    inning = game.get("inning") or game.get("current_inning")
    half = str(game.get("inning_half") or game.get("half") or "").strip()
    if inning:
        inning_label = f"{inning}回{half}" if half else f"{inning}回"
    elif final:
        inning_label = "試合終了"
    elif live:
        inning_label = "進行情報取得中"
    else:
        inning_label = "試合前"

    return {
        "live": live,
        "final": final,
        "status_label": "LIVE" if live else "FINAL" if final else "PRE GAME",
        "inning_label": inning_label,
        "balls": _bounded_count(game.get("balls") or game.get("ball"), 3),
        "strikes": _bounded_count(game.get("strikes") or game.get("strike"), 2),
        "outs": _bounded_count(game.get("outs") or game.get("out"), 2),
        "bases": occupied_bases(game),
        "pitcher": str(
            game.get("current_pitcher")
            or game.get("pitcher")
            or game.get("home_starter")
            or game.get("away_starter")
            or "投手情報待ち"
        ),
        "batter": str(game.get("current_batter") or game.get("batter") or "打者情報待ち"),
        "lineup": lineup_names(game),
    }
