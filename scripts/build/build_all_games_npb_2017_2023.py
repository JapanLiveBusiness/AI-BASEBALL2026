#!/usr/bin/env python3
"""Collect 2017-2023 NPB first-team results from official NPB calendars."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

START_YEAR = 2017
END_YEAR = 2023
OUTPUT = Path("data/all_games_2017_2023.json")
PROGRESS = Path("data/all_games_2017_2023.npb_progress.json")
ERRORS = Path("data/all_games_2017_2023.npb_errors.json")
SLEEP_SECONDS = 0.35

TEAM_ALIASES = {
    "読売ジャイアンツ": "巨人", "読売": "巨人",
    "東京ヤクルトスワローズ": "ヤクルト", "東京ヤクルト": "ヤクルト",
    "横浜DeNAベイスターズ": "DeNA", "横浜DeNA": "DeNA",
    "中日ドラゴンズ": "中日", "阪神タイガース": "阪神",
    "広島東洋カープ": "広島", "北海道日本ハムファイターズ": "日本ハム",
    "北海道日本ハム": "日本ハム", "東北楽天ゴールデンイーグルス": "楽天",
    "東北楽天": "楽天", "埼玉西武ライオンズ": "西武", "埼玉西武": "西武",
    "千葉ロッテマリーンズ": "ロッテ", "千葉ロッテ": "ロッテ",
    "オリックス・バファローズ": "オリックス", "オリックス": "オリックス",
    "福岡ソフトバンクホークス": "ソフトバンク", "福岡ソフトバンク": "ソフトバンク",
    "巨人": "巨人", "ヤクルト": "ヤクルト", "DeNA": "DeNA",
    "中日": "中日", "阪神": "阪神", "広島": "広島",
    "日本ハム": "日本ハム", "楽天": "楽天", "西武": "西武",
    "ロッテ": "ロッテ", "ソフトバンク": "ソフトバンク",
}
OFFICIAL_TEAMS = set(TEAM_ALIASES.values())


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def get(session: requests.Session, url: str) -> str:
    last = None
    for attempt in range(3):
        try:
            response = session.get(url, timeout=30)
            response.raise_for_status()
            response.encoding = "utf-8"
            return response.text
        except Exception as exc:
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"{url}: {last}")


def normalize_team(value: str) -> str | None:
    clean = re.sub(r"\s+", "", value)
    for alias in sorted(TEAM_ALIASES, key=len, reverse=True):
        if re.sub(r"\s+", "", alias) in clean:
            return TEAM_ALIASES[alias]
    return None


def calendar_links(session: requests.Session):
    found = {}
    for year in range(START_YEAR, END_YEAR + 1):
        for month in range(3, 12):
            suffix = "" if month == 11 else f"index_{month:02d}.html"
            url = f"https://npb.jp/bis/{year}/calendar/{suffix}"
            try:
                html = get(session, url)
            except RuntimeError as exc:
                if "404 Client Error" in str(exc):
                    print(
                        f"CALENDAR {year}-{month:02d}: "
                        f"ページなし・スキップ",
                        flush=True,
                    )
                    continue
                raise

            soup = BeautifulSoup(html, "html.parser")
            count = 0
            for link in soup.select("a[href]"):
                href = link.get("href", "")
                if not re.search(r"(?:^|/)games/s\d+\.html$", href):
                    continue
                absolute = urljoin(url, href)
                text = link.get_text(" ", strip=True)
                score = re.search(r"(\d+)\s*-\s*(\d+)", text)
                if not score:
                    continue
                found[absolute] = {
                    "home_score": int(score.group(1)),
                    "away_score": int(score.group(2)),
                }
                count += 1
            print(f"CALENDAR {year}-{month:02d}: {count} links / unique {len(found)}", flush=True)
            time.sleep(SLEEP_SECONDS)
    return found


def parse_detail(html: str, url: str, score: dict):
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    match = re.search(r"試合結果\s*[（(](.+?)\s*vs\s*(.+?)[）)]", title)
    if not match:
        raise ValueError(f"対戦球団をタイトルから解析できません: {title}")
    home = normalize_team(match.group(1))
    away = normalize_team(match.group(2))
    if home not in OFFICIAL_TEAMS or away not in OFFICIAL_TEAMS or home == away:
        return None

    date_match = re.search(r"/s(\d{4})(\d{2})(\d{2})\d*\.html", url)
    if not date_match:
        raise ValueError("URLから試合日を解析できません")
    game_date = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"

    page_text = " ".join(soup.stripped_strings)
    venue = ""
    venue_match = re.search(
        rf"{re.escape(match.group(1))}\s+{score['home_score']}\s+"
        rf"{re.escape(match.group(2))}\s+{score['away_score']}\s+(.+?)\s+試合時間",
        page_text,
    )
    if venue_match:
        venue = venue_match.group(1).strip()
    else:
        generic = re.search(r"([^\s]{1,30}(?:ドーム|球場|スタジアム|神宮|甲子園|マツダ|ほっと神戸|ZOZOマリン))\s+試合時間", page_text)
        if generic:
            venue = generic.group(1).strip()

    # 試合種別は本文・ナビゲーションではなくタイトルだけで判定する。
    # 本文には他大会へのリンクが含まれるため誤分類の原因になる。
    game_type = "regular"
    if "日本シリーズ" in title:
        game_type = "japan_series"
    elif "クライマックス" in title:
        game_type = "climax"
    elif "セ・パ交流戦" in title or "交流戦" in title:
        game_type = "interleague"
    elif "オープン戦" in title:
        game_type = "preseason"
    elif "オールスター" in title:
        game_type = "all_star"

    return {
        "date": game_date,
        "home": home,
        "away": away,
        "home_score": score["home_score"],
        "away_score": score["away_score"],
        "venue": venue,
        "game_type": game_type,
        "source_url": url,
    }


def main():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 BASEBALL-AI-NEXT/1.0"})
    links = calendar_links(session)
    games = load_json(OUTPUT, [])
    done = set(load_json(PROGRESS, []))
    errors = load_json(ERRORS, [])
    unique = {(g["date"], g["home"], g["away"]): g for g in games}
    total = len(links)
    for index, (url, score) in enumerate(sorted(links.items()), 1):
        if url in done:
            continue
        try:
            game = parse_detail(get(session, url), url, score)
            if game:
                unique[(game["date"], game["home"], game["away"])] = game
            done.add(url)
            ordered = sorted(unique.values(), key=lambda x: (x["date"], x["home"], x["away"]))
            save_json(OUTPUT, ordered)
            save_json(PROGRESS, sorted(done))
            print(f"{index}/{total} {game['date'] if game else '-'} total={len(ordered)}", flush=True)
        except Exception as exc:
            errors.append({"url": url, "error": str(exc)})
            save_json(ERRORS, errors)
            print(f"ERROR {index}/{total} {url}: {exc}", flush=True)
        time.sleep(SLEEP_SECONDS)
    save_json(ERRORS, errors)
    print(f"DONE games={len(unique)} processed={len(done)} errors={len(errors)}", flush=True)


if __name__ == "__main__":
    main()
