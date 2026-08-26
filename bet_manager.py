import json
from pathlib import Path
from datetime import datetime, timedelta

from storage.json_store import load_json, save_json_atomic

DATA_DIR = Path(__file__).resolve().parent / "data"
GAMES_FILE = DATA_DIR / "all_games_2024_2026.json"
BETS_FILE = DATA_DIR / "bet_records.json"

TEAM_ALIASES = {
    "日ハム": "日本ハム",
    "日本ハム": "日本ハム",
    "ソフトバンク": "ソフトバンク",
    "西武": "西武",
    "ロッテ": "ロッテ",
    "楽天": "楽天",
    "オリックス": "オリックス",
    "巨人": "巨人",
    "中日": "中日",
    "阪神": "阪神",
    "ヤクルト": "ヤクルト",
    "DeNA": "DeNA",
    "広島": "広島",
}


def normalize_team(name):
    if not name:
        return ""
    return TEAM_ALIASES.get(str(name).strip(), str(name).strip())


def find_game(games, date_str, team, opponent):
    team = normalize_team(team)
    opponent = normalize_team(opponent)

    for g in games:
        if g.get("date") != date_str:
            continue

        home = normalize_team(g.get("home"))
        away = normalize_team(g.get("away"))

        if {home, away} == {team, opponent}:
            return g

    return None


def calculate_bet_result(bet, game):
    if not game:
        return {
            "status": "pending",
            "team_score": None,
            "opponent_score": None,
            "adjusted_score": None,
            "result": None,
            "profit": 0
        }

    team = normalize_team(bet["team"])
    opponent = normalize_team(bet["opponent"])

    home = normalize_team(game["home"])
    away = normalize_team(game["away"])

    if team == home:
        team_score = game.get("home_score")
        opponent_score = game.get("away_score")
    elif team == away:
        team_score = game.get("away_score")
        opponent_score = game.get("home_score")
    else:
        return {
            "status": "error",
            "team_score": None,
            "opponent_score": None,
            "adjusted_score": None,
            "result": None,
            "profit": 0
        }

    if team_score is None or opponent_score is None:
        return {
            "status": "pending",
            "team_score": team_score,
            "opponent_score": opponent_score,
            "adjusted_score": None,
            "result": None,
            "profit": 0
        }

    handicap = float(bet.get("handicap", 0))
    units = float(bet.get("bet_units", 0))

    adjusted_score = float(team_score) - handicap
    amount = abs(units) * 10000

    if adjusted_score > float(opponent_score):
        result = "win"
        profit = amount
    elif adjusted_score < float(opponent_score):
        result = "loss"
        profit = -amount
    else:
        result = "push"
        profit = 0

    return {
        "status": "final",
        "team_score": team_score,
        "opponent_score": opponent_score,
        "adjusted_score": adjusted_score,
        "result": result,
        "profit": int(profit)
    }


def get_latest_week_range(bets):
    dates = []

    for bet in bets:
        try:
            dates.append(
                datetime.strptime(bet["date"], "%Y-%m-%d").date()
            )
        except Exception:
            pass

    if not dates:
        return None, None

    latest = max(dates)
    monday = latest - timedelta(days=latest.weekday())
    sunday = monday + timedelta(days=6)

    return monday, sunday


def main():
    games = load_json(GAMES_FILE, [])
    bets = load_json(BETS_FILE, [])

    monday, sunday = get_latest_week_range(bets)

    weekly_unsettled_profit = 0

    for bet in bets:
        game = find_game(
            games,
            bet["date"],
            bet["team"],
            bet["opponent"]
        )

        calc = calculate_bet_result(bet, game)
        bet.update(calc)

        try:
            bet_date = datetime.strptime(
                bet["date"],
                "%Y-%m-%d"
            ).date()
        except Exception:
            continue

        if (
            monday
            and sunday
            and monday <= bet_date <= sunday
            and not bet.get("settled", False)
        ):
            weekly_unsettled_profit += int(
                bet.get("profit", 0)
            )

    save_json_atomic(BETS_FILE, bets)

    summary = {
        "week_start": monday.isoformat() if monday else None,
        "week_end": sunday.isoformat() if sunday else None,
        "weekly_unsettled_profit": weekly_unsettled_profit,
        "updated_at": datetime.now().isoformat(timespec="seconds")
    }

    save_json_atomic(
        DATA_DIR / "bet_summary.json",
        summary
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
