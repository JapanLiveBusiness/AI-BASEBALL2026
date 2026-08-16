import json
import re
import time
import urllib.request
from pathlib import Path

SRC = Path("/opt/hawks-ai/data/hawks_games_enriched.json")
OUT = Path("/opt/hawks-ai/data/hawks_games_with_starters.json")

with SRC.open(encoding="utf-8") as f:
    games = json.load(f)

TEAM_RE = re.compile(
    r'<div class="detail-card-team">\s*(.*?)\s*</div>',
    re.S
)

PITCHER_RE = re.compile(
    r'<div class="detail-team-pitcher">\s*(.*?)\s*</div>',
    re.S
)

SECTION_RE = re.compile(
    r'<div class="game-detail2">(.*?)</section>',
    re.S
)

TAG_RE = re.compile(r"<[^>]+>")


def clean(s):
    s = TAG_RE.sub("", s)
    s = s.replace("&nbsp;", " ")
    return " ".join(s.split())


def fetch(date):
    url = f"https://handenomori.com/jpb/{date.replace('-', '')}/"

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    try:
        return urllib.request.urlopen(
            req,
            timeout=20
        ).read().decode(
            "utf-8",
            errors="ignore"
        )
    except Exception as e:
        print("FETCH ERROR:", date, e)
        return ""


# 同じ日の複数試合で何度もアクセスしない
dates = sorted(set(g["date"] for g in games))

starter_map = {}

print("DATES:", len(dates))

for num, date in enumerate(dates, 1):

    html = fetch(date)

    if not html:
        continue

    sections = SECTION_RE.findall(html)

    for section in sections:

        teams = [
            clean(x)
            for x in TEAM_RE.findall(section)
        ]

        pitchers = [
            clean(x)
            for x in PITCHER_RE.findall(section)
        ]

        if len(teams) < 2:
            continue

        home = teams[0]
        away = teams[1]

        home_pitcher = pitchers[0] if len(pitchers) >= 1 else None
        away_pitcher = pitchers[1] if len(pitchers) >= 2 else None

        starter_map[
            (date, home, away)
        ] = {
            "home_starter": home_pitcher,
            "away_starter": away_pitcher
        }

    if num % 25 == 0 or num == len(dates):
        print(
            f"{num}/{len(dates)}",
            "games found:",
            len(starter_map)
        )

    time.sleep(0.10)


output = []

found = 0
missing = 0

for g in games:

    x = dict(g)

    key = (
        g["date"],
        g["home"],
        g["away"]
    )

    starters = starter_map.get(key)

    if starters:

        home_starter = starters["home_starter"]
        away_starter = starters["away_starter"]

        x["home_starter"] = home_starter
        x["away_starter"] = away_starter

        if g["home"] == "ソフトバンク":
            x["hawks_starter"] = home_starter
            x["opponent_starter"] = away_starter
        else:
            x["hawks_starter"] = away_starter
            x["opponent_starter"] = home_starter

        if x["hawks_starter"] and x["opponent_starter"]:
            found += 1
        else:
            missing += 1

    else:
        x["home_starter"] = None
        x["away_starter"] = None
        x["hawks_starter"] = None
        x["opponent_starter"] = None
        missing += 1

    output.append(x)


with OUT.open("w", encoding="utf-8") as f:
    json.dump(
        output,
        f,
        ensure_ascii=False,
        indent=2
    )


print()
print("===== STARTER DATA =====")
print("TOTAL   :", len(output))
print("FOUND   :", found)
print("MISSING :", missing)
print("RATE    :", f"{found / len(output):.1%}")
print("OUTPUT  :", OUT)

print()
print("===== LAST 10 =====")

for g in output[-10:]:
    print(
        g["date"],
        g["opponent"],
        "| HAWKS:",
        g["hawks_starter"],
        "| OPP:",
        g["opponent_starter"]
    )
