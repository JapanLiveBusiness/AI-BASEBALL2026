import json
from pathlib import Path

SRC = Path("/opt/hawks-ai/data/hawks_games_context.json")

with SRC.open(encoding="utf-8") as f:
    data = json.load(f)

games = [
    g for g in data
    if g["game_type"] in {"regular", "interleague"}
    and g["result"] in {"win", "loss"}
]


def flags(g):
    sh = g["starter_history"]
    c = g["game_context"]

    rd5 = (
        c["hawks_recent5"]["avg_run_diff"]
        - c["opponent_recent5"]["avg_run_diff"]
    )

    return {
        "AWAY": g["home_away"] == "away",

        "VS_RAKUTEN": g["opponent"] == "楽天",
        "VS_NIPPONHAM": g["opponent"] == "日本ハム",
        "VS_SEIBU": g["opponent"] == "西武",
        "VS_LOTTE": g["opponent"] == "ロッテ",
        "VS_ORIX": g["opponent"] == "オリックス",

        "OPP_STARTER_60":
            sh["opponent"]["win_pct"] >= 0.60,

        "STARTER_ADV_NEG":
            sh["win_pct_diff"] < 0,

        "STARTER_ADV_MINUS20":
            sh["win_pct_diff"] <= -0.20,

        "STARTER_RD_NEG":
            sh["run_diff_advantage"] < 0,

        "RD5_NEG":
            rd5 < 0,

        "CONSEC_DISADV":
            c["consecutive_advantage"] <= -2,

        "REST_DISADV":
            c["rest_advantage"] < 0,
    }


# 過去分析でサンプル数が比較的大きかった候補だけ
PATTERNS = {
    "P1_AWAY_STRONG_OPP_BAD_STARTER":
        ["AWAY", "OPP_STARTER_60", "STARTER_RD_NEG"],

    "P2_AWAY_BAD_STARTER":
        ["AWAY", "STARTER_RD_NEG"],

    "P3_STRONG_OPP_RD5_NEG":
        ["OPP_STARTER_60", "RD5_NEG"],

    "P4_RAKUTEN_BAD_STARTER":
        ["VS_RAKUTEN", "STARTER_RD_NEG"],

    "P5_ORIX_BAD_STARTER":
        ["VS_ORIX", "STARTER_RD_NEG"],

    "P6_ORIX_STARTER_ADV_NEG":
        ["VS_ORIX", "STARTER_ADV_NEG"],

    "P7_STARTER_MINUS20_RD5_NEG":
        ["STARTER_ADV_MINUS20", "RD5_NEG"],
}


def matches(g, pattern):
    f = flags(g)
    return all(f[x] for x in pattern)


def evaluate(dataset, pattern):
    subset = [
        g for g in dataset
        if matches(g, pattern)
    ]

    if not subset:
        return {
            "games": 0,
            "losses": 0,
            "loss_rate": 0
        }

    losses = sum(
        g["result"] == "loss"
        for g in subset
    )

    return {
        "games": len(subset),
        "losses": losses,
        "loss_rate": losses / len(subset)
    }


train = [
    g for g in games
    if g["season"] in {2024, 2025}
]

test = [
    g for g in games
    if g["season"] == 2026
]


def baseline(dataset):
    losses = sum(
        g["result"] == "loss"
        for g in dataset
    )

    return losses / len(dataset)


print("===== LOSS PATTERN HOLDOUT TEST =====")

print(
    "TRAIN 2024-2025:",
    len(train),
    "baseline loss",
    f"{baseline(train):.1%}"
)

print(
    "TEST 2026      :",
    len(test),
    "baseline loss",
    f"{baseline(test):.1%}"
)


print("\n===== PATTERN VALIDATION =====")

valid_patterns = []

for name, pattern in PATTERNS.items():

    tr = evaluate(train, pattern)
    te = evaluate(test, pattern)

    lift_train = (
        tr["loss_rate"] - baseline(train)
    )

    lift_test = (
        te["loss_rate"] - baseline(test)
    )

    print()
    print(name)
    print("  RULE :", " + ".join(pattern))

    print(
        "  TRAIN:",
        f"{tr['losses']}/{tr['games']}",
        f"loss {tr['loss_rate']:.1%}",
        f"lift {lift_train:+.1%}"
    )

    print(
        "  TEST :",
        f"{te['losses']}/{te['games']}",
        f"loss {te['loss_rate']:.1%}",
        f"lift {lift_test:+.1%}"
    )

    # 最低8試合、2026でもベースより+5pt以上
    if (
        te["games"] >= 8
        and lift_test >= 0.05
    ):
        valid_patterns.append(
            (
                name,
                pattern,
                te["games"],
                te["loss_rate"],
                lift_test
            )
        )


print("\n===== VALIDATED PATTERNS =====")

if not valid_patterns:
    print("NONE")
else:
    valid_patterns.sort(
        key=lambda x: (
            x[4],
            x[2]
        ),
        reverse=True
    )

    for x in valid_patterns:
        print(
            x[0],
            "|",
            " + ".join(x[1]),
            "| games",
            x[2],
            "| loss",
            f"{x[3]:.1%}",
            "| lift",
            f"{x[4]:+.1%}"
        )


print("\n===== 2026 RISK SCORE TEST =====")

# 各条件1点。検証済みかどうかに関係なく
# 組み合わせ全体の傾向を見る。
risk_rows = []

for g in test:

    f = flags(g)

    score = 0

    if f["AWAY"]:
        score += 1

    if f["OPP_STARTER_60"]:
        score += 1

    if f["STARTER_ADV_NEG"]:
        score += 1

    if f["STARTER_RD_NEG"]:
        score += 1

    if f["RD5_NEG"]:
        score += 1

    if f["CONSEC_DISADV"]:
        score += 1

    if f["REST_DISADV"]:
        score += 1

    risk_rows.append(
        (score, g)
    )


for score in sorted(
    set(x[0] for x in risk_rows)
):

    subset = [
        g for s, g in risk_rows
        if s == score
    ]

    losses = sum(
        g["result"] == "loss"
        for g in subset
    )

    print(
        "RISK",
        score,
        "|",
        len(subset),
        "games",
        "|",
        losses,
        "losses",
        "| loss rate",
        f"{losses/len(subset):.1%}"
    )


print("\n===== RISK >= THRESHOLD =====")

for threshold in range(1, 6):

    subset = [
        g for score, g in risk_rows
        if score >= threshold
    ]

    if not subset:
        continue

    losses = sum(
        g["result"] == "loss"
        for g in subset
    )

    print(
        f"RISK >= {threshold}",
        "|",
        len(subset),
        "games",
        "|",
        losses,
        "losses",
        "| loss rate",
        f"{losses/len(subset):.1%}"
    )
