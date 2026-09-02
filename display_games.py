from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo


JST = ZoneInfo("Asia/Tokyo")
DEFAULT_START = time(18, 0)


def _normalize_now(now=None):
    now = now or datetime.now(JST)
    if now.tzinfo is None:
        return now.replace(tzinfo=JST)
    return now.astimezone(JST)


def _parse_start(game_date: str, raw_time) -> datetime:
    start_time = DEFAULT_START
    text = str(raw_time or "").strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            parsed = datetime.strptime(text, fmt).time()
            start_time = parsed
            break
        except ValueError:
            continue
    return datetime.fromisoformat(game_date).replace(
        hour=start_time.hour,
        minute=start_time.minute,
        second=start_time.second,
        microsecond=0,
        tzinfo=JST,
    )


def _collect_dated_games(payloads):
    dated_games = {}
    seen = set()
    for payload in payloads:
        if not payload:
            continue
        default_date = str(payload.get("date") or "")
        for game in list(payload.get("games", []) or []):
            game_date = str(game.get("date") or default_date or "")
            if not game_date:
                continue
            key = (
                game_date,
                str(game.get("home") or ""),
                str(game.get("away") or ""),
                str(game.get("time") or ""),
            )
            if key in seen:
                continue
            seen.add(key)
            dated_games.setdefault(game_date, []).append(game)
    return dated_games


def select_display_context(payload, previous_payloads=None, now=None, lead_hours=2):
    """Select the slate whose switch time has most recently passed.

    A slate becomes active ``lead_hours`` before its earliest scheduled first
    pitch. Until then, the immediately preceding slate remains visible. This
    also keeps the latest completed slate on screen across off-days.
    """
    now = _normalize_now(now)
    payloads = list(previous_payloads or []) + [payload or {}]
    dated_games = _collect_dated_games(payloads)

    if not dated_games:
        return {
            "games": [],
            "display_date": None,
            "next_date": None,
            "switch_at": None,
            "is_previous_preview": False,
        }

    dates = sorted(dated_games)
    switch_times = {}
    for game_date in dates:
        starts = [_parse_start(game_date, game.get("time")) for game in dated_games[game_date]]
        first_pitch = min(starts) if starts else _parse_start(game_date, None)
        switch_times[game_date] = first_pitch - timedelta(hours=lead_hours)

    active_dates = [game_date for game_date in dates if switch_times[game_date] <= now]
    if active_dates:
        display_date = active_dates[-1]
    else:
        display_date = dates[0]

    future_dates = [game_date for game_date in dates if switch_times[game_date] > now]
    next_date = future_dates[0] if future_dates else None
    switch_at = switch_times.get(next_date) if next_date else None

    today = now.date().isoformat()
    is_previous_preview = display_date < today or (
        next_date is not None and display_date < next_date and switch_times[next_date] > now
    )

    return {
        "games": dated_games[display_date],
        "display_date": display_date,
        "next_date": next_date,
        "switch_at": switch_at,
        "is_previous_preview": is_previous_preview,
    }


def select_display_games(payload, now=None, previous_payloads=None, lead_hours=2):
    """Compatibility wrapper returning only the selected games."""
    return select_display_context(
        payload,
        previous_payloads=previous_payloads,
        now=now,
        lead_hours=lead_hours,
    )["games"]
