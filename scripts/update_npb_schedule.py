#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

JST = ZoneInfo("Asia/Tokyo")
BASE_URL = "https://npb.jp/games/{year}/schedule_{month:02d}_detail.html"

TEAM_NAMES = (
    "ソフトバンク",
    "日本ハム",
    "オリックス",
    "ヤクルト",
    "DeNA",
    "ロッテ",
    "楽天",
    "西武",
    "巨人",
    "阪神",
    "広島",
    "中日",
)
CENTRAL = {"巨人", "阪神", "DeNA", "広島", "中日", "ヤクルト"}
PACIFIC = {"ソフトバンク", "日本ハム", "ロッテ", "楽天", "オリックス", "西武"}
DATE_RE = re.compile(r"(?P<month>\d{1,2})/(?P<day>\d{1,2})")
TIME_RE = re.compile(r"(?P<time>\d{1,2}:\d{2})")
SCORE_RE = re.compile(r"(?P<away_score>\d+)\s*[-－]\s*(?P<home_score>\d+)")


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\u3000", " ")).strip()


def league_for(home: str, away: str) -> str:
    sides = {home, away}
    if sides <= CENTRAL:
        return "セ・リーグ"
    if sides <= PACIFIC:
        return "パ・リーグ"
    return "交流戦"


def parse_card(text: str) -> tuple[str, str, int | None, int | None] | None:
    text = normalize_space(text)
    if "予備日" in text:
        return None

    found: list[tuple[int, str]] = []
    for team in TEAM_NAMES:
        pos = text.find(team)
        if pos >= 0:
            found.append((pos, team))
    found.sort()
    if len(found) < 2:
        return None

    # NPB detail tables list the home club first and visitor second.
    home = found[0][1]
    away = found[1][1]
    score_match = SCORE_RE.search(text)
    if score_match:
        home_score = int(score_match.group("away_score"))
        away_score = int(score_match.group("home_score"))
    else:
        home_score = None
        away_score = None
    return home, away, home_score, away_score


def rows_from_html(html_text: str, year: int, source_url: str) -> dict[str, list[dict]]:
    soup = BeautifulSoup(html_text, "html.parser")
    schedule_table = None
    for table in soup.find_all("table"):
        heading = normalize_space(table.get_text(" ", strip=True))
        if "対戦カード" in heading and "球場" in heading:
            schedule_table = table
            break
    if schedule_table is None:
        raise RuntimeError("NPB schedule table was not found; refusing to overwrite current data")

    by_date: dict[str, list[dict]] = {}
    current_date: str | None = None
    parsed_rows = 0

    for tr in schedule_table.find_all("tr"):
        cells = tr.find_all(["th", "td"], recursive=False)
        if not cells:
            continue
        texts = [normalize_space(cell.get_text(" ", strip=True)) for cell in cells]
        if not any(texts):
            continue

        date_match = DATE_RE.search(texts[0])
        offset = 0
        if date_match:
            month = int(date_match.group("month"))
            day = int(date_match.group("day"))
            current_date = date(year, month, day).isoformat()
            offset = 1
        if not current_date:
            continue

        remaining = texts[offset:]
        card_index = next(
            (i for i, value in enumerate(remaining) if sum(team in value for team in TEAM_NAMES) >= 2),
            None,
        )
        if card_index is None:
            continue
        card = parse_card(remaining[card_index])
        if card is None:
            continue
        home, away, home_score, away_score = card

        venue_time = remaining[card_index + 1] if card_index + 1 < len(remaining) else ""
        time_match = TIME_RE.search(venue_time)
        start_time = time_match.group("time") if time_match else "--:--"
        venue = TIME_RE.sub("", venue_time)
        venue = re.sub(r"(晴れ|曇り|くもり|雨|雪).*$", "", venue).strip(" ・")
        venue = venue or "会場未定"

        status = "final" if home_score is not None and away_score is not None else "scheduled"
        game = {
            "date": current_date,
            "time": start_time,
            "status": status,
            "home": home,
            "away": away,
            "home_score": home_score,
            "away_score": away_score,
            "venue": venue,
            "league": league_for(home, away),
            "result_source": "NPB公式",
            "official_url": source_url,
        }
        by_date.setdefault(current_date, []).append(game)
        parsed_rows += 1

    if parsed_rows == 0:
        raise RuntimeError("NPB schedule page was fetched but no game rows could be parsed")
    return by_date


def month_iter(start: date, count: int = 2) -> Iterable[tuple[int, int]]:
    year, month = start.year, start.month
    for _ in range(count):
        yield year, month
        month += 1
        if month == 13:
            year += 1
            month = 1


def fetch_month(year: int, month: int) -> tuple[str, str]:
    url = BASE_URL.format(year=year, month=month)
    headers = {
        "User-Agent": "AI-BASEBALL-STUDIO/1.0 (+schedule sync; contact via JapanLiveBusiness)",
        "Accept-Language": "ja,en;q=0.8",
    }
    response = requests.get(url, timeout=25, headers=headers)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    return url, response.text


def choose_slate(by_date: dict[str, list[dict]], today: date) -> tuple[str, list[dict]]:
    today_text = today.isoformat()
    if by_date.get(today_text):
        return today_text, by_date[today_text]
    future = sorted(key for key, games in by_date.items() if key > today_text and games)
    if not future:
        raise RuntimeError("No current or future NPB slate was found in the fetched schedule")
    selected = future[0]
    return selected, by_date[selected]


def build_payload(today: date | None = None) -> dict:
    today = today or datetime.now(JST).date()
    combined: dict[str, list[dict]] = {}
    fetched_urls: list[str] = []
    errors: list[str] = []

    for year, month in month_iter(today, count=2):
        try:
            url, html_text = fetch_month(year, month)
            fetched_urls.append(url)
            parsed = rows_from_html(html_text, year, url)
            for game_date, games in parsed.items():
                combined[game_date] = games
        except Exception as exc:
            errors.append(f"{year}-{month:02d}: {exc}")

    if not combined:
        raise RuntimeError("; ".join(errors) or "NPB schedule fetch failed")

    selected_date, games = choose_slate(combined, today)
    games = sorted(games, key=lambda row: (str(row.get("time") or "99:99"), str(row.get("home") or "")))
    return {
        "date": selected_date,
        "updated_at": datetime.now(JST).isoformat(timespec="seconds"),
        "count": len(games),
        "games": games,
        "source": "NPB公式",
        "source_urls": fetched_urls,
        "selection": "today_or_next_scheduled_slate",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch the current/next NPB official game slate")
    parser.add_argument("--date", help="JST reference date in YYYY-MM-DD format")
    parser.add_argument("--output", default="/tmp/npb_today.json")
    args = parser.parse_args()

    target_date = date.fromisoformat(args.date) if args.date else None
    payload = build_payload(target_date)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(output.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(output)
    print(json.dumps({"date": payload["date"], "count": payload["count"], "output": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
