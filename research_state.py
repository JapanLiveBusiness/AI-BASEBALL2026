from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from display_games import select_display_context

JST = ZoneInfo("Asia/Tokyo")
REPO_DATA_DIR = Path(__file__).resolve().parent / "data"
PROD_DATA_DIR = Path("/app/data")
SLATE_ARCHIVE = PROD_DATA_DIR / "npb_slates_archive.json"


def data_path(name: str) -> Path:
    prod = PROD_DATA_DIR / name
    if prod.exists() and prod.is_file() and prod.stat().st_size:
        return prod
    return REPO_DATA_DIR / name


def load_json(name: str, fallback: Any) -> Any:
    path = data_path(name)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback
    if isinstance(value, dict) and "games" in value and not value.get("games"):
        repo = REPO_DATA_DIR / name
        if path != repo:
            try:
                repo_value = json.loads(repo.read_text(encoding="utf-8"))
                if isinstance(repo_value, dict) and repo_value.get("games"):
                    return repo_value
            except (OSError, json.JSONDecodeError):
                pass
    return value


def _load_archive() -> list[dict]:
    try:
        value = json.loads(SLATE_ARCHIVE.read_text(encoding="utf-8"))
        return list(value) if isinstance(value, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def archive_slate(payload: dict) -> list[dict]:
    archive = _load_archive()
    slate_date = str((payload or {}).get("date") or "")
    games = list((payload or {}).get("games") or [])
    if not slate_date or not games:
        return archive

    entry = {
        "date": slate_date,
        "updated_at": payload.get("updated_at"),
        "games": games,
    }
    archive = [row for row in archive if str(row.get("date") or "") != slate_date]
    archive.append(entry)
    archive.sort(key=lambda row: str(row.get("date") or ""))
    archive = archive[-14:]

    try:
        PROD_DATA_DIR.mkdir(parents=True, exist_ok=True)
        SLATE_ARCHIVE.write_text(json.dumps(archive, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass
    return archive


def current_slate(now: datetime | None = None, lead_hours: int = 2) -> dict:
    schedule = load_json("npb_today.json", {"games": []})
    archive = archive_slate(schedule)
    current_date = str(schedule.get("date") or "")
    previous = [row for row in archive if str(row.get("date") or "") != current_date]
    return {
        "schedule": schedule,
        **select_display_context(
            schedule,
            previous_payloads=previous,
            now=now or datetime.now(JST),
            lead_hours=lead_hours,
        ),
    }


def parse_timestamp(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=JST)
    return parsed.astimezone(JST)


def freshness(payload: dict, now: datetime | None = None) -> dict:
    now = now or datetime.now(JST)
    updated = parse_timestamp((payload or {}).get("updated_at"))
    payload_date = str((payload or {}).get("date") or "")
    today = now.date().isoformat()
    hours = None
    if updated is not None:
        hours = max(0.0, (now - updated).total_seconds() / 3600.0)

    if payload_date == today and (hours is None or hours <= 12):
        level = "fresh"
        label = "最新"
    elif payload_date == today:
        level = "warning"
        label = "更新待ち"
    elif payload_date:
        level = "stale"
        label = "過去データ"
    else:
        level = "missing"
        label = "データなし"

    return {
        "level": level,
        "label": label,
        "date": payload_date or "--",
        "updated_at": updated,
        "age_hours": hours,
    }


def prediction_for_display(display_date: str | None) -> dict:
    predictions = load_json("today_ai_predictions.json", {"games": []})
    if str(predictions.get("date") or "") != str(display_date or ""):
        return {"games": [], "date": predictions.get("date"), "updated_at": predictions.get("updated_at")}
    return predictions


def data_health_rows() -> list[dict]:
    rows = []
    for name, label in (
        ("npb_today.json", "試合データ"),
        ("today_ai_predictions.json", "AI予測"),
        ("game_history.json", "試合履歴"),
        ("historical_backtest_report.json", "長期検証"),
    ):
        path = data_path(name)
        exists = path.exists() and path.is_file() and path.stat().st_size > 0
        rows.append({
            "項目": label,
            "ファイル": name,
            "状態": "OK" if exists else "未取得",
            "保存先": "本番共有" if str(path).startswith("/app/data") else "リポジトリ",
        })
    return rows
