import json
import math
from pathlib import Path

SRC = Path("/opt/hawks-ai/data/hawks_games_enriched.json")
OUT = Path("/opt/hawks-ai/data/hawks_backtest_v2_fast.json")

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


def sigmoid(z):
    z = max(-30, min(30, z))
    return 1.0 / (1.0 + math.exp(-z))


def win_pct(items):
    if not items:
        return 0.5
    return sum(g["result"] == "win" for g in items) / len(items)


def avg_diff(items):
    if not items:
        return 0.0
    return sum(g["run_diff"] for g in items) / len(items)


def features(history, game):
    recent5 = history[-5:]
    recent10 = history[-10:]
    recent20 = history[-20:]

    opp = [
        g for g in history
        if g["opponent"] == game["opponent"]
    ][-10:]

    same_ha = [
        g for g in history
        if g["home_away"] == game["home_away"]
    ]

    season = [
        g for g in history
        if g["season"] == game["season"]
    ]

    return [
        1.0,
        win_pct(recent5) - 0.5,
        win_pct(recent10) - 0.5,
        win_pct(recent20) - 0.5,
        win_pct(opp) - 0.5,
        win_pct(same_ha) - 0.5,
        win_pct(season) - 0.5,
        max(-5, min(5, avg_diff(recent5))) / 5.0,
        max(-5, min(5, avg_diff(recent10))) / 5.0,
        1.0 if game["home_away"] == "home" else 0.0,
        1.0 if game["game_type"] == "interleague" else 0.0,
    ]


# 11特徴量
weights = [0.0] * 11

LEARNING_RATE = 0.08
L2 = 0.01

predictions = []

for i, game in enumerate(games):

    history = games[:i]

    if len(history) < 30:
        continue

    x = features(history, game)

    z = sum(w * v for w, v in zip(weights, x))
    probability = sigmoid(z)

    predicted = "win" if probability >= 0.5 else "loss"
    actual = game["result"]

    predictions.append({
        "date": game["date"],
        "opponent": game["opponent"],
        "home_away": game["home_away"],
        "game_type": game["game_type"],
        "probability": round(probability, 4),
        "predicted": predicted,
        "actual": actual,
        "correct": predicted == actual,
    })

    # 試合終了後にだけ学習
    y = 1.0 if actual == "win" else 0.0
    error = probability - y

    for j in range(len(weights)):

        grad = error * x[j]

        if j != 0:
            grad += L2 * weights[j]

        weights[j] -= LEARNING_RATE * grad


total = len(predictions)
correct = sum(p["correct"] for p in predictions)

accuracy = correct / total if total else 0

always_correct = sum(
    p["actual"] == "win"
    for p in predictions
)

always_accuracy = (
    always_correct / total
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
    if loss_predictions else 0
)

brier = (
    sum(
        (
            p["probability"] -
            (1 if p["actual"] == "win" else 0)
        ) ** 2
        for p in predictions
    ) / total
    if total else 0
)

result = {
    "model": "hawks_logistic_online_v2",
    "predictions": total,
    "correct": correct,
    "accuracy": round(accuracy, 4),
    "always_win_accuracy": round(always_accuracy, 4),
    "improvement": round(
        accuracy - always_accuracy, 4
    ),
    "loss_predictions": len(loss_predictions),
    "loss_hits": loss_hits,
    "loss_precision": round(loss_precision, 4),
    "brier_score": round(brier, 4),
    "weights": [round(w, 6) for w in weights],
    "results": predictions,
}

with OUT.open("w", encoding="utf-8") as f:
    json.dump(
        result,
        f,
        ensure_ascii=False,
        indent=2
    )

print("===== HAWKS V2 FAST =====")
print("PREDICTIONS      :", total)
print("CORRECT          :", correct)
print("V2 ACCURACY      :", f"{accuracy:.2%}")
print("ALWAYS WIN       :", f"{always_accuracy:.2%}")
print(
    "IMPROVEMENT      :",
    f"{accuracy-always_accuracy:+.2%}"
)
print("LOSS PREDICTIONS :", len(loss_predictions))
print("LOSS HITS        :", loss_hits)
print("LOSS PRECISION   :", f"{loss_precision:.2%}")
print("BRIER SCORE      :", f"{brier:.4f}")
print("OUTPUT           :", OUT)

print("\n===== FINAL WEIGHTS =====")
for i, w in enumerate(weights):
    print(i, round(w, 4))

print("\n===== LAST 10 =====")
for p in predictions[-10:]:
    mark = "○" if p["correct"] else "×"

    print(
        p["date"],
        p["opponent"],
        p["home_away"],
        f"勝率 {p['probability']:.1%}",
        "予測", p["predicted"],
        "結果", p["actual"],
        mark
    )
