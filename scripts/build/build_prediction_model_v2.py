import json
import math
from pathlib import Path

SRC = Path("/opt/hawks-ai/data/hawks_games_enriched.json")
OUT = Path("/opt/hawks-ai/data/hawks_backtest_v2.json")

VALID_TYPES = {"regular", "interleague"}

with SRC.open(encoding="utf-8") as f:
    all_games = json.load(f)

games = sorted(
    [g for g in all_games if g["game_type"] in VALID_TYPES],
    key=lambda x: x["date"]
)

# 引き分けは学習・評価対象から除外
decided_games = [g for g in games if g["result"] != "draw"]


def win_pct(items):
    d = [g for g in items if g["result"] != "draw"]
    if not d:
        return 0.5
    return sum(g["result"] == "win" for g in d) / len(d)


def avg_run_diff(items):
    if not items:
        return 0.0
    return sum(g["run_diff"] for g in items) / len(items)


def build_features(history, game):
    recent5 = history[-5:]
    recent10 = history[-10:]
    recent20 = history[-20:]

    opp = [
        g for g in history
        if g["opponent"] == game["opponent"]
    ]

    opp_recent = opp[-10:]

    ha = [
        g for g in history
        if g["home_away"] == game["home_away"]
    ]

    season = [
        g for g in history
        if g["season"] == game["season"]
    ]

    # 0.5中心になるよう変換
    return [
        1.0,
        win_pct(recent5) - 0.5,
        win_pct(recent10) - 0.5,
        win_pct(recent20) - 0.5,
        win_pct(opp_recent) - 0.5,
        win_pct(ha) - 0.5,
        win_pct(season) - 0.5,
        max(-5, min(5, avg_run_diff(recent5))) / 5,
        max(-5, min(5, avg_run_diff(recent10))) / 5,
        1.0 if game["home_away"] == "home" else 0.0,
        1.0 if game["game_type"] == "interleague" else 0.0,
    ]


def sigmoid(z):
    if z < -35:
        return 0.0
    if z > 35:
        return 1.0
    return 1.0 / (1.0 + math.exp(-z))


def train_logistic(X, y, epochs=1200, lr=0.08, l2=0.03):
    n_features = len(X[0])
    w = [0.0] * n_features

    for _ in range(epochs):
        grad = [0.0] * n_features

        for xi, yi in zip(X, y):
            p = sigmoid(sum(a*b for a, b in zip(w, xi)))
            err = p - yi

            for j in range(n_features):
                grad[j] += err * xi[j]

        n = len(X)

        for j in range(n_features):
            grad[j] /= n

            # interceptは正則化しない
            if j != 0:
                grad[j] += l2 * w[j]

            w[j] -= lr * grad[j]

    return w


predictions = []

# 100試合たまってからwalk-forward開始
for i in range(100, len(decided_games)):
    train_games = decided_games[:i]
    test_game = decided_games[i]

    X = []
    y = []

    # 学習データ内でも各試合より前だけを特徴量に使う
    for j in range(30, len(train_games)):
        hist = train_games[:j]
        target = train_games[j]

        X.append(build_features(hist, target))
        y.append(1 if target["result"] == "win" else 0)

    if len(X) < 30:
        continue

    w = train_logistic(X, y)

    x_test = build_features(train_games, test_game)
    probability = sigmoid(
        sum(a*b for a, b in zip(w, x_test))
    )

    predicted = "win" if probability >= 0.5 else "loss"

    predictions.append({
        "date": test_game["date"],
        "opponent": test_game["opponent"],
        "home_away": test_game["home_away"],
        "game_type": test_game["game_type"],
        "probability": round(probability, 4),
        "predicted": predicted,
        "actual": test_game["result"],
        "correct": predicted == test_game["result"],
    })


total = len(predictions)
correct = sum(p["correct"] for p in predictions)
accuracy = correct / total if total else 0

always_win = sum(
    p["actual"] == "win"
    for p in predictions
)

always_accuracy = always_win / total if total else 0

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

# Brier score: 確率予測の品質
brier = sum(
    (
        p["probability"] -
        (1 if p["actual"] == "win" else 0)
    ) ** 2
    for p in predictions
) / total if total else 0


# 確率帯ごとの実勝率
bins = []

for low in [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
    high = low + 0.1

    subset = [
        p for p in predictions
        if low <= p["probability"] < high
    ]

    if not subset:
        continue

    actual_win = sum(
        p["actual"] == "win"
        for p in subset
    ) / len(subset)

    bins.append({
        "range": f"{low:.1f}-{high:.1f}",
        "games": len(subset),
        "actual_win_pct": round(actual_win, 3)
    })


result = {
    "model": "hawks_logistic_v2",
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
    "calibration": bins,
    "results": predictions,
}

with OUT.open("w", encoding="utf-8") as f:
    json.dump(
        result,
        f,
        ensure_ascii=False,
        indent=2
    )


print("===== HAWKS MODEL V2 =====")
print("PREDICTIONS        :", total)
print("CORRECT            :", correct)
print("V2 ACCURACY        :", f"{accuracy:.2%}")
print("ALWAYS WIN         :", f"{always_accuracy:.2%}")
print(
    "IMPROVEMENT        :",
    f"{accuracy-always_accuracy:+.2%}"
)
print("LOSS PREDICTIONS   :", len(loss_predictions))
print("LOSS HITS          :", loss_hits)
print("LOSS PRECISION     :", f"{loss_precision:.2%}")
print("BRIER SCORE        :", f"{brier:.4f}")
print("OUTPUT             :", OUT)

print("\n===== CALIBRATION =====")
for b in bins:
    print(
        b["range"],
        "games:", b["games"],
        "actual win:",
        f"{b['actual_win_pct']:.1%}"
    )

print("\n===== LAST 10 =====")
for p in predictions[-10:]:
    mark = "○" if p["correct"] else "×"

    print(
        p["date"],
        p["opponent"],
        p["home_away"],
        f"{p['probability']:.1%}",
        p["predicted"],
        "actual:",
        p["actual"],
        mark
    )
