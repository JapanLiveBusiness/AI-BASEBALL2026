#!/usr/bin/env python3
"""Fetch authenticated Handenomori data for NPB game dates in one season."""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

APP_ROOT = Path("/app")
if (APP_ROOT / "game_calendar.py").exists():
    sys.path.insert(0, str(APP_ROOT))

from game_calendar import fetch_daily_handicaps

JST = ZoneInfo("Asia/Tokyo")


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def save_atomic(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def game_dates(history_paths: list[Path], year: int, through: date) -> list[date]:
    values = set()
    for path in history_paths:
        payload = load_json(path, [])
        rows = (payload.get("games") or []) if isinstance(payload, dict) else payload
        for row in rows if isinstance(rows, list) else []:
            try:
                value = date.fromisoformat(str(row.get("date") or "")[:10])
            except (AttributeError, ValueError):
                continue
            if value.year == year and value <= through:
                values.add(value)
    return sorted(values)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=datetime.now(JST).year)
    parser.add_argument("--history", action="append", default=[])
    parser.add_argument("--output", default="/app/data/handenomori_2026.json")
    parser.add_argument("--sleep", type=float, default=0.75)
    parser.add_argument("--retry-failed", action="store_true")
    args = parser.parse_args()

    yesterday = datetime.now(JST).date() - timedelta(days=1)
    histories = [Path(value) for value in args.history] or [
        Path("/app/data/historical_games_2017_2026.json"),
        Path("/app/data/npb_results_cache.json"),
        Path("/app/shared-data/npb_results_cache.json"),
    ]
    output = Path(args.output)
    previous = load_json(output, {})
    stored = {
        (str(row.get("date") or ""), str(row.get("home") or ""), str(row.get("away") or "")): row
        for row in previous.get("games") or []
        if isinstance(row, dict)
    }
    completed = set(previous.get("completed_dates") or [])
    failed = set(previous.get("failed_dates") or [])
    targets = game_dates(histories, args.year, yesterday)
    if not targets:
        raise SystemExit("ERROR: no official NPB game dates found for target year")

    checked = 0
    for target in targets:
        key = target.isoformat()
        if key in completed or (key in failed and not args.retry_failed):
            continue
        try:
            rows = fetch_daily_handicaps(target, timeout=20, strict=True)
        except Exception:
            failed.add(key)
            print(f"{key} authenticated fetch failed")
        else:
            if not rows:
                failed.add(key)
                print(f"{key} authenticated page returned no games")
            else:
                for row in rows:
                    row_key = (str(row.get("date") or key), str(row.get("home") or ""), str(row.get("away") or ""))
                    if all(row_key):
                        stored[row_key] = row
                completed.add(key)
                failed.discard(key)
                print(f"{key} games={len(rows)}")
        checked += 1
        payload = {
            "year": args.year,
            "generated_at": datetime.now(JST).isoformat(),
            "source": "ハンデの森（認証付き）",
            "target_dates": len(targets),
            "completed_dates": sorted(completed),
            "failed_dates": sorted(failed),
            "games": sorted(stored.values(), key=lambda row: (str(row.get("date") or ""), str(row.get("home") or ""))),
        }
        save_atomic(output, payload)
        if args.sleep > 0:
            time.sleep(args.sleep)

    final = load_json(output, {})
    print(f"YEAR: {args.year}")
    print(f"TARGET DATES: {len(targets)}")
    print(f"CHECKED NOW: {checked}")
    print(f"COMPLETED DATES: {len(final.get('completed_dates') or [])}")
    print(f"FAILED DATES: {len(final.get('failed_dates') or [])}")
    print(f"GAMES: {len(final.get('games') or [])}")
    print(f"OUTPUT: {output}")


if __name__ == "__main__":
    main()
