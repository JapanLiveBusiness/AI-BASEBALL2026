import json
import math
from pathlib import Path

SRC = Path("/opt/hawks-ai/data/hawks_games_starter_history.json")
OUT = Path("/opt/hawks-ai/data/hawks_backtest_v4.json")

VALID_TYPES = {"regular", "interleague"}

with SRC.open(encoding="utf-8") as f:
    all_games = json.load(f)

games = sorted(
    [
        g for g in all_games
        if g["game_type"] in VALID_TYPES
        and g["result"] != "draw"
    ],
    key=lambda x: x["date"]
)


def win_pct(items):
    if not items:
        return 0.5

    wins = sum(
        g["result"] == "win"
        for g in items
    )

    return wins / len(items)


def avg_diff(items):
    if not items:
        return 0.0

    return sum(
        g["run_diff"]
        for g in items
    ) / len(items)


def shrink(pct, n, prior=0.5, strength=8):
    """
    少数サンプルを0.5へ縮小。
    n=1の100%などをそのまま使わない。
    """
    return (
        pct * n + prior * strength
    ) / (
        n + strength
    )


def sigmoid(z):
    z = max(-35, min(35, z))
    return 1 / (1 + math.exp(-z))


def build_features(history, game):

    recent5 = history[-5:]
    recent10 = history[-10:]
    recent20 = history[-20:]

    opp = [
        g for g in history
        if g["opponent"] == game["opponent"]
    ]

    ha = [
        g for g in history
        if g["home_away"] == game["home_away"]
    ]

    season = [
        g for g in history
        if g["season"] == game["season"]
    ]

    sh = game["starter_history"]

    hs = sh["hawks"]
    os = sh["opponent"]

    h_starter = shrink(
        hs["win_pct"],
        hs["starts"]
    )

    o_starter = shrink(
        os["win_pct"],
        os["starts"]
    )

    h_recent = shrink(
        hs["recent3_win_pct"],
        min(hs["starts"], 3),
        strength=4
    )

    o_recent = shrink(
        os["recent3_win_pct"],
        min(os["starts"], 3),
        strength=4
    )

    starter_adv = h_starter - o_starter
    starter_recent_adv = h_recent - o_recent

    starter_run_adv = max(
        -5,
        min(
            5,
            sh["run_diff_advantage"]
        )
    ) / 5

    return [
        1.0,

        win_pct(recent5) - 0.5,
        win_pct(recent10) - 0.5,
        win_pct(recent20) - 0.5,

        win_pct(opp) - 0.5,
        win_pct(ha) - 0.5,
        win_pct(season) - 0.5,

        max(-5, min(5, avg_diff(recent5))) / 5,
        max(-5, min(5, avg_diff(recent10))) / 5,

        1.0 if game["home_away"] == "home" else 0.0,
        1.0 if game["game_type"] == "interleague" else 0.0,

        starter_adv,
        starter_recent_adv,
        starter_run_adv,

        min(hs["starts"], 30) / 30,
        min(os["starts"], 30) / 30,
    ]


def train(X, y, epochs=250, lr=0.08, l2=0.05):

    nf = len(X[0])
    w = [0.0] * nf

    for _ in range(epochs):

        grad = [0.0] * nf

        for xi, yi in zip(X, y):

            z = sum(
                a * b
                for a, b in zip(w, xi)
            )

            p = sigmoid(z)
            err = p - yi

            for j in range(nf):
                grad[j] += err * xi[j]

        n = len(X)

        for j in range(nf):

            grad[j] /= n

            if j != 0:
                grad[j] += l2 * w[j]

            w[j] -= lr * grad[j]

    return w


predictions = []

# v2/v3と同じ100試合後から評価
for i in range(100, len(games)):

    train_games = games[:i]
    test = games[i]

    X = []
    y = []

    for j in range(30, len(train_games)):

        hist = train_games[:j]
        target = train_games[j]

        X.append(
            build_features(
                hist,
                target
            )
        )

        y.append(
            1 if target["result"] == "win"
            else 0
        )

    if len(X) < 30:
        continue

    w = train(X, y)

    xt = build_features(
        train_games,
        test
    )

    probability = sigmoid(
        sum(
            a * b
            for a, b in zip(w, xt)
        )
    )

    predicted = (
        "win"
        if probability >= 0.5
        else "loss"
    )

    predictions.append({
        "date": test["date"],
        "opponent": test["opponent"],
        "hawks_starter": test["hawks_starter"],
        "opponent_starter": test["opponent_starter"],
        "home_away": test["home_away"],
        "probability": round(probability, 4),
        "predicted": predicted,
        "actual": test["result"],
        "correct": predicted == test["result"]
    })


total = len(predictions)

correct = sum(
    p["correct"]
    for p in predictions
)

accuracy = (
    correct / total
    if total else 0
)

always = sum(
    p["actual"] == "win"
    for p in predictions
)

always_acc = (
    always / total
    if total else 0
)

loss_predictions = [
    p for p in predictions
    if p["predicted"] == "loss"
]

loss_hits = sum(
    p["actual"] == "loss"
    for p in loss_predictions
)

loss_precision = (
    loss_hits / len(loss_predictions)
    if loss_predictions
    else 0
)

brier = (
    sum(
        (
            p["probability"] -
            (
                1
                if p["actual"] == "win"
                else 0
            )
        ) ** 2
        for p in predictions
    ) / total
    if total else 0
)


result = {
    "model": "hawks_v4_starter_history",
    "predictions": total,
    "correct": correct,
    "accuracy": round(accuracy, 4),
    "always_win_accuracy": round(always_acc, 4),
    "improvement": round(
        accuracy - always_acc,
        4
    ),
    "loss_predictions": len(loss_predictions),
    "loss_hits": loss_hits,
    "loss_precision": round(
        loss_precision,
        4
    ),
    "brier_score": round(brier, 4),
    "results": predictions
}


with OUT.open(
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        result,
        f,
        ensure_ascii=False,
        indent=2
    )


print("===== HAWKS MODEL V4 =====")

print("PREDICTIONS      :", total)
print("CORRECT          :", correct)
print("V4 ACCURACY      :", f"{accuracy:.2%}")
print("ALWAYS WIN       :", f"{always_acc:.2%}")
print(
    "IMPROVEMENT      :",
    f"{accuracy-always_acc:+.2%}"
)

print(
    "LOSS PREDICTIONS :",
    len(loss_predictions)
)

print("LOSS HITS        :", loss_hits)

print(
    "LOSS PRECISION   :",
    f"{loss_precision:.2%}"
)

print(
    "BRIER SCORE      :",
    f"{brier:.4f}"
)

print("OUTPUT           :", OUT)


print("\n===== LAST 10 =====")

for p in predictions[-10:]:

    mark = (
        "○"
        if p["correct"]
        else "×"
    )

    print(
        p["date"],
        p["hawks_starter"],
        "vs",
        p["opponent_starter"],
        "|",
        f"{p['probability']:.1%}",
        p["predicted"],
        "| actual:",
        p["actual"],
        mark
    )
