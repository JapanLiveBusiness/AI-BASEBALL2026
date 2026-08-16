import json
from pathlib import Path
from collections import defaultdict

SRC = Path("/opt/hawks-ai/data/hawks_games_context.json")

VALID_TYPES = {"regular", "interleague"}

with SRC.open(encoding="utf-8") as f:
    data = json.load(f)

games = sorted(
    [
        g for g in data
        if g["game_type"] in VALID_TYPES
        and g["result"] in {"win", "loss"}
    ],
    key=lambda x: x["date"]
)


def avg(values):
    values = [x for x in values if x is not None]
    return sum(values) / len(values) if values else 0.0


def extract(g):
    sh = g["starter_history"]
    c = g["game_context"]

    hs = sh["hawks"]
    os = sh["opponent"]

    return {
        # 先発履歴
        "hawks_starter_win_pct": hs["win_pct"],
        "opp_starter_win_pct": os["win_pct"],
        "starter_win_pct_adv": sh["win_pct_diff"],

        "hawks_starter_recent3": hs["recent3_win_pct"],
        "opp_starter_recent3": os["recent3_win_pct"],
        "starter_recent3_adv": sh["recent3_diff"],

        "hawks_starter_run_diff": hs["avg_run_diff"],
        "opp_starter_run_diff": os["avg_run_diff"],
        "starter_run_diff_adv": sh["run_diff_advantage"],

        "hawks_starter_starts": hs["starts"],
        "opp_starter_starts": os["starts"],

        # 休養・連戦
        "hawks_rest_days": c["hawks_rest_days"],
        "opp_rest_days": c["opponent_rest_days"],
        "rest_advantage": c["rest_advantage"],

        "hawks_consecutive": c["hawks_consecutive_games"],
        "opp_consecutive": c["opponent_consecutive_games"],
        "consecutive_advantage": c["consecutive_advantage"],

        # 得点力
        "score_adv_3": c["recent3_scoring_advantage"],
        "score_adv_5": c["recent5_scoring_advantage"],
        "score_adv_10": c["recent10_scoring_advantage"],

        # 失点
        "allowed_adv_3": (
            c["opponent_recent3"]["avg_runs_against"]
            - c["hawks_recent3"]["avg_runs_against"]
        ),

        "allowed_adv_5": (
            c["opponent_recent5"]["avg_runs_against"]
            - c["hawks_recent5"]["avg_runs_against"]
        ),

        "allowed_adv_10": (
            c["opponent_recent10"]["avg_runs_against"]
            - c["hawks_recent10"]["avg_runs_against"]
        ),

        # 得失点差
        "run_diff_adv_3": (
            c["hawks_recent3"]["avg_run_diff"]
            - c["opponent_recent3"]["avg_run_diff"]
        ),

        "run_diff_adv_5": (
            c["hawks_recent5"]["avg_run_diff"]
            - c["opponent_recent5"]["avg_run_diff"]
        ),

        "run_diff_adv_10": (
            c["hawks_recent10"]["avg_run_diff"]
            - c["opponent_recent10"]["avg_run_diff"]
        ),

        "home": 1 if g["home_away"] == "home" else 0,
        "interleague": 1 if g["game_type"] == "interleague" else 0,
    }


rows = []

for g in games:
    rows.append({
        "game": g,
        "features": extract(g)
    })


wins = [x for x in rows if x["game"]["result"] == "win"]
losses = [x for x in rows if x["game"]["result"] == "loss"]

print("===== LOSS FACTOR ANALYSIS =====")
print("TOTAL :", len(rows))
print("WINS  :", len(wins))
print("LOSSES:", len(losses))
print("WIN % :", f"{len(wins)/len(rows):.1%}")


feature_names = list(rows[0]["features"].keys())

results = []

for name in feature_names:

    w = avg([
        x["features"][name]
        for x in wins
    ])

    l = avg([
        x["features"][name]
        for x in losses
    ])

    diff = w - l

    all_values = [
        x["features"][name]
        for x in rows
    ]

    lo = min(all_values)
    hi = max(all_values)
    spread = hi - lo

    normalized = (
        abs(diff) / spread
        if spread > 0 else 0
    )

    results.append({
        "name": name,
        "win_avg": w,
        "loss_avg": l,
        "diff": diff,
        "normalized": normalized
    })


results.sort(
    key=lambda x: x["normalized"],
    reverse=True
)


print("\n===== FACTOR RANKING =====")

for i, r in enumerate(results, 1):

    direction = (
        "WIN ↑"
        if r["diff"] > 0
        else "LOSS ↑"
    )

    print(
        f"{i:2}.",
        f"{r['name']:28}",
        f"WIN {r['win_avg']:+7.3f}",
        f"LOSS {r['loss_avg']:+7.3f}",
        f"DIFF {r['diff']:+7.3f}",
        direction
    )


print("\n===== OPPONENT LOSS RATE =====")

opp = defaultdict(
    lambda: {
        "games": 0,
        "losses": 0
    }
)

for g in games:

    s = opp[g["opponent"]]

    s["games"] += 1

    if g["result"] == "loss":
        s["losses"] += 1


for team, s in sorted(
    opp.items(),
    key=lambda x: (
        x[1]["losses"] / x[1]["games"]
    ),
    reverse=True
):

    rate = s["losses"] / s["games"]

    print(
        f"{team:8}",
        f"{s['games']:3}試合",
        f"{s['losses']:3}敗",
        f"敗戦率 {rate:.1%}"
    )


print("\n===== HOME / AWAY =====")

for ha in ["home", "away"]:

    subset = [
        g for g in games
        if g["home_away"] == ha
    ]

    loss = sum(
        g["result"] == "loss"
        for g in subset
    )

    print(
        ha.upper(),
        len(subset),
        "games",
        "losses",
        loss,
        "loss rate",
        f"{loss/len(subset):.1%}"
    )


print("\n===== RECENT 2026 LOSSES =====")

recent_losses = [
    g for g in games
    if g["season"] == 2026
    and g["result"] == "loss"
]

for g in recent_losses[-15:]:

    c = g["game_context"]
    sh = g["starter_history"]

    print(
        g["date"],
        g["opponent"],
        "|",
        g["hawks_starter"],
        "vs",
        g["opponent_starter"],
        "| starter adv",
        f"{sh['win_pct_diff']:+.1%}",
        "| score5",
        f"{c['recent5_scoring_advantage']:+.2f}",
        "| rest",
        c["rest_advantage"],
        "| consec",
        c["consecutive_advantage"]
    )
