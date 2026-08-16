import json
from pathlib import Path
from collections import defaultdict

SRC = Path("/opt/hawks-ai/data/hawks_games_enriched.json")
OUT = Path("/opt/hawks-ai/data/hawks_backtest.json")

VALID_TYPES = {"regular", "interleague"}

with SRC.open(encoding="utf-8") as f:
    games = json.load(f)

games = sorted(
    [g for g in games if g["game_type"] in VALID_TYPES],
    key=lambda x: x["date"]
)

def win_pct(items):
    decided = [g for g in items if g["result"] != "draw"]
    if not decided:
        return 0.5
    return sum(g["result"] == "win" for g in decided) / len(decided)

def avg_diff(items):
    if not items:
        return 0.0
    return sum(g["run_diff"] for g in items) / len(items)

predictions = []

for i, game in enumerate(games):

    # 最低30試合たまるまでは予測対象外
    history = games[:i]

    if len(history) < 30:
        continue

    # その試合より前のデータだけ使用
    recent10 = history[-10:]

    opponent_history = [
        g for g in history
        if g["opponent"] == game["opponent"]
    ]

    venue_history = [
        g for g in history
        if g["home_away"] == game["home_away"]
    ]

    season_history = [
        g for g in history
        if g["season"] == game["season"]
    ]

    # 各要素
    overall = win_pct(history)
    recent = win_pct(recent10)

    opponent = (
        win_pct(opponent_history)
        if opponent_history
        else overall
    )

    homeaway = (
        win_pct(venue_history)
        if venue_history
        else overall
    )

    season = (
        win_pct(season_history)
        if season_history
        else overall
    )

    recent_diff = avg_diff(recent10)

    # 得失点差を0〜1の補正値へ
    run_strength = max(
        0.0,
        min(
            1.0,
            0.5 + recent_diff / 10
        )
    )

    # 初期ウェイト
    probability = (
        overall * 0.15 +
        season * 0.25 +
        recent * 0.25 +
        opponent * 0.15 +
        homeaway * 0.10 +
        run_strength * 0.10
    )

    probability = max(
        0.05,
        min(0.95, probability)
    )

    predicted = (
        "win"
        if probability >= 0.5
        else "loss"
    )

    actual = game["result"]

    correct = (
        actual != "draw"
        and predicted == actual
    )

    predictions.append({
        "date": game["date"],
        "opponent": game["opponent"],
        "home_away": game["home_away"],
        "predicted_win_probability": round(
            probability, 3
        ),
        "predicted": predicted,
        "actual": actual,
        "correct": correct,
        "features": {
            "overall_win_pct": round(overall, 3),
            "season_win_pct": round(season, 3),
            "recent10_win_pct": round(recent, 3),
            "opponent_win_pct": round(opponent, 3),
            "homeaway_win_pct": round(homeaway, 3),
            "recent10_run_diff": round(
                recent_diff, 3
            )
        }
    })

decided = [
    p for p in predictions
    if p["actual"] != "draw"
]

correct = sum(
    p["correct"] for p in decided
)

accuracy = (
    correct / len(decided)
    if decided
    else 0
)

summary = {
    "model": "hawks_baseline_v1",
    "total_predictions": len(predictions),
    "decided_games": len(decided),
    "correct": correct,
    "accuracy": round(accuracy, 4),
    "predictions": predictions
}

with OUT.open("w", encoding="utf-8") as f:
    json.dump(
        summary,
        f,
        ensure_ascii=False,
        indent=2
    )

print("===== HAWKS BACKTEST V1 =====")
print("PREDICTIONS :", len(predictions))
print("DECIDED     :", len(decided))
print("CORRECT     :", correct)
print("ACCURACY    :", f"{accuracy:.1%}")
print("OUTPUT      :", OUT)

print("\n===== LAST 10 =====")

for p in predictions[-10:]:
    mark = "○" if p["correct"] else "×"

    if p["actual"] == "draw":
        mark = "△"

    print(
        p["date"],
        p["opponent"],
        p["home_away"],
        f"予測勝率 {p['predicted_win_probability']:.1%}",
        f"予測 {p['predicted']}",
        f"結果 {p['actual']}",
        mark
    )
