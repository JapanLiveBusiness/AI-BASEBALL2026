#!/usr/bin/env python3

import json
import sys
from pathlib import Path
from datetime import datetime

DATA = Path("/opt/hawks-ai/data/hawks_games_context.json")
ALL_DATA = Path("/opt/hawks-ai/data/all_games_2024_2026.json")

if not DATA.exists():
    print("ERROR: data not found:", DATA)
    sys.exit(1)

if not ALL_DATA.exists():
    print("ERROR: all games data not found:", ALL_DATA)
    sys.exit(1)

with DATA.open(encoding="utf-8") as f:
    games = json.load(f)

with ALL_DATA.open(encoding="utf-8") as f:
    all_games = json.load(f)

games = sorted(games, key=lambda x: x["date"])
all_games = sorted(all_games, key=lambda x: x["date"])


def ask(prompt, default=None):
    if default is not None:
        value = input(f"{prompt} [{default}]: ").strip()
        return value if value else default
    return input(f"{prompt}: ").strip()


def normalize_home_away(value):
    value = value.lower().strip()

    if value in {"home", "h", "ホーム"}:
        return "home"

    if value in {"away", "a", "ビジター", "アウェイ"}:
        return "away"

    print("ERROR: home / away を入力してください")
    sys.exit(1)


def team_games_before(team, date):
    result = []

    # 全12球団2566試合から対象チームの直近成績を取得
    for g in all_games:
        if g["date"] >= date:
            continue

        if g["home"] == team:
            rf = g["home_score"]
            ra = g["away_score"]

        elif g["away"] == team:
            rf = g["away_score"]
            ra = g["home_score"]

        else:
            continue

        if rf > ra:
            result_text = "win"
        elif rf < ra:
            result_text = "loss"
        else:
            result_text = "draw"

        result.append({
            "date": g["date"],
            "runs_for": rf,
            "runs_against": ra,
            "run_diff": rf - ra,
            "result": result_text,
        })

    return result


def recent_stats(team, date, n):
    hist = team_games_before(team, date)[-n:]

    if not hist:
        return {
            "games": 0,
            "win_pct": 0.5,
            "avg_run_diff": 0.0,
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
        win_pct = wins / len(decided)
    else:
        win_pct = 0.5

    avg_rd = sum(
        x["run_diff"]
        for x in hist
    ) / len(hist)

    return {
        "games": len(hist),
        "win_pct": win_pct,
        "avg_run_diff": avg_rd,
    }


def starter_history_hawks(starter, date):
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
            "avg_run_diff": 0.0,
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
        ) / len(hist),
    }


def starter_history_opponent(opponent, starter, date):
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
            "avg_run_diff": 0.0,
        }

    hawks_wins = sum(
        g["result"] == "win"
        for g in hist
    )

    return {
        "starts": len(hist),
        "hawks_win_pct": hawks_wins / len(hist),
        "avg_run_diff": sum(
            g["run_diff"]
            for g in hist
        ) / len(hist),
    }


print("=" * 64)
print(" HAWKS AI - NEXT GAME PREDICTION")
print(" Model: V8 FINAL")
print("=" * 64)

print()
print("登録試合数 :", len(games))

if games:
    print("最終データ :", games[-1]["date"])

print()
print("===== NEXT GAME INPUT =====")

default_date = games[-1]["date"] if games else datetime.now().strftime("%Y-%m-%d")

date = ask("試合日 YYYY-MM-DD", default_date)
opponent = ask("対戦相手")
home_away = normalize_home_away(
    ask("home / away", "home")
)
hawks_starter = ask("ホークス先発")
opp_starter = ask("相手先発")


# --------------------------------------------------
# 試合前データ
# --------------------------------------------------

h5 = recent_stats(
    "ソフトバンク",
    date,
    5
)

o5 = recent_stats(
    opponent,
    date,
    5
)

hs = starter_history_hawks(
    hawks_starter,
    date
)

os = starter_history_opponent(
    opponent,
    opp_starter,
    date
)


# --------------------------------------------------
# V8 条件
# --------------------------------------------------

# 相手先発がホークス戦で強い
opp_starter_win_pct = (
    1.0 - os["hawks_win_pct"]
)

# ホークス先発 vs 相手先発の勝率差
starter_adv = (
    hs["win_pct"]
    - os["hawks_win_pct"]
)

# 先発時の得失点差
starter_rd_adv = (
    hs["avg_run_diff"]
    - os["avg_run_diff"]
)

rd5 = (
    h5["avg_run_diff"]
    - o5["avg_run_diff"]
)

p1 = (
    home_away == "away"
    and opp_starter_win_pct >= 0.60
    and starter_rd_adv < 0
)

p2 = (
    home_away == "away"
    and starter_rd_adv < 0
)

p3 = (
    opp_starter_win_pct >= 0.60
    and rd5 < 0
)

p7 = (
    starter_adv <= -0.20
    and rd5 < 0
)

matched = []

if p1:
    matched.append("P1: ビジター＋相手先発強＋先発得失点差不利")

if p2:
    matched.append("P2: ビジター＋先発得失点差不利")

if p3:
    matched.append("P3: 相手先発強＋直近5試合得失点差不利")

if p7:
    matched.append("P7: 先発勝率差-20%以上＋直近5試合不利")


# --------------------------------------------------
# V8 FINAL 判定
# --------------------------------------------------

probability = 0.634
risk = "通常"
risk_icon = "🟢"

if p3:
    probability = 0.42
    risk = "危険"
    risk_icon = "🔴"

elif p1:
    probability = 0.50
    risk = "注意"
    risk_icon = "🟡"

elif p7:
    probability = 0.50
    risk = "注意"
    risk_icon = "🟡"

elif p2:
    probability = 0.56
    risk = "注意"
    risk_icon = "🟡"


# --------------------------------------------------
# 表示
# --------------------------------------------------

print()
print("=" * 64)
print(" HAWKS AI PREDICTION")
print("=" * 64)

print()
print("試合日       :", date)
print("対戦相手     :", opponent)
print("開催         :", home_away)
print(
    "先発         :",
    hawks_starter,
    "vs",
    opp_starter
)

print()
print("勝利期待度   :", f"{probability:.1%}")
print(
    "リスク判定   :",
    risk_icon,
    risk
)

print()
print("===== PRE-GAME DATA =====")

print(
    "Hawks直近5   :",
    f"勝率 {h5['win_pct']:.1%}",
    f"得失点差 {h5['avg_run_diff']:+.2f}"
)

print(
    f"{opponent}直近5 :",
    f"勝率 {o5['win_pct']:.1%}",
    f"得失点差 {o5['avg_run_diff']:+.2f}"
)

print(
    "直近5差      :",
    f"{rd5:+.2f}"
)

print()
print(
    "Hawks先発履歴:",
    hawks_starter,
    f"{hs['starts']}試合",
    f"勝率 {hs['win_pct']:.1%}",
    f"平均得失点差 {hs['avg_run_diff']:+.2f}"
)

print(
    "相手先発履歴 :",
    opp_starter,
    f"{os['starts']}試合",
    f"ホークス勝率 {os['hawks_win_pct']:.1%}",
    f"平均得失点差 {os['avg_run_diff']:+.2f}"
)

print()
print("===== V8 RISK PATTERNS =====")

if matched:
    for x in matched:
        print("・", x)
else:
    print("該当なし")

print()
print("===== AI COMMENT =====")

if risk == "危険":
    print(
        "相手先発と直近チーム状態の組み合わせから、"
        "通常より敗戦リスクが高い試合です。"
    )

elif risk == "注意":
    print(
        "ホークス有利を基本としつつ、"
        "V8の危険条件が検出されています。"
    )

else:
    print(
        "V8の主要危険パターンには該当していません。"
        "基本勝率を基準にホークス有利判定です。"
    )

print()
print("=" * 64)
