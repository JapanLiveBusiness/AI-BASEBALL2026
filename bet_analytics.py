"""Pure helpers for BET summary metrics and history ordering."""


SORT_OPTIONS = (
    "新しい日付順",
    "古い日付順",
    "収支が高い順",
    "収支が低い順",
    "BET額が高い順",
)


def _number(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def bet_amount(record):
    """Return the explicit stake or derive it from legacy bet units."""
    if record.get("bet_amount") is not None:
        return _number(record.get("bet_amount"))
    return abs(_number(record.get("bet_units"))) * 10000


def settle_bet(team_score, opponent_score, handicap=0):
    """Settle a bet after subtracting the handicap from the selected team."""
    adjusted_score = _number(team_score) - _number(handicap)
    opponent = _number(opponent_score)
    margin = adjusted_score - opponent

    if abs(margin) < 1e-9:
        result = "push"
    elif margin > 0:
        result = "win"
    else:
        result = "loss"

    return round(adjusted_score, 3), result


def profit_for_result(result, amount):
    """Return even-money profit used by the existing BET records."""
    stake = abs(_number(amount))
    if result == "win":
        return int(round(stake))
    if result == "loss":
        return -int(round(stake))
    return 0


def calculate_hit_rate(records):
    """Return wins, decided bets and hit rate; pushes/pending are excluded."""
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


def sort_bets(records, option):
    """Return a new list ordered by the selected history sort option."""
    bets = list(records)
    date_key = lambda bet: (
        str(bet.get("date", "")),
        str(bet.get("time", "")),
        str(bet.get("created_at", "")),
    )

    if option == "古い日付順":
        return sorted(bets, key=date_key)
    if option == "収支が高い順":
        return sorted(bets, key=lambda bet: _number(bet.get("profit")), reverse=True)
    if option == "収支が低い順":
        return sorted(bets, key=lambda bet: _number(bet.get("profit")))
    if option == "BET額が高い順":
        return sorted(bets, key=bet_amount, reverse=True)
    return sorted(bets, key=date_key, reverse=True)
