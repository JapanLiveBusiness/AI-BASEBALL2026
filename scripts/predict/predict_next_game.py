#!/usr/bin/env python3

import json
import re
import urllib.request
from pathlib import Path
from datetime import datetime, timedelta

HAWKS_DATA = Path("/opt/hawks-ai/data/hawks_games_context.json")
ALL_DATA = Path("/opt/hawks-ai/data/all_games_2024_2026.json")

with HAWKS_DATA.open(encoding="utf-8") as f:
    games = json.load(f)

with ALL_DATA.open(encoding="utf-8") as f:
    all_games = json.load(f)

games = sorted(games, key=lambda x: x["date"])
all_games = sorted(all_games, key=lambda x: x["date"])


def clean(s):
    return re.sub(r"<[^>]+>", "", s).strip()


def fetch_hawks_game(date):
    ymd = date.replace("-", "")
    url = f"https://handenomori.com/jpb/{ymd}/"

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    try:
        html = urllib.request.urlopen(
            req,
            timeout=20
        ).read().decode(
            "utf-8",
            errors="ignore"
        )
    except Exception:
        return None

    sections = re.findall(
        r'<div class="game-detail2">(.*?)</section>',
        html,
        re.S
    )

    for section in sections:

        teams = [
            clean(x)
            for x in re.findall(
                r'<div class="detail-card-team">\s*(.*?)\s*</div>',
                section,
                re.S
            )
        ]

        pitchers = [
            clean(x)
            for x in re.findall(
                r'<div class="detail-team-pitcher">\s*(.*?)\s*</div>',
                section,
                re.S
            )
        ]

        stadium = [
            clean(x)
            for x in re.findall(
                r'<div class="detail-single-studium-time">.*?'
                r'<span>.*?</span>\s*<span>(.*?)</span>',
                section,
                re.S
            )
        ]

        if "ソフトバンク" not in teams:
            continue

        if len(teams) < 2:
            continue

        if teams[0] == "ソフトバンク":
            home_away = "home"
            opponent = teams[1]
            hawks_starter = pitchers[0] if len(pitchers) >= 1 else None
            opponent_starter = pitchers[1] if len(pitchers) >= 2 else None
        else:
            home_away = "away"
            opponent = teams[0]
            hawks_starter = pitchers[1] if len(pitchers) >= 2 else None
            opponent_starter = pitchers[0] if len(pitchers) >= 1 else None

        return {
            "date": date,
            "opponent": opponent,
            "home_away": home_away,
            "hawks_starter": hawks_starter,
            "opponent_starter": opponent_starter,
            "stadium": stadium[0] if stadium else "不明",
            "source_url": url
        }

    return None


def team_history(team, before_date):
    rows = []

    for g in all_games:

        if g["date"] >= before_date:
            continue

        if g["home"] == team:
            rf = g["home_score"]
            ra = g["away_score"]

        elif g["away"] == team:
            rf = g["away_score"]
            ra = g["home_score"]

        else:
            continue

        result = (
            "win" if rf > ra
            else "loss" if rf < ra
            else "draw"
        )

        rows.append({
            "date": g["date"],
            "result": result,
            "run_diff": rf - ra
        })

    return rows


def recent5(team, date):
    hist = team_history(team, date)[-5:]

    if not hist:
        return {
            "win_pct": 0.5,
            "avg_run_diff": 0.0
        }

    decided = [
        x for x in hist
        if x["result"] != "draw"
    ]

    if decided:
        wins = sum(
            x["result"] == "win"
            for x in decided
        )
        pct = wins / len(decided)
    else:
        pct = 0.5

    return {
        "win_pct": pct,
        "avg_run_diff": sum(
            x["run_diff"]
            for x in hist
        ) / len(hist)
    }


def hawks_starter_history(starter, date):
    hist = [
        g for g in games
        if g["date"] < date
        and g.get("hawks_starter") == starter
        and g["result"] in {"win", "loss"}
    ]

    if not hist:
        return {
            "starts": 0,
            "win_pct": 0.5,
            "avg_run_diff": 0.0
        }

    wins = sum(
        g["result"] == "win"
        for g in hist
    )

    return {
        "starts": len(hist),
        "win_pct": wins / len(hist),
        "avg_run_diff": sum(
            g["run_diff"]
            for g in hist
        ) / len(hist)
    }


def opponent_starter_history(opponent, starter, date):
    hist = [
        g for g in games
        if g["date"] < date
        and g["opponent"] == opponent
        and g.get("opponent_starter") == starter
        and g["result"] in {"win", "loss"}
    ]

    if not hist:
        return {
            "starts": 0,
            "hawks_win_pct": 0.5,
            "avg_run_diff": 0.0
        }

    wins = sum(
        g["result"] == "win"
        for g in hist
    )

    return {
        "starts": len(hist),
        "hawks_win_pct": wins / len(hist),
        "avg_run_diff": sum(
            g["run_diff"]
            for g in hist
        ) / len(hist)
    }


# 最終データ翌日から次戦を探す
last_date = datetime.strptime(
    games[-1]["date"],
    "%Y-%m-%d"
)

next_game = None

for offset in range(1, 8):
    d = (
        last_date + timedelta(days=offset)
    ).strftime("%Y-%m-%d")

    x = fetch_hawks_game(d)

    if x:
        next_game = x
        break


if not next_game:
    print("NEXT HAWKS GAME NOT FOUND")
    raise SystemExit(1)


date = next_game["date"]
opponent = next_game["opponent"]

h5 = recent5(
    "ソフトバンク",
    date
)

o5 = recent5(
    opponent,
    date
)

hs = hawks_starter_history(
    next_game["hawks_starter"],
    date
)

os = opponent_starter_history(
    opponent,
    next_game["opponent_starter"],
    date
)


opp_starter_strength = (
    1.0 - os["hawks_win_pct"]
)

starter_adv = (
    hs["win_pct"]
    - os["hawks_win_pct"]
)

starter_rd_adv = (
    hs["avg_run_diff"]
    - os["avg_run_diff"]
)

rd5 = (
    h5["avg_run_diff"]
    - o5["avg_run_diff"]
)


p1 = (
    next_game["home_away"] == "away"
    and opp_starter_strength >= 0.60
    and starter_rd_adv < 0
)

p2 = (
    next_game["home_away"] == "away"
    and starter_rd_adv < 0
)

p3 = (
    opp_starter_strength >= 0.60
    and rd5 < 0
)

p7 = (
    starter_adv <= -0.20
    and rd5 < 0
)


probability = 0.634
risk = "通常"
icon = "🟢"

matched = []

if p1:
    matched.append("P1")

if p2:
    matched.append("P2")

if p3:
    matched.append("P3")

if p7:
    matched.append("P7")


if p3:
    probability = 0.42
    risk = "危険"
    icon = "🔴"

elif p1 or p7:
    probability = 0.50
    risk = "注意"
    icon = "🟡"

elif p2:
    probability = 0.56
    risk = "注意"
    icon = "🟡"


print("=" * 64)
print(" HAWKS AI - AUTO PREDICTION")
print(" Model: V8 FINAL")
print("=" * 64)

print()
print("試合日       :", date)
print("対戦相手     :", opponent)
print("開催         :", next_game["home_away"])
print("球場         :", next_game["stadium"])

print(
    "先発         :",
    next_game["hawks_starter"],
    "vs",
    next_game["opponent_starter"]
)

print()
print("勝利期待度   :", f"{probability:.1%}")
print("リスク判定   :", icon, risk)

print()
print("===== PRE-GAME DATA =====")

print(
    "Hawks直近5   :",
    f"{h5['win_pct']:.1%}",
    f"RD {h5['avg_run_diff']:+.2f}"
)

print(
    f"{opponent}直近5 :",
    f"{o5['win_pct']:.1%}",
    f"RD {o5['avg_run_diff']:+.2f}"
)

print(
    "直近5差      :",
    f"{rd5:+.2f}"
)

print()
print(
    "Hawks先発    :",
    next_game["hawks_starter"],
    f"{hs['starts']} starts",
    f"勝率 {hs['win_pct']:.1%}",
    f"RD {hs['avg_run_diff']:+.2f}"
)

print(
    "相手先発     :",
    next_game["opponent_starter"],
    f"{os['starts']} starts",
    f"Hawks勝率 {os['hawks_win_pct']:.1%}",
    f"RD {os['avg_run_diff']:+.2f}"
)

print()
print("===== V8 PATTERNS =====")

if matched:
    print(", ".join(matched))
else:
    print("該当なし")

print()
print("SOURCE:", next_game["source_url"])
print("=" * 64)
