import json
from pathlib import Path
from collections import defaultdict

ALL_GAMES = Path("/app/data/all_games_2026.json")
HAWKS_GAMES = Path("/app/data/historical_games.json")
OUTPUT = Path("/app/data/hawks_log5_backtest.json")

HAWKS = "ソフトバンク"


def win_pct(rec):
    w = rec["wins"]
    l = rec["losses"]

    if w + l == 0:
        return 0.5

    return w / (w + l)


def log5(p, q):
    numerator = p - (p * q)
    denominator = p + q - (2 * p * q)

    if denominator == 0:
        return 0.5

    return numerator / denominator


def main():
    all_games = json.loads(
        ALL_GAMES.read_text(encoding="utf-8")
    )

    hawks_games = json.loads(
        HAWKS_GAMES.read_text(encoding="utf-8")
    )

    # 日付 → ホークス履歴
    hawks_by_date = {
        g["date"]: g
        for g in hawks_games
    }

    standings = defaultdict(
        lambda: {
            "wins": 0,
            "losses": 0,
            "draws": 0
        }
    )

    output = []

    # 日付順
    all_games.sort(
        key=lambda g: g["date"]
    )

    # 同日の全試合をまとめる
    by_date = defaultdict(list)

    for g in all_games:
        by_date[g["date"]].append(g)

    for game_date in sorted(by_date):

        games_today = by_date[game_date]

        # =========================================
        # 先にホークス戦の「試合前」成績を記録
        # =========================================
        for g in games_today:

            if (
                g["home"] != HAWKS
                and g["away"] != HAWKS
            ):
                continue

            opponent = (
                g["away"]
                if g["home"] == HAWKS
                else g["home"]
            )

            h_rec = standings[HAWKS].copy()
            o_rec = standings[opponent].copy()

            h_pct = win_pct(h_rec)
            o_pct = win_pct(o_rec)

            base = log5(
                h_pct,
                o_pct
            )

            historical = hawks_by_date.get(
                game_date,
                {}
            )

            output.append({
                "date": game_date,
                "opponent": opponent,

                "home":
                    g["home"] == HAWKS,

                "hawks_pre_wins":
                    h_rec["wins"],

                "hawks_pre_losses":
                    h_rec["losses"],

                "hawks_pre_draws":
                    h_rec["draws"],

                "hawks_pre_pct":
                    round(h_pct, 4),

                "opponent_pre_wins":
                    o_rec["wins"],

                "opponent_pre_losses":
                    o_rec["losses"],

                "opponent_pre_draws":
                    o_rec["draws"],

                "opponent_pre_pct":
                    round(o_pct, 4),

                "log5_probability":
                    round(base * 100, 2),

                "hawks_score":
                    g["home_score"]
                    if g["home"] == HAWKS
                    else g["away_score"],

                "opponent_score":
                    g["away_score"]
                    if g["home"] == HAWKS
                    else g["home_score"],

                "result":
                    historical.get("result"),

                "handicap_raw":
                    historical.get(
                        "handicap_raw"
                    ),

                "hawks_handicap":
                    historical.get(
                        "hawks_handicap"
                    ),
            })

        # =========================================
        # その後で今日の試合結果を順位へ反映
        # =========================================
        for g in games_today:

            home = g["home"]
            away = g["away"]

            hs = int(g["home_score"])
            aws = int(g["away_score"])

            if hs > aws:
                standings[home]["wins"] += 1
                standings[away]["losses"] += 1

            elif hs < aws:
                standings[away]["wins"] += 1
                standings[home]["losses"] += 1

            else:
                standings[home]["draws"] += 1
                standings[away]["draws"] += 1

    OUTPUT.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print("LOG5_BACKTEST_CREATED")
    print("TOTAL:", len(output))
    print("OUTPUT:", OUTPUT)

    print()
    print("===== 最新10試合 =====")

    for g in output[-10:]:
        print(
            g["date"],
            g["opponent"],
            f'H={g["hawks_pre_pct"]:.3f}',
            f'O={g["opponent_pre_pct"]:.3f}',
            f'LOG5={g["log5_probability"]:.1f}%',
            g["result"]
        )


if __name__ == "__main__":
    main()
