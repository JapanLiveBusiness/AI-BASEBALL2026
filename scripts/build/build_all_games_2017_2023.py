import json
import re
import time
import urllib.request
from datetime import date, timedelta
from pathlib import Path

from bs4 import BeautifulSoup

START_DATE = date(2017, 1, 1)
END_DATE = date(2023, 12, 31)

OUTPUT = Path("data/all_games_2017_2023.json")

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

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    progress_path = OUTPUT.with_suffix(
        ".progress.json"
    )

    # 取得済み試合を復元
    if OUTPUT.exists():
        try:
            existing = json.loads(
                OUTPUT.read_text(
                    encoding="utf-8"
                )
            )
        except Exception:
            existing = []
    else:
        existing = []

    unique = {}

    for game in existing:
        key = (
            game["date"],
            game["home"],
            game["away"]
        )
        unique[key] = game

    # 取得済み日付を復元
    if progress_path.exists():
        try:
            completed_dates = set(
                json.loads(
                    progress_path.read_text(
                        encoding="utf-8"
                    )
                )
            )
        except Exception:
            completed_dates = set()
    else:
        completed_dates = set()

    print(
        "保存済み試合:",
        len(unique)
    )
    print(
        "処理済み日付:",
        len(completed_dates)
    )

    current = START_DATE
    errors = []

    while current <= END_DATE:

        date_text = current.isoformat()

        if date_text in completed_dates:
            current += timedelta(days=1)
            continue

        try:
            games = fetch(current)

            for game in games:
                key = (
                    game["date"],
                    game["home"],
                    game["away"]
                )
                unique[key] = game

            completed_dates.add(date_text)

            saved_games = sorted(
                unique.values(),
                key=lambda x: (
                    x["date"],
                    x["home"],
                    x["away"]
                )
            )

            # 1日ごとに途中保存
            OUTPUT.write_text(
                json.dumps(
                    saved_games,
                    ensure_ascii=False,
                    indent=2
                ),
                encoding="utf-8"
            )

            progress_path.write_text(
                json.dumps(
                    sorted(completed_dates),
                    ensure_ascii=False,
                    indent=2
                ),
                encoding="utf-8"
            )

            print(
                date_text,
                "取得:",
                len(games),
                "累計:",
                len(saved_games)
            )

        except Exception as exc:
            errors.append({
                "date": date_text,
                "error": str(exc)
            })

            print(
                date_text,
                "ERROR:",
                exc
            )

        current += timedelta(days=1)
        time.sleep(0.5)

    error_path = OUTPUT.with_suffix(
        ".errors.json"
    )

    error_path.write_text(
        json.dumps(
            errors,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print()
    print(
        "TOTAL GAMES:",
        len(unique)
    )
    print(
        "COMPLETED DATES:",
        len(completed_dates)
    )
    print(
        "ERRORS:",
        len(errors)
    )
    print(
        "OUTPUT:",
        OUTPUT
    )


if __name__ == "__main__":
    main()
