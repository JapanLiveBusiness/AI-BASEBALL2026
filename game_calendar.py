from __future__ import annotations

import re
from datetime import date

import requests
from bs4 import BeautifulSoup


NPB_SCHEDULE_URL = "https://npb.jp/games/{year}/schedule_{month:02d}_detail.html"
HANDICAP_URL = "https://handenomori.com/jpb/{ymd}/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/151 Safari/537.36"
    )
}
TEAM_NAMES = (
    "ソフトバンク",
    "日本ハム",
    "オリックス",
    "ヤクルト",
    "DeNA",
    "ロッテ",
    "巨人",
    "阪神",
    "広島",
    "中日",
    "楽天",
    "西武",
)
TEAM_ALIASES = {
    "福岡ソフトバンク": "ソフトバンク",
    "横浜DeNA": "DeNA",
}


def clean_text(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_team(value) -> str:
    text = clean_text(value)
    for alias, canonical in TEAM_ALIASES.items():
        text = text.replace(alias, canonical)
    return text


def _teams_in_text(text: str) -> list[str]:
    normalized = normalize_team(text)
    found = []
    for team in TEAM_NAMES:
        position = normalized.find(team)
        if position >= 0:
            found.append((position, team))
    return [team for _, team in sorted(found)[:2]]


def parse_npb_schedule_html(content, year: int, month: int) -> list[dict]:
    """Parse one official NPB monthly schedule into normalized game rows."""
    soup = BeautifulSoup(content, "html.parser")
    current_date = None
    games = []
    source_url = NPB_SCHEDULE_URL.format(year=year, month=month)

    for row in soup.find_all("tr"):
        cells = [clean_text(cell.get_text(" ", strip=True)) for cell in row.find_all(["th", "td"])]
        text = clean_text(row.get_text(" ", strip=True))
        date_match = re.search(r"(?<!\d)(\d{1,2})/(\d{1,2})(?!\d)", text)
        if date_match:
            try:
                current_date = date(year, int(date_match.group(1)), int(date_match.group(2)))
            except ValueError:
                current_date = None
        if current_date is None or current_date.month != month:
            continue

        teams = _teams_in_text(text)
        if len(teams) != 2:
            continue

        matchup_cell = next((cell for cell in cells if len(_teams_in_text(cell)) == 2), text)
        score_match = re.search(r"(?<!\d)(\d{1,2})\s*-\s*(\d{1,2})(?!\d)", matchup_cell)
        time_match = re.search(r"(?<!\d)(\d{1,2}:\d{2})(?!\d)", text)
        venue = "会場未定"
        if time_match:
            venue_cell = next((cell for cell in cells if time_match.group(1) in cell), "")
            candidate = clean_text(venue_cell.split(time_match.group(1), 1)[0])
            if candidate:
                venue = candidate

        status = "scheduled"
        if score_match:
            status = "final"
        elif any(token in text for token in ("中止", "ノーゲーム")):
            status = "cancelled"

        games.append(
            {
                "date": current_date.isoformat(),
                "time": time_match.group(1) if time_match else "--:--",
                "status": status,
                "home": teams[0],
                "away": teams[1],
                "home_score": int(score_match.group(1)) if score_match else None,
                "away_score": int(score_match.group(2)) if score_match else None,
                "venue": venue,
                "source_url": source_url,
                "official_url": source_url,
                "result_source": "NPB公式",
            }
        )

    unique = {}
    for game in games:
        unique[(game["date"], game["home"], game["away"])] = game
    return list(unique.values())


def fetch_npb_schedule_day(target_date: date, timeout: int = 12) -> list[dict]:
    url = NPB_SCHEDULE_URL.format(year=target_date.year, month=target_date.month)
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        response.raise_for_status()
        games = parse_npb_schedule_html(response.content, target_date.year, target_date.month)
    except Exception:
        return []
    return [game for game in games if game.get("date") == target_date.isoformat()]


def parse_handicap_html(content, target_date: date) -> list[dict]:
    """Parse every published handicap from a Handenomori daily page."""
    soup = BeautifulSoup(content, "html.parser")
    games = []
    source_url = HANDICAP_URL.format(ymd=target_date.strftime("%Y%m%d"))

    for card in soup.select(".game-detail2"):
        teams = [normalize_team(node.get_text(" ", strip=True)) for node in card.select(".detail-card-team")]
        teams = [team for team in teams if team]
        if len(teams) < 2:
            continue

        handicap_cells = [clean_text(node.get_text(" ", strip=True)) for node in card.select("td.single-handi-handi")]
        handicap_cells += [""] * max(0, 2 - len(handicap_cells))
        score_match = re.search(r"(?<!\d)(\d{1,2})\s*-\s*(\d{1,2})(?!\d)", clean_text(card.get_text(" ", strip=True)))
        info = [clean_text(node.get_text(" ", strip=True)) for node in card.select(".detail-single-studium-time span")]

        games.append(
            {
                "date": target_date.isoformat(),
                "home": teams[0],
                "away": teams[1],
                "home_score": int(score_match.group(1)) if score_match else None,
                "away_score": int(score_match.group(2)) if score_match else None,
                "status": "final" if score_match else "result_pending",
                "home_handicap": handicap_cells[0] or None,
                "away_handicap": handicap_cells[1] or None,
                "time": info[0] if info else None,
                "venue": info[1] if len(info) > 1 else None,
                "handicap_source_url": source_url,
                "result_source": "ハンデの森",
            }
        )
    return games


def fetch_daily_handicaps(target_date: date, timeout: int = 12) -> list[dict]:
    url = HANDICAP_URL.format(ymd=target_date.strftime("%Y%m%d"))
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        response.raise_for_status()
        return parse_handicap_html(response.content, target_date)
    except Exception:
        return []


def same_match(left: dict, right: dict) -> bool:
    left_teams = {normalize_team(left.get("home")), normalize_team(left.get("away"))}
    right_teams = {normalize_team(right.get("home")), normalize_team(right.get("away"))}
    return "" not in left_teams and left_teams == right_teams


def merge_game_sources(*sources: list[dict]) -> list[dict]:
    """Merge schedule/result sources without downgrading confirmed results."""
    merged = []
    for source in sources:
        for incoming in source or []:
            existing = next((game for game in merged if same_match(game, incoming)), None)
            if existing is None:
                merged.append(dict(incoming))
                continue
            existing_final = str(existing.get("status") or "").lower() in {
                "final", "finished", "completed", "終了", "試合終了",
            }
            incoming_final = str(incoming.get("status") or "").lower() in {
                "final", "finished", "completed", "終了", "試合終了",
            }
            for key, value in incoming.items():
                if value not in (None, "", "--:--", "会場未定"):
                    if existing_final and not incoming_final and key in {
                        "status", "home_score", "away_score", "result_source",
                    }:
                        continue
                    existing[key] = value
    return merged


def attach_handicaps(games: list[dict], handicaps: list[dict]) -> list[dict]:
    output = [dict(game) for game in games]
    for game in output:
        row = next((item for item in handicaps if same_match(game, item)), None)
        if row:
            for key in ("home_handicap", "away_handicap", "handicap_source_url"):
                game[key] = row.get(key)
    return output
