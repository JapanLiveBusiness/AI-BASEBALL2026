import json
import math
from pathlib import Path

SRC = Path("/opt/hawks-ai/data/hawks_games_context.json")
OUT = Path("/opt/hawks-ai/data/hawks_backtest_v7.json")

VALID_TYPES = {"regular", "interleague"}

with SRC.open(encoding="utf-8") as f:
    data = json.load(f)

games = sorted(
    [
        g for g in data
        if g["game_type"] in VALID_TYPES
        and g["result"] != "draw"
    ],
    key=lambda x: x["date"]
)


def sigmoid(z):
    z = max(-35, min(35, z))
    return 1.0 / (1.0 + math.exp(-z))


def shrink(p, n, strength=10):
    return (p * n + 0.5 * strength) / (n + strength)


def features(game):
    sh = game["starter_history"]
    hs = sh["hawks"]
    os = sh["opponent"]

    tf = game["team_form"]
    c = game["game_context"]

    h5 = tf["hawks_recent5"]
    h10 = tf["hawks_recent10"]
    o5 = tf["opponent_recent5"]
    o10 = tf["opponent_recent10"]

    h3c = c["hawks_recent3"]
    h5c = c["hawks_recent5"]
    h10c = c["hawks_recent10"]

    o3c = c["opponent_recent3"]
    o5c = c["opponent_recent5"]
    o10c = c["opponent_recent10"]

    hp = shrink(
        hs["win_pct"],
        hs["starts"]
    )

    op = shrink(
        os["win_pct"],
        os["starts"]
    )

    hr = shrink(
        hs["recent3_win_pct"],
        min(hs["starts"], 3),
        strength=5
    )

    or_ = shrink(
        os["recent3_win_pct"],
        min(os["starts"], 3),
        strength=5
    )

    return [
        1.0,

        # チーム状態
        h5["win_pct"] - o5["win_pct"],
        h10["win_pct"] - o10["win_pct"],

        max(
            -5,
            min(
                5,
                h5["avg_run_diff"] -
                o5["avg_run_diff"]
            )
        ) / 5,

        max(
            -5,
            min(
                5,
                h10["avg_run_diff"] -
                o10["avg_run_diff"]
            )
        ) / 5,

        # 先発投手
        hp - op,
        hr - or_,

        max(
            -5,
            min(5, sh["run_diff_advantage"])
        ) / 5,

        min(hs["starts"], 30) / 30,
        min(os["starts"], 30) / 30,

        # 休養・連戦
        max(
            -3,
            min(3, c["rest_advantage"])
        ) / 3,

        max(
            -6,
            min(6, c["consecutive_advantage"])
        ) / 6,

        # 直近得点力
        max(
            -10,
            min(10, c["recent3_scoring_advantage"])
        ) / 10,

        max(
            -10,
            min(10, c["recent5_scoring_advantage"])
        ) / 10,

        max(
            -10,
            min(10, c["recent10_scoring_advantage"])
        ) / 10,

        # 直近失点力
        max(
            -10,
            min(
                10,
                o3c["avg_runs_against"] -
                h3c["avg_runs_against"]
            )
        ) / 10,

        max(
            -10,
            min(
                10,
                o5c["avg_runs_against"] -
                h5c["avg_runs_against"]
            )
        ) / 10,

        max(
            -10,
            min(
                10,
                o10c["avg_runs_against"] -
                h10c["avg_runs_against"]
            )
        ) / 10,

        # 得失点差
        max(
            -10,
            min(
                10,
                h3c["avg_run_diff"] -
                o3c["avg_run_diff"]
            )
        ) / 10,

        max(
            -10,
            min(
                10,
                h5c["avg_run_diff"] -
                o5c["avg_run_diff"]
            )
        ) / 10,

        max(
            -10,
            min(
                10,
                h10c["avg_run_diff"] -
                o10c["avg_run_diff"]
            )
        ) / 10,

        # ホーム
        1.0 if game["home_away"] == "home" else 0.0,

        # 交流戦
        1.0 if game["game_type"] == "interleague" else 0.0,
    ]


def train(X, y, epochs=350, lr=0.05, l2=0.10):
    nf = len(X[0])
    w = [0.0] * nf

    for _ in range(epochs):
        grad = [0.0] * nf

        for xi, yi in zip(X, y):
            p = sigmoid(
                sum(
                    a * b
                    for a, b in zip(w, xi)
                )
            )

            err = p - yi

            for j in range(nf):
                grad[j] += err * xi[j]

        n = len(X)

        for j in range(nf):
            grad[j] /= n

            if j:
                grad[j] += l2 * w[j]

            w[j] -= lr * grad[j]

    return w


def auc_score(predictions):
    wins = [
        p["probability"]
        for p in predictions
        if p["actual"] == "win"
    ]

    losses = [
        p["probability"]
        for p in predictions
        if p["actual"] == "loss"
    ]

    if not wins or not losses:
        return 0.5

    score = 0.0
    total = len(wins) * len(losses)

    for w in wins:
        for l in losses:
            if w > l:
                score += 1
            elif w == l:
                score += 0.5

    return score / total


predictions = []

for i in range(100, len(games)):
    train_games = games[:i]
    test = games[i]

    X = []
    y = []

    for j in range(30, len(train_games)):
        target = train_games[j]

        X.append(features(target))

        y.append(
            1 if target["result"] == "win"
            else 0
        )

    if len(X) < 30:
        continue

    w = train(X, y)

    xt = features(test)

    prob = sigmoid(
        sum(
            a * b
            for a, b in zip(w, xt)
        )
    )

    predicted = (
        "win"
        if prob >= 0.5
        else "loss"
    )

    predictions.append({
        "date": test["date"],
        "opponent": test["opponent"],
        "hawks_starter": test["hawks_starter"],
        "opponent_starter": test["opponent_starter"],
        "probability": round(prob, 4),
        "predicted": predicted,
        "actual": test["result"],
        "correct": predicted == test["result"]
    })


total = len(predictions)

correct = sum(
    p["correct"]
    for p in predictions
)

accuracy = correct / total if total else 0

always_win = (
    sum(
        p["actual"] == "win"
        for p in predictions
    ) / total
    if total else 0
)

brier = (
    sum(
        (
            p["probability"] -
            (
                1 if p["actual"] == "win"
                else 0
            )
        ) ** 2
        for p in predictions
    ) / total
    if total else 0
)

auc = auc_score(predictions)


print("===== HAWKS MODEL V7 =====")
print("PREDICTIONS :", total)
print("CORRECT     :", correct)
print("ACCURACY    :", f"{accuracy:.2%}")
print("ALWAYS WIN  :", f"{always_win:.2%}")
print(
    "IMPROVEMENT :",
    f"{accuracy-always_win:+.2%}"
)
print("BRIER       :", f"{brier:.4f}")
print("AUC         :", f"{auc:.4f}")


ordered = sorted(
    predictions,
    key=lambda x: x["probability"]
)

n = max(1, len(ordered) // 5)

bottom = ordered[:n]
top = ordered[-n:]


def actual_win_pct(items):
    return sum(
        p["actual"] == "win"
        for p in items
    ) / len(items)


print("\n===== RANKING TEST =====")

print(
    "BOTTOM 20%:",
    len(bottom),
    "games",
    f"actual win {actual_win_pct(bottom):.1%}"
)

print(
    "TOP 20%   :",
    len(top),
    "games",
    f"actual win {actual_win_pct(top):.1%}"
)


loss_predictions = [
    p for p in predictions
    if p["predicted"] == "loss"
]

loss_hits = sum(
    p["actual"] == "loss"
    for p in loss_predictions
)

print("\n===== LOSS DETECTION =====")
print("LOSS PREDICTIONS:", len(loss_predictions))
print("LOSS HITS       :", loss_hits)

if loss_predictions:
    print(
        "LOSS PRECISION  :",
        f"{loss_hits/len(loss_predictions):.1%}"
    )


result = {
    "model": "hawks_v7_context",
    "predictions": total,
    "correct": correct,
    "accuracy": round(accuracy, 4),
    "always_win": round(always_win, 4),
    "improvement": round(
        accuracy - always_win, 4
    ),
    "brier": round(brier, 4),
    "auc": round(auc, 4),
    "results": predictions
}

with OUT.open("w", encoding="utf-8") as f:
    json.dump(
        result,
        f,
        ensure_ascii=False,
        indent=2
    )


print("\nOUTPUT:", OUT)

print("\n===== LAST 10 =====")

for p in predictions[-10:]:
    mark = "○" if p["correct"] else "×"

    print(
        p["date"],
        p["opponent"],
        "|",
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
