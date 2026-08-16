from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urljoin
import json
import re
import urllib.request

from bs4 import BeautifulSoup


TEAMS = {
    "阪神", "巨人", "中日", "広島", "DeNA", "ヤクルト",
    "ソフトバンク", "ロッテ", "楽天", "日本ハム",
    "西武", "オリックス",
}

BASE_URL = "https://handenomori.com/jpb/{:%Y%m%d}/"

NPB_MONTH_URL = (
    "https://npb.jp/games/{year}/"
    "schedule_{month:02d}_detail.html"
)

OUTPUT = Path("/app/data/npb_today.json")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/151 Safari/537.36"
    )
}

JST = ZoneInfo("Asia/Tokyo")


TEAM_ALIASES = {
    "阪神": (
        "阪神",
        "阪神タイガース",
    ),
    "巨人": (
        "巨人",
        "読売ジャイアンツ",
        "読売巨人",
    ),
    "中日": (
        "中日",
        "中日ドラゴンズ",
    ),
    "広島": (
        "広島",
        "広島東洋カープ",
    ),
    "DeNA": (
        "DeNA",
        "横浜DeNAベイスターズ",
        "横浜ＤｅＮＡベイスターズ",
    ),
    "ヤクルト": (
        "ヤクルト",
        "東京ヤクルトスワローズ",
    ),
    "ソフトバンク": (
        "ソフトバンク",
        "福岡ソフトバンクホークス",
    ),
    "ロッテ": (
        "ロッテ",
        "千葉ロッテマリーンズ",
    ),
    "楽天": (
        "楽天",
        "東北楽天ゴールデンイーグルス",
    ),
    "日本ハム": (
        "日本ハム",
        "北海道日本ハムファイターズ",
    ),
    "西武": (
        "西武",
        "埼玉西武ライオンズ",
    ),
    "オリックス": (
        "オリックス",
        "オリックス・バファローズ",
        "オリックスバファローズ",
    ),
}


def clean(x):
    return re.sub(r"\s+", " ", str(x)).strip()


def normalize_team(text):
    value = clean(text)

    for short_name, aliases in TEAM_ALIASES.items():
        for alias in aliases:
            if alias in value:
                return short_name

    return None


def fetch_html(url):
    req = urllib.request.Request(
        url,
        headers=HEADERS,
    )

    return urllib.request.urlopen(
        req,
        timeout=15,
    ).read()


# =========================================================
# handenomori
# 基本カード、開始時間、球場を取得
# =========================================================
def fetch_handenomori(target_date):

    url = BASE_URL.format(target_date)

    html = fetch_html(url)

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    lines = [
        clean(x)
        for x in soup.get_text(
            "\n",
            strip=True,
        ).splitlines()
        if clean(x)
    ]

    now = datetime.now(JST)

    games = []

    for i in range(len(lines)):

        home = lines[i]

        if home not in TEAMS:
            continue

        if i < 2:
            continue

        game_time = lines[i - 2]
        venue = lines[i - 1]

        if not re.fullmatch(
            r"\d{1,2}:\d{2}",
            game_time,
        ):
            continue

        home_score = None
        away_score = None
        away = None

        # -----------------------------
        # スコア取得済み
        # -----------------------------
        if (
            i + 4 < len(lines)
            and lines[i + 1].isdigit()
            and lines[i + 2] == "-"
            and lines[i + 3].isdigit()
            and lines[i + 4] in TEAMS
        ):

            home_score = int(lines[i + 1])
            away_score = int(lines[i + 3])
            away = lines[i + 4]

            status = "final"

        # -----------------------------
        # スコアなし
        # -----------------------------
        elif (
            i + 2 < len(lines)
            and lines[i + 1] == "-"
            and lines[i + 2] in TEAMS
        ):

            away = lines[i + 2]

            try:
                hh, mm = map(
                    int,
                    game_time.split(":"),
                )

                game_dt = datetime(
                    target_date.year,
                    target_date.month,
                    target_date.day,
                    hh,
                    mm,
                    tzinfo=JST,
                )

                status = (
                    "scheduled"
                    if now < game_dt
                    else "live"
                )

            except Exception:
                status = "scheduled"

        else:
            continue

        games.append(
            {
                "date": target_date.isoformat(),
                "time": game_time,
                "status": status,
                "home": home,
                "away": away,
                "home_score": home_score,
                "away_score": away_score,
                "venue": venue,
                "source_url": url,
                "result_source": "handenomori",
            }
        )

    return games


# =========================================================
# NPB公式
# 当日の試合速報リンクを取得
# =========================================================
def fetch_npb_game_links(target_date):

    month_url = NPB_MONTH_URL.format(
        year=target_date.year,
        month=target_date.month,
    )

    html = fetch_html(month_url)

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    mmdd = target_date.strftime("%m%d")

    pattern = re.compile(
        rf"/scores/{target_date.year}/{mmdd}/[^/]+/?$"
    )

    urls = []

    for a in soup.find_all(
        "a",
        href=True,
    ):

        href = a.get("href", "")

        if not pattern.search(href):
            continue

        full_url = urljoin(
            "https://npb.jp",
            href,
        )

        if full_url not in urls:
            urls.append(full_url)

    return urls


# =========================================================
# NPB公式試合速報ページ
# チーム、状態、最終スコアを取得
# =========================================================
def parse_npb_game(url):

    html = fetch_html(url)

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    page_text = clean(
        soup.get_text(
            " ",
            strip=True,
        )
    )

    # -----------------------------
    # 対戦カード
    # -----------------------------
    home = None
    away = None

    title_candidates = []

    for tag in soup.find_all(
        ["h1", "h2", "h3", "h4"],
    ):
        text = clean(
            tag.get_text(
                " ",
                strip=True,
            )
        )

        if " vs " in text.lower():
            title_candidates.append(text)

    for text in title_candidates:

        m = re.search(
            r"(.+?)\s+vs\s+(.+?)(?:\s+\d+回戦|$)",
            text,
            flags=re.I,
        )

        if not m:
            continue

        left = normalize_team(m.group(1))
        right = normalize_team(m.group(2))

        if left and right:
            # NPBタイトルは HOME vs AWAY
            home = left
            away = right
            break

    # タイトルで取れない場合は本文から補助
    if not home or not away:

        found = []

        for short_name, aliases in TEAM_ALIASES.items():

            if any(
                alias in page_text
                for alias in aliases
            ):
                found.append(short_name)

        found = list(dict.fromkeys(found))

        if len(found) >= 2:
            home = found[0]
            away = found[1]

    # -----------------------------
    # ステータス
    # -----------------------------
    if "試合終了" in page_text:
        status = "final"
    elif (
        "試合中" in page_text
        or "回表" in page_text
        or "回裏" in page_text
    ):
        status = "live"
    else:
        status = "scheduled"

    # -----------------------------
    # スコア表を探す
    # -----------------------------
    scores = {}

    for table in soup.find_all("table"):

        rows = table.find_all("tr")

        if not rows:
            continue

        header_index = None
        total_index = None

        for idx, row in enumerate(rows):

            cells = [
                clean(x.get_text(" ", strip=True))
                for x in row.find_all(
                    ["th", "td"],
                )
            ]

            if "計" in cells:
                header_index = idx
                total_index = cells.index("計")
                break

        if (
            header_index is None
            or total_index is None
        ):
            continue

        for row in rows[
            header_index + 1:
            header_index + 4
        ]:

            cells = [
                clean(x.get_text(" ", strip=True))
                for x in row.find_all(
                    ["th", "td"],
                )
            ]

            if not cells:
                continue

            team = normalize_team(cells[0])

            if not team:
                continue

            # チーム名列の後にイニング列が並ぶため、
            # headerの「計」の位置に合わせる。
            if total_index >= len(cells):
                continue

            score_text = re.sub(
                r"[^\d]",
                "",
                cells[total_index],
            )

            if score_text.isdigit():
                scores[team] = int(score_text)

        if len(scores) >= 2:
            break

    # NPBページの表構造差を補助
    if (
        home
        and away
        and (
            home not in scores
            or away not in scores
        )
    ):

        for row in soup.find_all("tr"):

            cells = [
                clean(x.get_text(" ", strip=True))
                for x in row.find_all(
                    ["th", "td"],
                )
            ]

            if len(cells) < 10:
                continue

            team = normalize_team(cells[0])

            if team not in {
                home,
                away,
            }:
                continue

            numeric = [
                x
                for x in cells[1:]
                if re.fullmatch(
                    r"\d+|x|X|-",
                    x,
                )
            ]

            # 通常は9イニング後の「計」
            # 正規のheader解析を優先するため補助のみ
            if team not in scores:

                # 後ろ3列が 計/H/E である構造を利用
                tail_numbers = [
                    x
                    for x in cells[-3:]
                    if x.isdigit()
                ]

                if tail_numbers:
                    scores[team] = int(
                        tail_numbers[0]
                    )

    if not home or not away:
        return None

    return {
        "home": home,
        "away": away,
        "status": status,
        "home_score": scores.get(home),
        "away_score": scores.get(away),
        "source_url": url,
    }


def fetch_npb_official(target_date):

    results = []

    try:
        links = fetch_npb_game_links(
            target_date
        )

        print(
            "NPB OFFICIAL LINKS:",
            len(links),
        )

        for url in links:

            try:
                game = parse_npb_game(url)

                if game:
                    results.append(game)

            except Exception as e:
                print(
                    "NPB GAME PARSE ERROR:",
                    url,
                    repr(e),
                )

    except Exception as e:
        print(
            "NPB OFFICIAL ERROR:",
            repr(e),
        )

    return results


# =========================================================
# マージ
# NPB公式を優先
# =========================================================
def merge_official(
    base_games,
    official_games,
):

    official_map = {}

    for g in official_games:

        key = frozenset(
            (
                g.get("home"),
                g.get("away"),
            )
        )

        official_map[key] = g

    for game in base_games:

        key = frozenset(
            (
                game.get("home"),
                game.get("away"),
            )
        )

        official = official_map.get(key)

        if not official:
            continue

        official_status = official.get(
            "status"
        )

        official_home_score = official.get(
            "home_score"
        )

        official_away_score = official.get(
            "away_score"
        )

        # NPB公式のHOME/AWAYに揃える
        if (
            official.get("home")
            and official.get("away")
        ):
            game["home"] = official["home"]
            game["away"] = official["away"]

        # -----------------------------
        # 試合終了
        # -----------------------------
        if (
            official_status == "final"
            and official_home_score
            is not None
            and official_away_score
            is not None
        ):
            game["status"] = "final"

            game["home_score"] = (
                official_home_score
            )

            game["away_score"] = (
                official_away_score
            )

            game["result_source"] = (
                "NPB公式"
            )

            game["official_url"] = (
                official["source_url"]
            )

        # -----------------------------
        # LIVE
        # -----------------------------
        elif official_status == "live":

            game["status"] = "live"

            if (
                official_home_score
                is not None
            ):
                game["home_score"] = (
                    official_home_score
                )

            if (
                official_away_score
                is not None
            ):
                game["away_score"] = (
                    official_away_score
                )

            game["result_source"] = (
                "NPB公式"
            )

            game["official_url"] = (
                official["source_url"]
            )

    return base_games


# =========================================================
# MAIN
# =========================================================
now = datetime.now(JST)
today = now.date()

games = fetch_handenomori(today)

official_games = fetch_npb_official(
    today
)

games = merge_official(
    games,
    official_games,
)

OUTPUT.write_text(
    json.dumps(
        {
            "date": today.isoformat(),
            "updated_at": now.isoformat(
                timespec="seconds"
            ),
            "count": len(games),
            "games": games,
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)

print("DATE :", today)
print("GAMES:", len(games))
print("OUTPUT:", OUTPUT)

for g in games:

    if g["status"] == "final":

        display = (
            f'{g["away_score"]}'
            f' - '
            f'{g["home_score"]}'
        )

    elif g["status"] == "live":

        if (
            g["away_score"] is not None
            and g["home_score"] is not None
        ):
            display = (
                f'{g["away_score"]}'
                f' - '
                f'{g["home_score"]}'
            )
        else:
            display = "LIVE"

    else:
        display = g["time"]

    print(
        f'{g["away"]} '
        f'{display} '
        f'{g["home"]} '
        f'[{g["status"]}] '
        f'{g["venue"]} '
        f'[{g.get("result_source", "-")}]'
    )
