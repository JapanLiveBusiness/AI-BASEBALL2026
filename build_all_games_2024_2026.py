import json
import re
import time
import urllib.request
from datetime import date, timedelta
from pathlib import Path

from bs4 import BeautifulSoup

START_DATE = date(2024, 3, 1)
END_DATE = date.today()

OUTPUT = Path("/app/data/all_games_2024_2026.json")

BASE_URL = "https://handenomori.com/jpb/{:%Y%m%d}/"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

TEAMS = {
    "ソフトバンク",
    "楽天",
    "西武",
    "日本ハム",
    "オリックス",
    "ロッテ",
    "巨人",
    "阪神",
    "DeNA",
    "広島",
    "ヤクルト",
    "中日",
}


def clean(x):
    return re.sub(
        r"\s+",
        " ",
        str(x)
    ).strip()


def fetch(target_date):

    url = BASE_URL.format(target_date)

    req = urllib.request.Request(
        url,
        headers=HEADERS
    )

    try:
        html = urllib.request.urlopen(
            req,
            timeout=12
        ).read()

    except Exception:
        return []

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    lines = [
        clean(x)
        for x in soup.get_text(
            "\n",
            strip=True
        ).splitlines()
        if clean(x)
    ]

    games = []

    # 基本構造
    #
    # 球場
    # HOME
    # 得点
    # -
    # 得点
    # AWAY

    for i in range(
        1,
        len(lines) - 4
    ):

        home = lines[i]

        if home not in TEAMS:
            continue

        if not lines[i + 1].isdigit():
            continue

        if lines[i + 2] != "-":
            continue

        if not lines[i + 3].isdigit():
            continue

        away = lines[i + 4]

        if away not in TEAMS:
            continue

        home_score = int(
            lines[i + 1]
        )

        away_score = int(
            lines[i + 3]
        )

        venue = lines[i - 1]

        games.append({
            "date":
                target_date.isoformat(),

            "home": home,
            "away": away,

            "home_score":
                home_score,

            "away_score":
                away_score,

            "venue": venue,

            "source_url": url,
        })

    return games


def main():

    all_games = []

    current = START_DATE

    while current <= END_DATE:

        games = fetch(current)

        if games:

            all_games.extend(
                games
            )

            print(
                current,
                len(games),
                "games"
            )

        current += timedelta(days=1)

        time.sleep(0.3)

    # 重複除去
    unique = {}

    for g in all_games:

        key = (
            g["date"],
            g["home"],
            g["away"]
        )

        unique[key] = g

    games = sorted(
        unique.values(),
        key=lambda x: (
            x["date"],
            x["home"]
        )
    )

    OUTPUT.write_text(
        json.dumps(
            games,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print()
    print(
        "TOTAL GAMES:",
        len(games)
    )

    print(
        "OUTPUT:",
        OUTPUT
    )


if __name__ == "__main__":
    main()
