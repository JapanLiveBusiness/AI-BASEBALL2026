"""Pure helpers for baseball score-adjustment sensitivity analysis."""

SORT_OPTIONS = (
    "新しい日付順",
    "古い日付順",
    "評価スコア差が高い順",
    "評価スコア差が低い順",
    "評価ウェイトが高い順",
)


def _number(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def simulation_points(record):
    """Return the evaluation weight assigned to a scenario."""
    return max(0.0, _number(record.get("simulation_points")))


def point_delta(record):
    """Return the signed evaluation score for a completed scenario."""
    if record.get("point_delta") is not None:
        return _number(record.get("point_delta"))
    result = record.get("result")
    points = simulation_points(record)
    if result == "win":
        return points
    if result == "loss":
        return -points
    return 0.0


def calculate_hit_rate(records):
    """Return successful, decided scenarios and success rate."""
    results = [
        record.get("result")
        for record in records
        if record.get("status") == "final"
        and record.get("result") in {"win", "loss"}
    ]
    successes = results.count("win")
    decided = len(results)
    rate = (successes / decided * 100.0) if decided else None
    return successes, decided, rate


def adjusted_margin(team_score, opponent_score, score_adjustment):
    """Return score margin after applying a hypothetical score adjustment."""
    return _number(team_score) + _number(score_adjustment) - _number(opponent_score)


def classify_result(team_score, opponent_score, score_adjustment):
    """Classify a score-adjustment scenario as positive/negative/boundary."""
    margin = adjusted_margin(team_score, opponent_score, score_adjustment)
    if margin > 0:
        return "win"
    if margin < 0:
        return "loss"
    return "push"


def sort_bets(records, option):
    """Return scenarios ordered by the selected research-history option."""
    scenarios = list(records)
    date_key = lambda item: (
        str(item.get("date", "")),
        str(item.get("time", "")),
        str(item.get("created_at", "")),
    )

    if option == "古い日付順":
        return sorted(scenarios, key=date_key)
    if option == "評価スコア差が高い順":
        return sorted(scenarios, key=point_delta, reverse=True)
    if option == "評価スコア差が低い順":
        return sorted(scenarios, key=point_delta)
    if option == "評価ウェイトが高い順":
        return sorted(scenarios, key=simulation_points, reverse=True)
    return sorted(scenarios, key=date_key, reverse=True)
