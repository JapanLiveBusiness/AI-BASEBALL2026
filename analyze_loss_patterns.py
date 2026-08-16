import json
from pathlib import Path
from itertools import combinations

SRC = Path("/opt/hawks-ai/data/hawks_games_context.json")

with SRC.open(encoding="utf-8") as f:
    data = json.load(f)

games = [
    g for g in data
    if g["game_type"] in {"regular", "interleague"}
    and g["result"] in {"win", "loss"}
]

def conditions(g):
    sh = g["starter_history"]
    c = g["game_context"]

    return {
        "AWAY":
            g["home_away"] == "away",

        "HOME":
            g["home_away"] == "home",

        "VS_RAKUTEN":
            g["opponent"] == "楽天",

        "VS_NIPPONHAM":
            g["opponent"] == "日本ハム",

        "VS_SEIBU":
            g["opponent"] == "西武",

        "VS_LOTTE":
            g["opponent"] == "ロッテ",

        "VS_ORIX":
            g["opponent"] == "オリックス",

        # 相手先発が強い
        "OPP_STARTER_60":
            sh["opponent"]["win_pct"] >= 0.60,

        "OPP_STARTER_65":
            sh["opponent"]["win_pct"] >= 0.65,

        # ホークス先発不利
        "STARTER_ADV_NEG":
            sh["win_pct_diff"] < 0,

        "STARTER_ADV_MINUS20":
            sh["win_pct_diff"] <= -0.20,

        # 先発得失点差で不利
        "STARTER_RD_NEG":
            sh["run_diff_advantage"] < 0,

        # 連戦条件
        "HAWKS_CONSEC_3":
            c["hawks_consecutive_games"] >= 3,

        "HAWKS_CONSEC_4":
            c["hawks_consecutive_games"] >= 4,

        "CONSEC_DISADV":
            c["consecutive_advantage"] <= -2,

        # 休養不利
        "REST_DISADV":
            c["rest_advantage"] < 0,

        # 最近打っている
        "SCORE5_PLUS2":
            c["recent5_scoring_advantage"] >= 2,

        # 最近の得失点差
        "RD5_PLUS2":
            (
                c["hawks_recent5"]["avg_run_diff"]
                -
                c["opponent_recent5"]["avg_run_diff"]
            ) >= 2,

        "RD5_NEG":
            (
                c["hawks_recent5"]["avg_run_diff"]
                -
                c["opponent_recent5"]["avg_run_diff"]
            ) < 0,
    }


rows = [(g, conditions(g)) for g in games]


def evaluate(names):
    subset = [
        g for g, cond in rows
        if all(cond[n] for n in names)
    ]

    if len(subset) < 8:
        return None

    losses = sum(
        g["result"] == "loss"
        for g in subset
    )

    rate = losses / len(subset)

    return {
        "conditions": names,
        "games": len(subset),
        "losses": losses,
        "loss_rate": rate
    }


names = list(rows[0][1].keys())

results = []

# 単独
for n in names:
    r = evaluate((n,))
    if r:
        results.append(r)

# 2条件組み合わせ
for combo in combinations(names, 2):
    r = evaluate(combo)
    if r:
        results.append(r)

# 3条件組み合わせ
for combo in combinations(names, 3):
    r = evaluate(combo)
    if r:
        results.append(r)


results.sort(
    key=lambda x: (
        x["loss_rate"],
        x["games"]
    ),
    reverse=True
)

baseline = (
    sum(g["result"] == "loss" for g in games)
    / len(games)
)

print("===== LOSS PATTERN ANALYSIS =====")
print("TOTAL:", len(games))
print("BASE LOSS RATE:", f"{baseline:.1%}")

print("\n===== TOP LOSS PATTERNS =====")

shown = 0

for r in results:

    # ベースより最低10ポイント高いものだけ
    if r["loss_rate"] < baseline + 0.10:
        continue

    print(
        f"{r['loss_rate']:6.1%}",
        f"{r['losses']:3}/{r['games']:3}",
        " | ",
        " + ".join(r["conditions"])
    )

    shown += 1

    if shown >= 40:
        break


print("\n===== LARGE SAMPLE PATTERNS =====")

large = [
    r for r in results
    if r["games"] >= 20
]

large.sort(
    key=lambda x: x["loss_rate"],
    reverse=True
)

for r in large[:30]:
    print(
        f"{r['loss_rate']:6.1%}",
        f"{r['losses']:3}/{r['games']:3}",
        " | ",
        " + ".join(r["conditions"])
    )


print("\n===== RECENT LOSSES MATCH =====")

for g, cond in rows:

    if g["season"] != 2026:
        continue

    if g["result"] != "loss":
        continue

    active = [
        name
        for name, value in cond.items()
        if value
    ]

    print(
        g["date"],
        g["opponent"],
        "|",
        g["hawks_starter"],
        "vs",
        g["opponent_starter"],
        "|",
        ", ".join(active)
    )
