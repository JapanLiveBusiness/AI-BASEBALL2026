import json
import re
import time
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup


DATA_FILE = Path("/app/data/historical_games.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def handicap_to_value(raw):
    """
    HAWKS AI分析用の連続値。

    通常値:
      0.3 -> 0.3
      0.9 -> 0.9
      1.5 -> 1.5
      2   -> 2.0

    「1半」系:
      1半  -> 1.50
      1半3 -> 1.65
      1半5 -> 1.75
      1半7 -> 1.85

    ※「1半3/5/7」はハンデの森の決済表を
      連続的な強さへ換算したHAWKS AI独自値。
    """

    if raw is None:
        return None

    s = str(raw).strip()

    # 通常の数値
    try:
        return float(s)
    except ValueError:
        pass

    # 1半 / 1半3 / 1半5 / 1半7
    m = re.fullmatch(r"(\d+)半([357])?", s)

    if m:
        base = float(m.group(1)) + 0.5
        suffix = m.group(2)

        if suffix is None:
            return base

        # 3 -> +0.15
        # 5 -> +0.25
        # 7 -> +0.35
        return base + (int(suffix) / 20.0)

    return None


def detect_handicap_side(url):
    """
    ページ内のソフトバンク戦を特定し、
    ハンデが HOME / AWAY どちらに記載されているか取得。
    """

    req = urllib.request.Request(
        url,
        headers=HEADERS
    )

    html = urllib.request.urlopen(
        req,
        timeout=12
    ).read()

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    text_lines = [
        re.sub(r"\s+", " ", x).strip()
        for x in soup.get_text("\n", strip=True).splitlines()
        if x.strip()
    ]

    # ソフトバンク戦がその日の何試合目かを特定
    hawks_index = None

    for i, line in enumerate(text_lines):
        if line == "ソフトバンク":
            hawks_index = i
            break

    if hawks_index is None:
        return None, None

    # 「予告先発」の出現数 = 試合順
    game_number = sum(
        1
        for x in text_lines[:hawks_index]
        if x == "予告先発"
    )

    tables = soup.find_all("table")

    if game_number >= len(tables):
        return None, None

    table = tables[game_number]

    rows = table.find_all("tr")

    if len(rows) < 2:
        return None, None

    cells = rows[-1].find_all(["td", "th"])

    if len(cells) < 2:
        return None, None

    home_value = cells[0].get_text(
        " ",
        strip=True
    )

    away_value = cells[1].get_text(
        " ",
        strip=True
    )

    if home_value:
        return "home", home_value

    if away_value:
        return "away", away_value

    return None, None


def main():
    if not DATA_FILE.exists():
        raise SystemExit(
            f"DATA_NOT_FOUND: {DATA_FILE}"
        )

    data = json.loads(
        DATA_FILE.read_text(
            encoding="utf-8"
        )
    )

    updated = 0
    failed = 0

    for n, game in enumerate(data, 1):

        raw = game.get("handicap_raw")
        url = game.get("source_url")

        value = handicap_to_value(raw)

        game["handicap_value"] = value

        side = None
        detected_raw = None

        try:
            side, detected_raw = detect_handicap_side(
                url
            )
        except Exception as e:
            print(
                "SIDE_ERROR",
                game.get("date"),
                repr(e)
            )

        if side:
            game["handicap_side"] = side

            # ページ上の値も保存
            game["handicap_detected_raw"] = (
                detected_raw
            )

            hawks_is_home = bool(
                game.get("home")
            )

            hawks_is_giver = (
                (side == "home" and hawks_is_home)
                or
                (side == "away" and not hawks_is_home)
            )

            game["hawks_is_handicap_giver"] = (
                hawks_is_giver
            )

            # HAWKS AIでは
            # マイナス = ホークスにハンディを課す
            # プラス   = 相手側にハンディ
            if value is not None:
                game["hawks_handicap"] = (
                    -value
                    if hawks_is_giver
                    else value
                )
            else:
                game["hawks_handicap"] = None

            updated += 1

        else:
            game["handicap_side"] = None
            game["hawks_is_handicap_giver"] = None
            game["hawks_handicap"] = None
            failed += 1

        print(
            f'{n:03d}',
            game.get("date"),
            game.get("opponent"),
            "RAW=",
            raw,
            "VALUE=",
            value,
            "SIDE=",
            side,
            "HAWKS=",
            game.get("hawks_handicap")
        )

        time.sleep(0.3)

    backup = DATA_FILE.with_name(
        "historical_games.before-handicap-values.json"
    )

    if not backup.exists():
        backup.write_text(
            DATA_FILE.read_text(
                encoding="utf-8"
            ),
            encoding="utf-8"
        )

    DATA_FILE.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print()
    print("TOTAL:", len(data))
    print("UPDATED:", updated)
    print("FAILED:", failed)
    print("OUTPUT:", DATA_FILE)


if __name__ == "__main__":
    main()
