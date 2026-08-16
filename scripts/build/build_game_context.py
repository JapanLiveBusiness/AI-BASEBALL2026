import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

ALL = Path("/opt/hawks-ai/data/all_games_2024_2026.json")
HAWKS = Path("/opt/hawks-ai/data/hawks_games_team_form.json")
OUT = Path("/opt/hawks-ai/data/hawks_games_context.json")

with ALL.open(encoding="utf-8") as f:
    all_games = json.load(f)

with HAWKS.open(encoding="utf-8") as f:
    hawks_games = json.load(f)

all_games = sorted(all_games, key=lambda x: x["date"])


def dt(s):
    return datetime.strptime(s, "%Y-%m-%d")


def team_view(g, team):
    if g["home"] == team:
        rf = g["home_score"]
        ra = g["away_score"]
    elif g["away"] == team:
        rf = g["away_score"]
        ra = g["home_score"]
    else:
        return None

    if rf > ra:
        result = "win"
    elif rf < ra:
        result = "loss"
    else:
        result = "draw"

    return {
        "date": g["date"],
        "runs_for": rf,
        "runs_against": ra,
        "run_diff": rf - ra,
        "result": result
    }


team_history = defaultdict(list)

for g in all_games:
    for team in (g["home"], g["away"]):
        x = team_view(g, team)
        if x:
            team_history[team].append(x)


def history_before(team, date):
    return [
        g for g in team_history[team]
        if g["date"] < date
    ]


def recent_stats(history, n):
    recent = history[-n:]

    if not recent:
        return {
            "games": 0,
            "avg_runs_for": 0.0,
            "avg_runs_against": 0.0,
            "avg_run_diff": 0.0
        }

    return {
        "games": len(recent),
        "avg_runs_for": round(
            sum(g["runs_for"] for g in recent) / len(recent), 3
        ),
        "avg_runs_against": round(
            sum(g["runs_against"] for g in recent) / len(recent), 3
        ),
        "avg_run_diff": round(
            sum(g["run_diff"] for g in recent) / len(recent), 3
        )
    }


def rest_days(history, date):
    if not history:
        return 7

    last = dt(history[-1]["date"])
    current = dt(date)

    gap = (current - last).days - 1

    return max(0, min(gap, 7))


def consecutive_games(history, date):
    if not history:
        return 0

    current = dt(date)
    count = 0
    expected = current

    for g in reversed(history):
        gd = dt(g["date"])

        if (expected - gd).days == 1:
            count += 1
            expected = gd
        else:
            break

    return count


output = []

for g in hawks_games:
    date = g["date"]
    opponent = g["opponent"]

    hh = history_before("ソフトバンク", date)
    oh = history_before(opponent, date)

    h3 = recent_stats(hh, 3)
    h5 = recent_stats(hh, 5)
    h10 = recent_stats(hh, 10)

    o3 = recent_stats(oh, 3)
    o5 = recent_stats(oh, 5)
    o10 = recent_stats(oh, 10)

    x = dict(g)

    x["game_context"] = {
        "hawks_rest_days": rest_days(hh, date),
        "opponent_rest_days": rest_days(oh, date),

        "hawks_consecutive_games": consecutive_games(hh, date),
        "opponent_consecutive_games": consecutive_games(oh, date),

        "hawks_recent3": h3,
        "hawks_recent5": h5,
        "hawks_recent10": h10,

        "opponent_recent3": o3,
        "opponent_recent5": o5,
        "opponent_recent10": o10,

        "rest_advantage": (
            rest_days(hh, date)
            - rest_days(oh, date)
        ),

        "consecutive_advantage": (
            consecutive_games(oh, date)
            - consecutive_games(hh, date)
        ),

        "recent3_scoring_advantage": round(
            h3["avg_runs_for"]
            - o3["avg_runs_for"],
            3
        ),

        "recent5_scoring_advantage": round(
            h5["avg_runs_for"]
            - o5["avg_runs_for"],
            3
        ),

        "recent10_scoring_advantage": round(
            h10["avg_runs_for"]
            - o10["avg_runs_for"],
            3
        )
    }

    output.append(x)


with OUT.open("w", encoding="utf-8") as f:
    json.dump(
        output,
        f,
        ensure_ascii=False,
        indent=2
    )


print("===== GAME CONTEXT =====")
print("TOTAL :", len(output))
print("OUTPUT:", OUT)

print("\n===== LAST 10 =====")

for g in output[-10:]:
    c = g["game_context"]

    print(
        g["date"],
        g["opponent"],
        "| REST",
        c["hawks_rest_days"],
        "-",
        c["opponent_rest_days"],
        "| CONSEC",
        c["hawks_consecutive_games"],
        "-",
        c["opponent_consecutive_games"],
        "| R3 SCORE ADV",
        f"{c['recent3_scoring_advantage']:+.2f}",
        "| R5 SCORE ADV",
        f"{c['recent5_scoring_advantage']:+.2f}"
    )
