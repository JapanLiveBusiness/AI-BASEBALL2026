import json
import math
from collections import deque
from pathlib import Path

P = Path("/app/data/hawks_log5_backtest.json")

data = json.loads(
    P.read_text(encoding="utf-8")
)

# 古い → 新しい
data = sorted(
    data,
    key=lambda g: g["date"]
)

recent = deque(maxlen=5)
results = []

momentum_table = {
    5: 5.0,
    4: 3.5,
    3: 1.5,
    2: -1.0,
    1: -3.0,
    0: -5.0,
}

for g in data:

    result = g.get("result")

    # 引き分けは確率評価から除外
    actual = (
        1 if result == "勝"
        else 0 if result == "敗"
        else None
    )

    base = float(
        g["log5_probability"]
    )

    # ------------------------------
    # HOME / AWAY
    # 過去実績差が小さいため弱め
    # ------------------------------
    venue_mod = (
        0.7
        if g.get("home")
        else -0.7
    )

    # ------------------------------
    # 直近5試合
    # ------------------------------
    recent_wins = sum(
        x == "勝"
        for x in recent
    )

    if len(recent) == 5:
        momentum_mod = (
            momentum_table[
                recent_wins
            ]
        )
    else:
        momentum_mod = 0.0

    # ------------------------------
    # 市場ハンディ
    #
    # いきなり×8は強すぎる可能性があるため
    # 今回は複数係数を同時比較
    # ------------------------------
    h = g.get("hawks_handicap")

    try:
        h = float(h)
    except (TypeError, ValueError):
        h = 0.0

    for handicap_weight in [
        0.0,
        2.0,
        4.0,
        6.0,
        8.0
    ]:

        handicap_mod = (
            h * handicap_weight
        )

        probability = (
            base
            + venue_mod
            + momentum_mod
            + handicap_mod
        )

        probability = max(
            0.5,
            min(99.5, probability)
        )

        results.append({
            "date": g["date"],
            "result": result,
            "actual": actual,
            "weight": handicap_weight,
            "probability": probability
        })

    recent.append(result)


print("===== LOG5 MODEL COMPARISON =====")
print()

for weight in [
    0.0,
    2.0,
    4.0,
    6.0,
    8.0
]:

    games = [
        g for g in results
        if g["weight"] == weight
        and g["actual"] is not None
    ]

    hits = 0
    brier = 0.0
    logloss = 0.0

    for g in games:

        p = (
            g["probability"]
            / 100.0
        )

        y = g["actual"]

        if (p >= 0.5) == bool(y):
            hits += 1

        brier += (
            p - y
        ) ** 2

        safe = max(
            0.001,
            min(0.999, p)
        )

        logloss += -(
            y * math.log(safe)
            + (1-y)
            * math.log(1-safe)
        )

    n = len(games)

    print(
        f"HANDICAP × {weight:.0f}",
        f"| 的中 {hits/n*100:5.1f}%",
        f"| Brier {brier/n:.4f}",
        f"| LogLoss {logloss/n:.4f}"
    )


# ==========================================
# Log5単体も評価
# ==========================================

games = [
    g for g in data
    if g.get("result") in (
        "勝",
        "敗"
    )
]

hits = 0
brier = 0.0
logloss = 0.0

for g in games:

    p = (
        float(
            g["log5_probability"]
        )
        / 100.0
    )

    y = (
        1
        if g["result"] == "勝"
        else 0
    )

    if (p >= 0.5) == bool(y):
        hits += 1

    brier += (
        p-y
    ) ** 2

    safe = max(
        0.001,
        min(0.999, p)
    )

    logloss += -(
        y * math.log(safe)
        + (1-y)
        * math.log(1-safe)
    )

n = len(games)

print()
print(
    "LOG5 ONLY",
    f"| 的中 {hits/n*100:5.1f}%",
    f"| Brier {brier/n:.4f}",
    f"| LogLoss {logloss/n:.4f}"
)
