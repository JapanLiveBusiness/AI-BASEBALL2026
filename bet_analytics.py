"""Pure helpers for hypothetical baseball simulation metrics and ordering.

The module intentionally treats all quantities as virtual points. It can read
legacy records for compatibility, but it does not model or recommend real-money
wagers.
"""


SORT_OPTIONS = (
    "新しい日付順",
    "古い日付順",
    "仮想ポイント差が高い順",
    "仮想ポイント差が低い順",
    "仮想投入ポイントが高い順",
)


def _number(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def simulation_points(record):
    """Return virtual scenario points, with legacy field compatibility."""
    if record.get("simulation_points") is not None:
        return max(0.0, _number(record.get("simulation_points")))
    if record.get("bet_amount") is not None:
        # Legacy records are displayed only as abstract points.
        return max(0.0, _number(record.get("bet_amount")) / 100.0)
    return abs(_number(record.get("bet_units"))) * 100.0


def point_delta(record):
    """Return the virtual point delta for a completed scenario."""
    if record.get("point_delta") is not None:
        return _number(record.get("point_delta"))
    if record.get("profit") is not None:
        # Legacy compatibility only: scale old numeric values into points.
        return _number(record.get("profit")) / 100.0
    result = record.get("result")
    points = simulation_points(record)
    if result == "win":
        return points
    if result == "loss":
        return -points
    return 0.0


def calculate_hit_rate(records):
    """Return wins, decided scenarios and hit rate; pushes/pending excluded."""
    results = [
        record.get("result")
        for record in records
        if record.get("status") == "final"
        and record.get("result") in {"win", "loss"}
    ]
    wins = results.count("win")
    decided = len(results)
    rate = (wins / decided * 100.0) if decided else None
    return wins, decided, rate


def adjusted_margin(team_score, opponent_score, handicap):
    """Return score margin after applying the hypothetical handicap."""
    return _number(team_score) + _number(handicap) - _number(opponent_score)


def classify_result(team_score, opponent_score, handicap):
    """Classify a hypothetical handicap scenario as win/loss/push."""
    margin = adjusted_margin(team_score, opponent_score, handicap)
    if margin > 0:
        return "win"
    if margin < 0:
        return "loss"
    return "push"


def sort_bets(records, option):
    """Return a new list ordered by the selected simulation history option."""
    scenarios = list(records)
    date_key = lambda item: (
        str(item.get("date", "")),
        str(item.get("time", "")),
        str(item.get("created_at", "")),
    )

    if option == "古い日付順":
        return sorted(scenarios, key=date_key)
    if option == "仮想ポイント差が高い順":
        return sorted(scenarios, key=point_delta, reverse=True)
    if option == "仮想ポイント差が低い順":
        return sorted(scenarios, key=point_delta)
    if option == "仮想投入ポイントが高い順":
        return sorted(scenarios, key=simulation_points, reverse=True)
    return sorted(scenarios, key=date_key, reverse=True)
