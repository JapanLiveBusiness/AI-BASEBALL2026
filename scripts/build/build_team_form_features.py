import json
from pathlib import Path
from collections import defaultdict

ALL = Path("/opt/hawks-ai/data/all_games_2024_2026.json")
HAWKS = Path("/opt/hawks-ai/data/hawks_games_starter_history.json")
OUT = Path("/opt/hawks-ai/data/hawks_games_team_form.json")

with ALL.open(encoding="utf-8") as f:
    all_games = json.load(f)

with HAWKS.open(encoding="utf-8") as f:
    hawks_games = json.load(f)

all_games = sorted(all_games, key=lambda x: x["date"])


def team_view(game, team):

    if game["home"] == team:
        rf = game["home_score"]
        ra = game["away_score"]

    elif game["away"] == team:
        rf = game["away_score"]
        ra = game["home_score"]

    else:
        return None

    if rf > ra:
        result = "win"
    elif rf < ra:
        result = "loss"
    else:
        result = "draw"

    return {
        "date": game["date"],
        "runs_for": rf,
        "runs_against": ra,
        "run_diff": rf - ra,
        "result": result
    }


# 全12球団の履歴を作成
team_games = defaultdict(list)

for g in all_games:

    for team in (g["home"], g["away"]):

        x = team_view(g, team)

        if x:
            team_games[team].append(x)


def stats_before(team, date, n):

    history = [
        g for g in team_games[team]
        if g["date"] < date
    ]

    recent = history[-n:]

    if not recent:
        return {
            "games": 0,
            "win_pct": 0.5,
            "avg_runs_for": 0.0,
            "avg_runs_against": 0.0,
            "avg_run_diff": 0.0
        }

    decided = [
        g for g in recent
        if g["result"] != "draw"
    ]

    if decided:
        wins = sum(
            g["result"] == "win"
            for g in decided
        )
        pct = wins / len(decided)
    else:
        pct = 0.5

    return {
        "games": len(recent),

        "win_pct": round(
            pct,
            4
        ),

        "avg_runs_for": round(
            sum(g["runs_for"] for g in recent)
            / len(recent),
            3
        ),

        "avg_runs_against": round(
            sum(g["runs_against"] for g in recent)
            / len(recent),
            3
        ),

        "avg_run_diff": round(
            sum(g["run_diff"] for g in recent)
            / len(recent),
            3
        )
    }


output = []

for g in hawks_games:

    date = g["date"]
    opponent = g["opponent"]

    x = dict(g)

    x["team_form"] = {

        "hawks_recent5":
            stats_before(
                "ソフトバンク",
                date,
                5
            ),

        "hawks_recent10":
            stats_before(
                "ソフトバンク",
                date,
                10
            ),

        "opponent_recent5":
            stats_before(
                opponent,
                date,
                5
            ),

        "opponent_recent10":
            stats_before(
                opponent,
                date,
                10
            )
    }

    output.append(x)


with OUT.open(
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        output,
        f,
        ensure_ascii=False,
        indent=2
    )


print("===== TEAM FORM FEATURES =====")
print("TOTAL :", len(output))
print("OUTPUT:", OUT)

print("\n===== LAST 10 =====")

for g in output[-10:]:

    tf = g["team_form"]

    h5 = tf["hawks_recent5"]
    o5 = tf["opponent_recent5"]

    print(
        g["date"],
        g["opponent"],
        "| H5",
        f"{h5['win_pct']:.1%}",
        f"RD {h5['avg_run_diff']:+.2f}",
        "| O5",
        f"{o5['win_pct']:.1%}",
        f"RD {o5['avg_run_diff']:+.2f}",
        "| ADV",
        f"{h5['win_pct'] - o5['win_pct']:+.1%}"
    )
