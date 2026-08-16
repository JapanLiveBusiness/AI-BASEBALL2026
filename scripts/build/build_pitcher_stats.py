import json
import re
import urllib.request
from pathlib import Path
from html import unescape

OUT = Path("/opt/hawks-ai/data/pitcher_stats_2024_2026.json")

TEAMS = {
    "ソフトバンク": "h",
    "日本ハム": "f",
    "オリックス": "b",
    "ロッテ": "m",
    "楽天": "e",
    "西武": "l",
    "巨人": "g",
    "阪神": "t",
    "中日": "d",
    "広島": "c",
    "DeNA": "db",
    "ヤクルト": "s",
}

YEARS = [2024, 2025, 2026]


def clean(x):
    x = re.sub(r"<br\s*/?>", " ", x, flags=re.I)
    x = re.sub(r"<[^>]+>", "", x)
    x = unescape(x)
    x = " ".join(x.split())

    # 左投手の * を除去
    x = x.lstrip("*").strip()

    # 全角スペースも通常スペースへ
    x = x.replace("\u3000", " ")

    # 連続スペース整理
    x = " ".join(x.split())

    return x


def ip_to_float(value):
    """
    NPB投球回表記
    182.2 = 182回2/3
    90.1  = 90回1/3
    63.2  = 63回2/3
    """
    value = str(value).strip()

    if not value:
        return 0.0

    if "." not in value:
        return float(value)

    whole, frac = value.split(".", 1)
    whole = int(whole)

    if frac == "1":
        return whole + 1 / 3

    if frac == "2":
        return whole + 2 / 3

    return float(value)


def safe_int(x):
    try:
        return int(str(x).replace(",", ""))
    except:
        return 0


def safe_float(x):
    try:
        return float(str(x).replace(",", ""))
    except:
        return 0.0


def normalize_row(vals):
    """
    NPB年度別HTML差異を24列へ正規化。

    2025/2026:
      24列
      選手名 index 0
      投球回 index 12

    2024:
      26列
      index 0 = 空セル
      index 1 = 選手名
      投球回 index 13 + index 14
    """

    # 2025 / 2026
    if len(vals) == 24:
        return vals

    # 2024
    if len(vals) == 26:
        # 先頭の空セルを削除
        vals = vals[1:]

        # 現在25列
        # index 12 = 投球回整数部
        # index 13 = ".1" / ".2" / ""
        ip_main = vals[12]
        ip_frac = vals[13]

        if ip_frac in {".1", ".2", ""}:
            ip = ip_main + ip_frac

            vals = (
                vals[:12]
                + [ip]
                + vals[14:]
            )

        if len(vals) == 24:
            return vals

    return None


def fetch(year, code):
    url = f"https://npb.jp/bis/{year}/stats/idp1_{code}.html"

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    return urllib.request.urlopen(
        req,
        timeout=30
    ).read().decode(
        "utf-8",
        errors="ignore"
    )


all_stats = []

for year in YEARS:

    print(f"\n===== {year} =====")

    for team, code in TEAMS.items():

        try:
            html = fetch(year, code)

        except Exception as e:
            print("ERROR:", year, team, e)
            continue

        table = re.search(
            r"<table.*?</table>",
            html,
            re.I | re.S
        )

        if not table:
            print("NO TABLE:", year, team)
            continue

        rows = re.findall(
            r"<tr.*?</tr>",
            table.group(0),
            re.I | re.S
        )

        count = 0
        skipped = 0

        for row in rows:

            cells = re.findall(
                r"<t[hd][^>]*>(.*?)</t[hd]>",
                row,
                re.I | re.S
            )

            vals = [clean(c) for c in cells]

            if not vals:
                continue

            # ヘッダー除外
            if vals[0] == "選手":
                continue

            vals = normalize_row(vals)

            if vals is None or len(vals) != 24:
                skipped += 1
                continue

            name = vals[0]

            if not name:
                continue

            appearances = safe_int(vals[1])
            wins = safe_int(vals[2])
            losses = safe_int(vals[3])

            ip_raw = vals[12]

            try:
                ip = ip_to_float(ip_raw)
            except:
                ip = 0.0

            hits = safe_int(vals[13])
            home_runs = safe_int(vals[14])
            walks = safe_int(vals[15])
            intentional_walks = safe_int(vals[16])
            hit_by_pitch = safe_int(vals[17])
            strikeouts = safe_int(vals[18])
            runs = safe_int(vals[21])
            earned_runs = safe_int(vals[22])
            era = safe_float(vals[23])

            if ip > 0:
                whip = (hits + walks) / ip
                k9 = strikeouts * 9 / ip
                bb9 = walks * 9 / ip
                hr9 = home_runs * 9 / ip
            else:
                whip = 0.0
                k9 = 0.0
                bb9 = 0.0
                hr9 = 0.0

            item = {
                "season": year,
                "team": team,
                "pitcher": name,

                "appearances": appearances,
                "wins": wins,
                "losses": losses,

                "innings_raw": ip_raw,
                "innings": round(ip, 3),

                "hits": hits,
                "home_runs": home_runs,
                "walks": walks,
                "intentional_walks": intentional_walks,
                "hit_by_pitch": hit_by_pitch,
                "strikeouts": strikeouts,

                "runs": runs,
                "earned_runs": earned_runs,

                "era": era,
                "whip": round(whip, 3),
                "k9": round(k9, 3),
                "bb9": round(bb9, 3),
                "hr9": round(hr9, 3),

                "source_url":
                    f"https://npb.jp/bis/{year}/stats/idp1_{code}.html"
            }

            all_stats.append(item)
            count += 1

        print(
            f"{team:8}",
            count,
            "pitchers",
            "| skipped:",
            skipped
        )


OUT.parent.mkdir(
    parents=True,
    exist_ok=True
)

with OUT.open(
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        all_stats,
        f,
        ensure_ascii=False,
        indent=2
    )


print()
print("===== COMPLETE =====")
print("TOTAL :", len(all_stats))
print("OUTPUT:", OUT)


print("\n===== YEAR COUNTS =====")

for year in YEARS:
    count = sum(
        1 for p in all_stats
        if p["season"] == year
    )

    print(year, ":", count)


print("\n===== 2024 HAWKS CHECK =====")

targets_2024 = {
    "有原 航平",
    "大津 亮介",
    "スチュワート・ジュニア",
    "大関 友久",
}

for p in all_stats:

    if (
        p["season"] == 2024
        and p["team"] == "ソフトバンク"
        and p["pitcher"] in targets_2024
    ):

        print(
            p["pitcher"],
            "ERA", p["era"],
            "WHIP", p["whip"],
            "K/9", p["k9"],
            "BB/9", p["bb9"],
            "IP", p["innings_raw"]
        )


print("\n===== 2026 HAWKS CHECK =====")

targets_2026 = {
    "上沢 直之",
    "大津 亮介",
    "モイネロ",
    "スチュワート・ジュニア",
}

for p in all_stats:

    if (
        p["season"] == 2026
        and p["team"] == "ソフトバンク"
        and p["pitcher"] in targets_2026
    ):

        print(
            p["pitcher"],
            "ERA", p["era"],
            "WHIP", p["whip"],
            "K/9", p["k9"],
            "BB/9", p["bb9"],
            "IP", p["innings_raw"]
        )
