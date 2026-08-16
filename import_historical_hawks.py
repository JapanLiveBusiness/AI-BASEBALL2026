import json
import re
import time
import urllib.request
from datetime import date, timedelta
from pathlib import Path

from bs4 import BeautifulSoup


START_DATE = date(2026, 8, 14)

# まずは2026年シーズン開始付近まで。
# 後で2025年以前へさらに延長可能。
END_DATE = date(2026, 3, 1)

OUTPUT = Path("/app/data/historical_games.json")
BASE_URL = "https://handenomori.com/jpb/{:%Y%m%d}/"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def clean(text):
    return re.sub(r"\s+", " ", str(text)).strip()


def fetch_day(target_date):
    url = BASE_URL.format(target_date)

    try:
        req = urllib.request.Request(
            url,
            headers=HEADERS
        )

        html = urllib.request.urlopen(
            req,
            timeout=12
        ).read()

    except Exception as e:
        return None, str(e)

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    title = soup.get_text(
        " ",
        strip=True
    )

    if "日本プロ野球過去データ" not in title:
        return None, "not_data_page"

    return soup, None


def parse_hawks_game(target_date, soup):
    text = soup.get_text(
        "\n",
        strip=True
    )

    lines = [
        clean(x)
        for x in text.splitlines()
        if clean(x)
    ]

    for i, line in enumerate(lines):

        if line != "ソフトバンク":
            continue

        # =============================================
        # ホーム
        #
        # ソフトバンク
        # 2
        # -
        # 5
        # 楽天
        # 大津 亮介
        # 予告先発
        # 藤井 聖
        # ホーム
        # ビジター
        # 1半5
        # =============================================
        if (
            i + 10 < len(lines)
            and lines[i + 2] == "-"
            and lines[i + 1].isdigit()
            and lines[i + 3].isdigit()
        ):
            home = True

            venue = (
                lines[i - 1]
                if i >= 1
                else "-"
            )

            start_time = (
                lines[i - 2]
                if i >= 2
                and re.fullmatch(
                    r"\d{1,2}:\d{2}",
                    lines[i - 2]
                )
                else "-"
            )

            hawks_score = int(
                lines[i + 1]
            )

            opponent_score = int(
                lines[i + 3]
            )

            opponent = lines[i + 4]

            hawks_starter = (
                lines[i + 5]
                if i + 5 < len(lines)
                else "-"
            )

            opponent_starter = (
                lines[i + 7]
                if i + 7 < len(lines)
                else "-"
            )

            handicap_raw = (
                lines[i + 10]
                if i + 10 < len(lines)
                else None
            )

        # =============================================
        # ビジター
        #
        # 例:
        # 相手
        # 3
        # -
        # 5
        # ソフトバンク
        # 相手先発
        # 予告先発
        # ホークス先発
        # ホーム
        # ビジター
        # ハンディ
        # =============================================
        elif (
            i >= 4
            and lines[i - 2] == "-"
            and lines[i - 3].isdigit()
            and lines[i - 1].isdigit()
        ):
            home = False

            opponent = lines[i - 4]

            opponent_score = int(
                lines[i - 3]
            )

            hawks_score = int(
                lines[i - 1]
            )

            venue = (
                lines[i - 5]
                if i >= 5
                else "-"
            )

            start_time = (
                lines[i - 6]
                if i >= 6
                and re.fullmatch(
                    r"\d{1,2}:\d{2}",
                    lines[i - 6]
                )
                else "-"
            )

            opponent_starter = (
                lines[i + 1]
                if i + 1 < len(lines)
                else "-"
            )

            hawks_starter = (
                lines[i + 3]
                if i + 3 < len(lines)
                else "-"
            )

            handicap_raw = (
                lines[i + 6]
                if i + 6 < len(lines)
                else None
            )

        else:
            continue

        if hawks_score > opponent_score:
            result = "勝"
        elif hawks_score < opponent_score:
            result = "敗"
        else:
            result = "分"

        return {
            "date": target_date.isoformat(),
            "source_url": BASE_URL.format(
                target_date
            ),
            "opponent": opponent,
            "home": home,
            "venue": venue,
            "start_time": start_time,
            "hawks_score": hawks_score,
            "opponent_score": opponent_score,
            "result": result,
            "hawks_starter": hawks_starter,
            "opponent_starter": opponent_starter,
            "handicap_raw": handicap_raw,
            "source": "handenomori",
        }

    return None


def main():
    existing = []

    if OUTPUT.exists():
        try:
            existing = json.loads(
                OUTPUT.read_text(
                    encoding="utf-8"
                )
            )
        except Exception:
            existing = []

    by_date = {
        x.get("date"): x
        for x in existing
        if x.get("date")
    }

    current = START_DATE

    found = 0
    checked = 0

    while current >= END_DATE:
        checked += 1

        soup, error = fetch_day(
            current
        )

        if soup:
            game = parse_hawks_game(
                current,
                soup
            )

            if game:
                by_date[
                    game["date"]
                ] = game

                found += 1

                print(
                    game["date"],
                    game["opponent"],
                    game["hawks_score"],
                    "-",
                    game["opponent_score"],
                    game["result"],
                    "HANDICAP=",
                    game["handicap_raw"]
                )

        current -= timedelta(days=1)

        # サイト負荷を抑える
        time.sleep(0.4)

    games = sorted(
        by_date.values(),
        key=lambda x: x["date"],
        reverse=True
    )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
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
        "CHECKED:",
        checked
    )

    print(
        "HAWKS GAMES:",
        len(games)
    )

    print(
        "NEW/FOUND:",
        found
    )

    print(
        "OUTPUT:",
        OUTPUT
    )


if __name__ == "__main__":
    main()
