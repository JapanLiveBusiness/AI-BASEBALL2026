import json
from pathlib import Path

SRC = Path("/opt/hawks-ai/data/hawks_games_context.json")
OUT = Path("/opt/hawks-ai/data/hawks_backtest_v8.json")

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
        "P1": (
            g["home_away"] == "away"
            and sh["opponent"]["win_pct"] >= 0.60
            and sh["run_diff_advantage"] < 0
        ),

        "P2": (
            g["home_away"] == "away"
            and sh["run_diff_advantage"] < 0
        ),

        "P3": (
            sh["opponent"]["win_pct"] >= 0.60
            and rd5 < 0
        ),

        "P7": (
            sh["win_pct_diff"] <= -0.20
            and rd5 < 0
        ),
    }

predictions = []

for g in games:
    f = flags(g)

    matched = [
        name for name, active in f.items()
        if active
    ]

    # ベース
    probability = 0.634

    # 検証済み危険パターン
    if f["P3"]:
        probability = 0.42
    elif f["P1"]:
        probability = 0.50
    elif f["P7"]:
        probability = 0.50
    elif f["P2"]:
        probability = 0.56

    predicted = (
        "win"
        if probability >= 0.5
        else "loss"
    )

    predictions.append({
        "date": g["date"],
        "opponent": g["opponent"],
        "hawks_starter": g["hawks_starter"],
        "opponent_starter": g["opponent_starter"],
        "probability": probability,
        "predicted": predicted,
        "actual": g["result"],
        "correct": predicted == g["result"],
        "matched_patterns": matched,
    })

total = len(predictions)
correct = sum(p["correct"] for p in predictions)
accuracy = correct / total

always = sum(
    p["actual"] == "win"
    for p in predictions
) / total

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

brier = sum(
    (
        p["probability"]
        - (1 if p["actual"] == "win" else 0)
    ) ** 2
    for p in predictions
) / total

print("===== HAWKS MODEL V8 =====")
print("TOTAL           :", total)
print("CORRECT         :", correct)
print("ACCURACY        :", f"{accuracy:.2%}")
print("ALWAYS WIN      :", f"{always:.2%}")
print("IMPROVEMENT     :", f"{accuracy-always:+.2%}")
print("LOSS PREDICTIONS:", len(loss_predictions))
print("LOSS HITS       :", loss_hits)
print("LOSS PRECISION  :", f"{loss_precision:.1%}")
print("BRIER           :", f"{brier:.4f}")

print("\n===== PATTERN RESULTS =====")

for name in ["P1", "P2", "P3", "P7"]:

    subset = [
        p for p in predictions
        if name in p["matched_patterns"]
    ]

    if not subset:
        continue

    losses = sum(
        p["actual"] == "loss"
        for p in subset
    )

    print(
        name,
        "|",
        len(subset),
        "games",
        "|",
        losses,
        "losses",
        "|",
        f"{losses/len(subset):.1%}"
    )

print("\n===== 2026 ONLY =====")

subset = [
    p for p in predictions
    if p["date"].startswith("2026-")
]

correct_2026 = sum(
    p["correct"] for p in subset
)

loss_pred_2026 = [
    p for p in subset
    if p["predicted"] == "loss"
]

loss_hit_2026 = sum(
    p["actual"] == "loss"
    for p in loss_pred_2026
)

print(
    "ACCURACY:",
    f"{correct_2026/len(subset):.2%}"
)

print(
    "LOSS PRED:",
    len(loss_pred_2026)
)

print(
    "LOSS HIT :",
    loss_hit_2026
)

if loss_pred_2026:
    print(
        "LOSS PREC:",
        f"{loss_hit_2026/len(loss_pred_2026):.1%}"
    )

with OUT.open("w", encoding="utf-8") as f:
    json.dump(
        {
            "model": "hawks_v8_rules",
            "accuracy": round(accuracy, 4),
            "always_win": round(always, 4),
            "brier": round(brier, 4),
            "loss_precision": round(loss_precision, 4),
            "results": predictions,
        },
        f,
        ensure_ascii=False,
        indent=2
    )

print("\nOUTPUT:", OUT)
