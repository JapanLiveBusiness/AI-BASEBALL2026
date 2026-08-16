import json
from pathlib import Path
from collections import deque

SOURCE = Path("/app/data/historical_games.json")
OUTPUT = Path("/app/data/hawks_backtest_dataset.json")


def pct(wins, losses):
    decided = wins + losses
    if decided == 0:
        return 0.5
    return wins / decided


def main():
    data = json.loads(
        SOURCE.read_text(encoding="utf-8")
    )

    # 古い試合 → 新しい試合
    games = sorted(
        data,
        key=lambda g: g["date"]
    )

    hawks_wins = 0
    hawks_losses = 0
    hawks_draws = 0

    recent = deque(maxlen=5)

    rows = []

    for g in games:

        # ==========================================
        # この試合より「前」のデータだけ使用
        # ==========================================
        pre_pct = pct(
            hawks_wins,
            hawks_losses
        )

        recent_wins = sum(
            1 for x in recent
            if x == "勝"
        )

        recent_losses = sum(
            1 for x in recent
            if x == "敗"
        )

        h = g.get("hawks_handicap")

        try:
            h = float(h)
        except (TypeError, ValueError):
            h = 0.0

        # ==========================================
        # v1バックテスト予測
        #
        # まだ相手の試合前勝率を持っていないため、
        # この段階ではLog5を入れない。
        # データリークを避けることを優先。
        # ==========================================

        base_prob = pre_pct * 100.0

        # シーズン序盤の母数不足を抑える
        games_before = hawks_wins + hawks_losses

        if games_before < 10:
            reliability = games_before / 10.0

            base_prob = (
                50.0 * (1.0 - reliability)
                + base_prob * reliability
            )

        # HOME補正
        # 119試合実績ではHOME/AWAY差が小さいため
        # 従来+3ではなく仮に+0.7 / -0.7
        venue_mod = (
            0.7
            if g.get("home")
            else -0.7
        )

        # 直近5試合
        if len(recent) >= 5:
            momentum_table = {
                5: 5.0,
                4: 3.5,
                3: 1.5,
                2: -1.0,
                1: -3.0,
                0: -5.0,
            }

            momentum_mod = momentum_table.get(
                recent_wins,
                0.0
            )
        else:
            momentum_mod = 0.0

        # 過去ハンディ
        # 現時点では固定×8を評価対象として残す
        handicap_mod = h * 8.0

        raw_prob = (
            base_prob
            + venue_mod
            + momentum_mod
            + handicap_mod
        )

        predicted = max(
            0.5,
            min(99.5, raw_prob)
        )

        actual = g.get("result")

        if actual == "勝":
            actual_win = 1
        elif actual == "敗":
            actual_win = 0
        else:
            actual_win = None

        row = {
            "date": g["date"],
            "opponent": g.get("opponent"),
            "home": bool(g.get("home")),

            "hawks_score": g.get(
                "hawks_score"
            ),

            "opponent_score": g.get(
                "opponent_score"
            ),

            "result": actual,

            "games_before": games_before,

            "pre_wins": hawks_wins,
            "pre_losses": hawks_losses,
            "pre_draws": hawks_draws,

            "pre_win_pct": round(
                pre_pct,
                4
            ),

            "recent5": list(recent),

            "recent5_wins": recent_wins,
            "recent5_losses": recent_losses,

            "handicap_raw": g.get(
                "handicap_raw"
            ),

            "hawks_handicap": h,

            "base_probability": round(
                base_prob,
                2
            ),

            "venue_mod": round(
                venue_mod,
                2
            ),

            "momentum_mod": round(
                momentum_mod,
                2
            ),

            "handicap_mod": round(
                handicap_mod,
                2
            ),

            "predicted_probability": round(
                predicted,
                2
            ),

            "actual_win": actual_win,
        }

        rows.append(row)

        # ==========================================
        # 試合結果は予測を作った「後」に更新
        # ==========================================
        if actual == "勝":
            hawks_wins += 1

        elif actual == "敗":
            hawks_losses += 1

        elif actual == "分":
            hawks_draws += 1

        recent.append(actual)

    OUTPUT.write_text(
        json.dumps(
            rows,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print("BACKTEST_DATASET_CREATED")
    print("TOTAL:", len(rows))
    print("OUTPUT:", OUTPUT)


if __name__ == "__main__":
    main()
