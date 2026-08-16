import json
import math
from pathlib import Path

SRC = Path("/opt/hawks-ai/data/hawks_games_starter_history.json")
OUT = Path("/opt/hawks-ai/data/hawks_backtest_v5.json")

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


def win_pct(items):
    if not items:
        return 0.5
    return sum(g["result"] == "win" for g in items) / len(items)


def avg_diff(items):
    if not items:
        return 0.0
    return sum(g["run_diff"] for g in items) / len(items)


def shrink(p, n, strength=10):
    return (p * n + 0.5 * strength) / (n + strength)


def sigmoid(z):
    z = max(-35, min(35, z))
    return 1 / (1 + math.exp(-z))


def features(history, game):

    recent5 = history[-5:]
    recent10 = history[-10:]
    recent20 = history[-20:]

    opp = [
        g for g in history
        if g["opponent"] == game["opponent"]
    ][-20:]

    ha = [
        g for g in history
        if g["home_away"] == game["home_away"]
    ][-30:]

    season = [
        g for g in history
        if g["season"] == game["season"]
    ]

    sh = game["starter_history"]

    hs = sh["hawks"]
    os = sh["opponent"]

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
        win_pct(recent5) - 0.5,
        win_pct(recent10) - 0.5,
        win_pct(recent20) - 0.5,

        max(-5, min(5, avg_diff(recent5))) / 5,
        max(-5, min(5, avg_diff(recent10))) / 5,

        # 対戦相手
        win_pct(opp) - 0.5,

        # HOME / AWAY
        win_pct(ha) - 0.5,

        # 今季
        win_pct(season) - 0.5,

        # 先発
        hp - 0.5,
        op - 0.5,
        hp - op,

        hr - or_,

        max(
            -5,
            min(
                5,
                sh["run_diff_advantage"]
            )
        ) / 5,

        # サンプル信頼度
        min(hs["starts"], 30) / 30,
        min(os["starts"], 30) / 30,

        # 場所
        1.0 if game["home_away"] == "home" else 0.0,

        # 交流戦
        1.0 if game["game_type"] == "interleague" else 0.0,
    ]


def train(X, y, epochs=300, lr=0.06, l2=0.08):

    nf = len(X[0])
    w = [0.0] * nf

    for _ in range(epochs):

        grad = [0.0] * nf

        for xi, yi in zip(X, y):

            p = sigmoid(
                sum(
                    a*b
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

# Walk-forward
for i in range(100, len(games)):

    train_games = games[:i]
    test = games[i]

    X = []
    y = []

    for j in range(30, len(train_games)):

        hist = train_games[:j]
        target = train_games[j]

        X.append(
            features(hist, target)
        )

        y.append(
            1 if target["result"] == "win"
            else 0
        )

    if len(X) < 30:
        continue

    w = train(X, y)

    xt = features(
        train_games,
        test
    )

    prob = sigmoid(
        sum(
            a*b
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
        "home_away": test["home_away"],
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

accuracy = correct / total

always_win = sum(
    p["actual"] == "win"
    for p in predictions
) / total

brier = sum(
    (
        p["probability"] -
        (1 if p["actual"] == "win" else 0)
    ) ** 2
    for p in predictions
) / total

auc = auc_score(predictions)


print("===== HAWKS MODEL V5 =====")

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


# 確率帯
print("\n===== PROBABILITY BINS =====")

for low in [
    0.45,
    0.50,
    0.55,
    0.60,
    0.65,
    0.70,
    0.75
]:

    high = low + 0.05

    subset = [
        p for p in predictions
        if low <= p["probability"] < high
    ]

    if not subset:
        continue

    wins = sum(
        p["actual"] == "win"
        for p in subset
    )

    print(
        f"{low:.0%}-{high:.0%}",
        len(subset),
        "games",
        f"actual win {wins/len(subset):.1%}"
    )


# 上位/下位比較
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


result = {
    "model": "hawks_v5",
    "predictions": total,
    "accuracy": round(accuracy, 4),
    "always_win": round(always_win, 4),
    "brier": round(brier, 4),
    "auc": round(auc, 4),
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


print("\nOUTPUT:", OUT)

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
        f"{p['probability']:.1%}",
        p["predicted"],
        "actual:",
        p["actual"],
        mark
    )
