#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

JST = ZoneInfo("Asia/Tokyo")
STARTER_URL = "https://npb.jp/announcement/starter/"

TEAM_ALIASES = {
    "読売ジャイアンツ": "巨人",
    "阪神タイガース": "阪神",
    "横浜DeNAベイスターズ": "DeNA",
    "東京ヤクルトスワローズ": "ヤクルト",
    "広島東洋カープ": "広島",
    "中日ドラゴンズ": "中日",
    "福岡ソフトバンクホークス": "ソフトバンク",
    "北海道日本ハムファイターズ": "日本ハム",
    "千葉ロッテマリーンズ": "ロッテ",
    "東北楽天ゴールデンイーグルス": "楽天",
    "埼玉西武ライオンズ": "西武",
    "オリックス・バファローズ": "オリックス",
}
DATE_RE = re.compile(r"(?P<month>\d{1,2})月(?P<day>\d{1,2})日")


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\u3000", " ")).strip()


def fetch_starters() -> dict:
    response = requests.get(
        STARTER_URL,
        timeout=20,
        headers={
            "User-Agent": "AI-BASEBALL-STUDIO/1.0 (+official starter sync)",
            "Accept-Language": "ja,en;q=0.8",
        },
    )
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    soup = BeautifulSoup(response.text, "html.parser")

    heading = next(
        (
            tag for tag in soup.find_all(["h3", "h4", "h5"])
            if "日の予告先発投手" in clean(tag.get_text(" ", strip=True))
        ),
        None,
    )
    if heading is None:
        raise RuntimeError("NPB probable-starter heading was not found")

    heading_text = clean(heading.get_text(" ", strip=True))
    date_match = DATE_RE.search(heading_text)
    if not date_match:
        raise RuntimeError("NPB probable-starter date was not found")

    month = int(date_match.group("month"))
    day = int(date_match.group("day"))
    now = datetime.now(JST)
    year = now.year + (1 if now.month == 12 and month == 1 else 0)
    slate_date = f"{year:04d}-{month:02d}-{day:02d}"

    starters: dict[str, str] = {}
    for img in heading.find_all_next("img"):
        alt = clean(str(img.get("alt") or ""))
        team = next((short for full, short in TEAM_ALIASES.items() if full in alt), None)
        if not team or team in starters:
            continue

        player_link = img.find_next("a")
        while player_link is not None and not clean(player_link.get_text(" ", strip=True)):
            player_link = player_link.find_next("a")
        if player_link is None:
            continue
        pitcher = clean(player_link.get_text(" ", strip=True))
        if pitcher and pitcher not in TEAM_ALIASES:
            starters[team] = pitcher

    if not starters:
        raise RuntimeError("NPB probable-starter page returned no pitcher names")

    return {
        "date": slate_date,
        "updated_at": now.isoformat(timespec="seconds"),
        "source": "NPB公式 予告先発",
        "source_url": STARTER_URL,
        "starters": starters,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch NPB official probable starters")
    parser.add_argument("--output", default="data/npb_starters.json")
    args = parser.parse_args()

    payload = fetch_starters()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(output.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(output)
    print(json.dumps({"date": payload["date"], "count": len(payload["starters"]), "output": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
