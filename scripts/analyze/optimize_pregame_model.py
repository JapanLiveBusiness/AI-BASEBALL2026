import json
from collections import deque
from itertools import product
from pathlib import Path

P = Path("/app/data/hawks_log5_backtest.json")

data = json.loads(
    P.read_text(encoding="utf-8")
)

data = sorted(data, key=lambda g: g["date"])

momentum_table = {
    5: 5.0,
    4: 3.5,
    3: 1.5,
    2: -1.0,
    1: -3.0,
    0: -5.0,
}

# --------------------------------------------------
# 各試合について「その試合前」のrecent5を一度だけ作る
# --------------------------------------------------

recent = deque(maxlen=5)
rows = []

for g in data:

    result = g.get("result")

    if len(recent) == 5:
        recent_wins = sum(
            x == "勝"
            for x in recent
        )
        momentum_raw = momentum_table[recent_wins]
    else:
        momentum_raw = 0.0

    h = g.get("hawks_handicap")

    try:
        h = float(h)
    except (TypeError, ValueError):
        h = 0.0

    if result in ("勝", "敗"):

        rows.append({
            "log5": float(
                g["log5_probability"]
            ),
            "home": bool(
                g.get("home")
            ),
            "momentum": momentum_raw,
            "handicap": h,
            "actual":
                1 if result == "勝" else 0,
        })

    recent.append(result)


# --------------------------------------------------
# グリッドサーチ
# --------------------------------------------------

results = []

shrink_values = [
    x / 20
    for x in range(0, 21)
]
# 0.00 ～ 1.00

venue_values = [
    x / 4
    for x in range(-4, 9)
]
# -1.00 ～ +2.00

momentum_weights = [
    x / 10
    for x in range(0, 16)
]
# 0.0 ～ 1.5

handicap_weights = [
    x / 4
    for x in range(-8, 17)
]
# -2.0 ～ +4.0


for (
    shrink,
    venue,
    momentum_weight,
    handicap_weight
) in product(
    shrink_values,
    venue_values,
    momentum_weights,
    handicap_weights
):

    brier = 0.0
    hits = 0

    for r in rows:

        # Log5を50%方向へ縮小
        base = (
            50.0
            + (
                r["log5"] - 50.0
            ) * shrink
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

        brier += (p - y) ** 2

        if (p >= 0.5) == bool(y):
            hits += 1

    n = len(rows)

    results.append({
        "brier": brier / n,
        "accuracy": hits / n,
        "shrink": shrink,
        "venue": venue,
        "momentum_weight":
            momentum_weight,
        "handicap_weight":
            handicap_weight,
    })


results.sort(
    key=lambda x: x["brier"]
)

print(
    "===== BEST 20 MODELS ====="
)

for i, r in enumerate(
    results[:20],
    1
):
    print(
        f'{i:2d}',
        f'Brier={r["brier"]:.4f}',
        f'Hit={r["accuracy"]*100:.1f}%',
        f'Log5Shrink={r["shrink"]:.2f}',
        f'HOME={r["venue"]:+.2f}',
        f'Momentum×{r["momentum_weight"]:.2f}',
        f'Handicap×{r["handicap_weight"]:.2f}'
    )

print()
print("TOTAL GAMES:", len(rows))
print(
    "MODELS TESTED:",
    len(results)
)
