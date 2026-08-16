import json
import math
from collections import deque
from itertools import product
from pathlib import Path

P = Path("/app/data/hawks_log5_backtest.json")

data = json.loads(P.read_text(encoding="utf-8"))
data = sorted(data, key=lambda g: g["date"])

momentum_table = {
    5: 5.0,
    4: 3.5,
    3: 1.5,
    2: -1.0,
    1: -3.0,
    0: -5.0,
}

recent = deque(maxlen=5)
rows = []

for g in data:

    result = g.get("result")

    if len(recent) == 5:
        recent_wins = sum(x == "勝" for x in recent)
        momentum = momentum_table[recent_wins]
    else:
        momentum = 0.0

    try:
        handicap = float(g.get("hawks_handicap", 0))
    except (TypeError, ValueError):
        handicap = 0.0

    if result in ("勝", "敗"):
        rows.append({
            "date": g["date"],
            "log5": float(g["log5_probability"]),
            "home": bool(g.get("home")),
            "momentum": momentum,
            "handicap": handicap,
            "actual": 1 if result == "勝" else 0,
        })

    recent.append(result)


# ==================================================
# 時系列分割
# 前70% = TRAIN
# 後30% = TEST
# ==================================================

split = int(len(rows) * 0.70)

train = rows[:split]
test = rows[split:]

print("TOTAL:", len(rows))
print("TRAIN:", len(train))
print(
    "TRAIN PERIOD:",
    train[0]["date"],
    "->",
    train[-1]["date"]
)

print("TEST:", len(test))
print(
    "TEST PERIOD:",
    test[0]["date"],
    "->",
    test[-1]["date"]
)


def evaluate(dataset, params):

    shrink, venue, momentum_weight, handicap_weight = params

    brier = 0.0
    logloss = 0.0
    hits = 0
    predictions = []

    for r in dataset:

        base = (
            50.0
            + (r["log5"] - 50.0) * shrink
        )

        venue_mod = (
            venue
            if r["home"]
            else -venue
        )

        momentum_mod = (
            r["momentum"]
            * momentum_weight
        )

        handicap_mod = (
            r["handicap"]
            * handicap_weight
        )

        pred = (
            base
            + venue_mod
            + momentum_mod
            + handicap_mod
        )

        pred = max(
            1.0,
            min(99.0, pred)
        )

        p = pred / 100.0
        y = r["actual"]

        brier += (p-y) ** 2

        safe = max(
            0.001,
            min(0.999, p)
        )

        logloss += -(
            y * math.log(safe)
            + (1-y) * math.log(1-safe)
        )

        if (p >= 0.5) == bool(y):
            hits += 1

        predictions.append(
            (pred, y)
        )

    n = len(dataset)

    return {
        "brier": brier / n,
        "logloss": logloss / n,
        "accuracy": hits / n,
        "predictions": predictions,
    }


# ==================================================
# TRAINだけで係数探索
# ==================================================

best = None
tested = 0

for params in product(

    [x/20 for x in range(0,21)],

    [x/4 for x in range(-4,9)],

    [x/10 for x in range(0,16)],

    [x/4 for x in range(-8,17)]
):

    tested += 1

    result = evaluate(
        train,
        params
    )

    if (
        best is None
        or result["brier"]
        < best["brier"]
    ):
        best = {
            **result,
            "params": params
        }


shrink, venue, momentum_weight, handicap_weight = best["params"]

print()
print("===== TRAIN BEST =====")

print(
    f"Log5Shrink={shrink:.2f}"
)

print(
    f"HOME={venue:+.2f}"
)

print(
    f"Momentum×{momentum_weight:.2f}"
)

print(
    f"Handicap×{handicap_weight:.2f}"
)

print(
    f'Brier={best["brier"]:.4f}'
)

print(
    f'Hit={best["accuracy"]*100:.1f}%'
)

print(
    f'LogLoss={best["logloss"]:.4f}'
)


# ==================================================
# 一度も学習に使っていないTESTへ適用
# ==================================================

test_result = evaluate(
    test,
    best["params"]
)

print()
print("===== OUT-OF-SAMPLE TEST =====")

print(
    f'Brier={test_result["brier"]:.4f}'
)

print(
    f'Hit={test_result["accuracy"]*100:.1f}%'
)

print(
    f'LogLoss={test_result["logloss"]:.4f}'
)


# ==================================================
# 基準モデル：常にTRAIN実勝率
# ==================================================

train_rate = (
    sum(r["actual"] for r in train)
    / len(train)
)

baseline_brier = sum(
    (train_rate - r["actual"]) ** 2
    for r in test
) / len(test)

baseline_hits = sum(
    (train_rate >= 0.5)
    == bool(r["actual"])
    for r in test
) / len(test)

print()
print("===== BASELINE =====")

print(
    f"TRAIN勝率={train_rate*100:.1f}%"
)

print(
    f"TEST Brier={baseline_brier:.4f}"
)

print(
    f"TEST Hit={baseline_hits*100:.1f}%"
)


print()
print("MODELS TESTED:", tested)
