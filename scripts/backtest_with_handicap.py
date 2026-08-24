import argparse
import json
import math
import re
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from sklearn.linear_model import LogisticRegression


TEAM_ALIASES = {
    "福岡ソフトバンクホークス": "ソフトバンク",
    "ソフトバンク": "ソフトバンク",
    "福岡ソフトバンク": "ソフトバンク",
    "北海道日本ハムファイターズ": "日本ハム",
    "日本ハム": "日本ハム",
    "東北楽天ゴールデンイーグルス": "楽天",
    "楽天": "楽天",
    "千葉ロッテマリーンズ": "ロッテ",
    "ロッテ": "ロッテ",
    "埼玉西武ライオンズ": "西武",
    "西武": "西武",
    "オリックス・バファローズ": "オリックス",
    "オリックス": "オリックス",
    "読売ジャイアンツ": "巨人",
    "巨人": "巨人",
    "東京ヤクルトスワローズ": "ヤクルト",
    "ヤクルト": "ヤクルト",
    "横浜DeNAベイスターズ": "DeNA",
    "DeNA": "DeNA",
    "中日ドラゴンズ": "中日",
    "中日": "中日",
    "阪神タイガース": "阪神",
    "阪神": "阪神",
    "広島東洋カープ": "広島",
    "広島": "広島",
}


def normalize_team(value):
    text = re.sub(r"\s+", "", str(value or ""))
    for name in sorted(TEAM_ALIASES, key=len, reverse=True):
        if name in text:
            return TEAM_ALIASES[name]
    return text


def numeric_handicap(value):
    text = str(value or "").strip()

    if not text or text in {"-", "－", "—", "未発表"}:
        return None

    text = text.replace("−", "-").replace("－", "-")

    # 1半、1半2、1半3、1半5、1半7などは
    # 二値勝敗判定上は1.5点境界として扱う
    half_match = re.search(r"(\d+)\s*半", text)
    if half_match:
        return float(half_match.group(1)) + 0.5

    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    return float(match.group()) if match else None

def fetch_handicap(game, session):
    url = game.get("source_url")

    if not url:
        date_text = str(game["date"]).replace("-", "")
        url = f"https://handenomori.com/jpb/{date_text}/"

    response = session.get(url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")

    home = normalize_team(game.get("home"))
    away = normalize_team(game.get("away"))

    for block in soup.select("div.game-detail2"):
        block_text = block.get_text(" ", strip=True)

        if home not in block_text or away not in block_text:
            continue

        for table in block.find_all("table"):
            rows = table.find_all("tr")

            for index, row in enumerate(rows):
                labels = [
                    cell.get_text(" ", strip=True)
                    for cell in row.find_all(["th", "td"])
                ]

                joined = " ".join(labels)

                if "ホーム" not in joined or "ビジター" not in joined:
                    continue

                # 見出し行の次にある値行を取得
                for value_row in rows[index + 1:]:
                    cells = value_row.find_all(["th", "td"])

                    if len(cells) < 2:
                        continue

                    home_raw = cells[0].get_text(" ", strip=True)
                    away_raw = cells[1].get_text(" ", strip=True)

                    home_value = numeric_handicap(home_raw)
                    away_value = numeric_handicap(away_raw)

                    return {
                        "home_handicap": home_value,
                        "away_handicap": away_value,
                        "home_handicap_raw": home_raw or None,
                        "away_handicap_raw": away_raw or None,
                        "handicap_team": (
                            home if home_value is not None
                            else away if away_value is not None
                            else None
                        ),
                        "handicap_url": url,
                    }

        return {
            "home_handicap": None,
            "away_handicap": None,
            "home_handicap_raw": None,
            "away_handicap_raw": None,
            "handicap_team": None,
            "handicap_url": url,
        }

    return {
        "home_handicap": None,
        "away_handicap": None,
        "home_handicap_raw": None,
        "away_handicap_raw": None,
        "handicap_team": None,
        "handicap_url": url,
    }

def build_features(previous, game):
    recent = previous[-30:]
    matchup = [
        row for row in previous
        if normalize_team(row.get("opponent"))
        == normalize_team(game.get("opponent"))
    ][-10:]

    if recent:
        recent_win_rate = sum(
            1 for row in recent if row.get("result") == "win"
        ) / len(recent)

        recent_run_diff = sum(
            float(row.get("run_diff", 0) or 0) for row in recent
        ) / len(recent)
    else:
        recent_win_rate = 0.5
        recent_run_diff = 0.0

    if matchup:
        matchup_win_rate = sum(
            1 for row in matchup if row.get("result") == "win"
        ) / len(matchup)
    else:
        matchup_win_rate = 0.5

    home_flag = 1.0 if game.get("home_away") == "home" else 0.0

    starter = game.get("starter_history") or {}
    win_pct_diff = float(starter.get("win_pct_diff", 0) or 0)
    recent3_diff = float(starter.get("recent3_diff", 0) or 0)
    starter_run_diff = float(starter.get("run_diff_advantage", 0) or 0)

    return [
        recent_win_rate,
        recent_run_diff,
        matchup_win_rate,
        home_flag,
        win_pct_diff,
        recent3_diff,
        starter_run_diff,
    ]


def fallback_probability(features):
    score = (
        (features[0] - 0.5) * 3.0
        + features[1] * 0.12
        + (features[2] - 0.5) * 1.5
        + features[3] * 0.18
        + features[4] * 0.8
        + features[5] * 0.5
        + features[6] * 0.05
    )
    return 1 / (1 + math.exp(-score))


def result_from_scores(hawks_score, opponent_score):
    if hawks_score > opponent_score:
        return "勝"
    if hawks_score < opponent_score:
        return "敗"
    return "分"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--from", dest="date_from", required=True)
    parser.add_argument("--to", dest="date_to", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--fetch-handicap", action="store_true")
    parser.add_argument("--walk-forward", action="store_true")
    parser.add_argument("--sleep", type=float, default=1.2)
    args = parser.parse_args()

    games = json.loads(Path(args.input).read_text(encoding="utf-8"))
    games = sorted(
        [
            game for game in games
            if args.date_from <= str(game.get("date", "")) <= args.date_to
        ],
        key=lambda game: str(game.get("date", "")),
    )

    prediction_path = Path("data/pregame_predictions.json")
    saved_predictions = {}

    if prediction_path.exists():
        rows = json.loads(prediction_path.read_text(encoding="utf-8"))
        for row in rows:
            key = (
                str(row.get("date")),
                normalize_team(row.get("opponent")),
            )
            try:
                saved_predictions[key] = float(row.get("probability"))
            except (TypeError, ValueError):
                pass

    cache_path = Path("data/handicap_cache.json")
    handicap_cache = {}

    if cache_path.exists():
        handicap_cache = json.loads(cache_path.read_text(encoding="utf-8"))

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 BASEBALL-AI-NEXT/1.0"
    })

    previous = []
    training_x = []
    training_y = []
    output_rows = []

    for index, game in enumerate(games, start=1):
        features = build_features(previous, game)

        key = (
            str(game.get("date")),
            normalize_team(game.get("opponent")),
        )

        if key in saved_predictions:
            probability = saved_predictions[key] / 100
            prediction_source = "固定済み試合前予測"
        elif len(set(training_y)) >= 2 and len(training_y) >= 30:
            model = LogisticRegression(max_iter=2000)
            model.fit(training_x, training_y)
            probability = float(model.predict_proba([features])[0][1])
            prediction_source = "ウォークフォワード"
        else:
            probability = fallback_probability(features)
            prediction_source = "初期計算式"

        predicted_result = "勝" if probability >= 0.5 else "敗"

        date_value = str(game.get("date"))
        handicap_data = handicap_cache.get(date_value)

        if args.fetch_handicap and handicap_data is None:
            try:
                handicap_data = fetch_handicap(game, session)
            except Exception as exc:
                handicap_data = {
                    "away_handicap": None,
                    "home_handicap": None,
                    "error": str(exc),
                }

            handicap_cache[date_value] = handicap_data
            cache_path.write_text(
                json.dumps(
                    handicap_cache,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            time.sleep(args.sleep)

        handicap_data = handicap_data or {}
        home_hcap = handicap_data.get("home_handicap")
        away_hcap = handicap_data.get("away_handicap")

        home_score = float(game.get("home_score", 0) or 0)
        away_score = float(game.get("away_score", 0) or 0)

        if game.get("home_away") == "home":
            hawks_score = home_score
            opponent_score = away_score
            hawks_hcap = home_hcap
            opponent_hcap = away_hcap
        else:
            hawks_score = away_score
            opponent_score = home_score
            hawks_hcap = away_hcap
            opponent_hcap = home_hcap

        normal_result = result_from_scores(hawks_score, opponent_score)
        normal_hit = (
            predicted_result == normal_result
            if normal_result != "分"
            else None
        )

        has_handicap = hawks_hcap is not None or opponent_hcap is not None

        if has_handicap:
            adjusted_hawks = hawks_score + float(hawks_hcap or 0)
            adjusted_opponent = opponent_score + float(opponent_hcap or 0)
            handicap_result = result_from_scores(
                adjusted_hawks,
                adjusted_opponent,
            )
            handicap_hit = (
                predicted_result == handicap_result
                if handicap_result != "分"
                else None
            )
        else:
            adjusted_hawks = None
            adjusted_opponent = None
            handicap_result = "対象外"
            handicap_hit = None

        output_rows.append({
            "試合日": date_value,
            "対戦相手": normalize_team(game.get("opponent")),
            "ホーム・ビジター": game.get("home_away"),
            "球場": game.get("venue", ""),
            "ホークス得点": hawks_score,
            "相手得点": opponent_score,
            "通常勝敗": normal_result,
            "ホークスハンデ": hawks_hcap,
            "相手ハンデ": opponent_hcap,
            "補正後ホークス得点": adjusted_hawks,
            "補正後相手得点": adjusted_opponent,
            "ハンデ勝敗": handicap_result,
            "AI予測": predicted_result,
            "AI勝率": round(probability * 100, 1),
            "予測方式": prediction_source,
            "通常的中": normal_hit,
            "ハンデ的中": handicap_hit,
        })

        if normal_result != "分":
            training_x.append(features)
            training_y.append(1 if normal_result == "勝" else 0)

        previous.append(game)

        print(
            f"[{index}/{len(games)}] {date_value} "
            f"vs {normalize_team(game.get('opponent'))} "
            f"AI {probability * 100:.1f}% "
            f"通常={normal_hit} ハンデ={handicap_hit}"
        )

    df = pd.DataFrame(output_rows)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False, encoding="utf-8-sig")

    normal = df["通常的中"].dropna()
    handicap = df["ハンデ的中"].dropna()

    print("\n========== 集計結果 ==========")
    print("全試合:", len(df))
    print("通常勝敗対象:", len(normal))
    print(
        "通常的中率:",
        f"{normal.astype(bool).mean() * 100:.1f}%"
        if len(normal) else "対象なし",
    )
    print("ハンデ取得・判定対象:", len(handicap))
    print(
        "ハンデ的中率:",
        f"{handicap.astype(bool).mean() * 100:.1f}%"
        if len(handicap) else "対象なし",
    )
    print("出力:", output)


if __name__ == "__main__":
    main()
