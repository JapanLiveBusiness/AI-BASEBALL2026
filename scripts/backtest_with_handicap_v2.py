#!/usr/bin/env python3
"""BASEBALL AI NEXT backtest V2.

2024: model training only
2025: probability calibration and decision-threshold selection only
2026: untouched final evaluation only
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import accuracy_score, balanced_accuracy_score, brier_score_loss, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


TEAM_ALIASES = {
    "福岡ソフトバンク": "ソフトバンク", "福岡ソフトバンクホークス": "ソフトバンク",
    "北海道日本ハム": "日本ハム", "北海道日本ハムファイターズ": "日本ハム",
    "埼玉西武": "西武", "千葉ロッテ": "ロッテ", "東北楽天": "楽天",
    "オリックス・バファローズ": "オリックス", "横浜DeNA": "DeNA",
    "東京ヤクルト": "ヤクルト", "読売": "巨人", "広島東洋": "広島",
}

NUMERIC_FEATURES = [
    "home", "games_before", "season_win_rate", "win_rate_5", "win_rate_10", "win_rate_20",
    "run_diff_5", "run_diff_10", "run_diff_20", "runs_for_10", "runs_against_10",
    "h2h_win_rate", "h2h_run_diff", "rest_days",
]
CATEGORICAL_FEATURES = ["opponent", "month"]


def first(row, *names, default=None):
    for name in names:
        value = row.get(name)
        if value is not None and str(value).strip() not in {"", "nan", "None", "-", "—"}:
            return value
    return default


def number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return np.nan


def team_name(value):
    value = str(value or "").strip()
    return TEAM_ALIASES.get(value, value)


def load_games(path: Path) -> pd.DataFrame:
    rows = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for row in rows:
        date = pd.to_datetime(first(row, "date", "試合日"), errors="coerce")
        if pd.isna(date):
            continue
        opponent = team_name(first(row, "opponent", "対戦相手", default="不明"))
        hawks_score = number(first(
            row, "hawks_score", "ホークス得点", "runs_for", "score_for"
        ))
        opponent_score = number(first(
            row, "opponent_score", "相手得点", "runs_against", "score_against"
        ))
        venue = str(first(row, "home_away", "ホーム・ビジター", "venue_side", default="")).lower()
        if venue in {"home", "ホーム", "h", "1"}:
            home = 1
        elif venue in {"away", "visitor", "ビジター", "a", "0"}:
            home = 0
        else:
            home_team = team_name(first(row, "home", "ホーム", "home_team", default=""))
            home = int(home_team == "ソフトバンク") if home_team else 0
        out.append({
            "date": date.normalize(), "opponent": opponent, "home": home,
            "hawks_score": hawks_score, "opponent_score": opponent_score,
        })
    df = pd.DataFrame(out).sort_values(["date", "opponent"]).drop_duplicates(
        ["date", "opponent"], keep="last"
    ).reset_index(drop=True)
    df["season"] = df["date"].dt.year
    df["margin"] = df["hawks_score"] - df["opponent_score"]
    df["target"] = np.where(df["margin"] > 0, 1, np.where(df["margin"] < 0, 0, np.nan))
    return df


def rolling_mean(values, n, default=0.0):
    values = list(values)[-n:]
    return float(np.mean(values)) if values else default


def make_features(games: pd.DataFrame) -> pd.DataFrame:
    records, history = [], []
    for _, game in games.iterrows():
        prior = [x for x in history if x["season"] == game["season"]]
        h2h = [x for x in prior if x["opponent"] == game["opponent"]]
        wins = [float(x["margin"] > 0) for x in prior if x["margin"] != 0]
        margins = [x["margin"] for x in prior]
        h2h_wins = [float(x["margin"] > 0) for x in h2h if x["margin"] != 0]
        prior_date = history[-1]["date"] if history else None
        rest = min(max((game["date"] - prior_date).days - 1, 0), 14) if prior_date is not None else 3
        rec = game.to_dict()
        rec.update({
            "month": str(game["date"].month), "games_before": len(prior),
            "season_win_rate": rolling_mean(wins, 999, .5),
            "win_rate_5": rolling_mean(wins, 5, .5), "win_rate_10": rolling_mean(wins, 10, .5),
            "win_rate_20": rolling_mean(wins, 20, .5),
            "run_diff_5": rolling_mean(margins, 5), "run_diff_10": rolling_mean(margins, 10),
            "run_diff_20": rolling_mean(margins, 20),
            "runs_for_10": rolling_mean([x["hawks_score"] for x in prior], 10, 3.5),
            "runs_against_10": rolling_mean([x["opponent_score"] for x in prior], 10, 3.5),
            "h2h_win_rate": rolling_mean(h2h_wins, 10, .5),
            "h2h_run_diff": rolling_mean([x["margin"] for x in h2h], 10), "rest_days": rest,
        })
        records.append(rec)
        if not np.isnan(game["margin"]):
            history.append(game.to_dict())
    return pd.DataFrame(records)


def preprocessor():
    numeric = Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())])
    category = Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                         ("onehot", OneHotEncoder(handle_unknown="ignore"))])
    return ColumnTransformer([("num", numeric, NUMERIC_FEATURES),
                              ("cat", category, CATEGORICAL_FEATURES)])


def fit_models(train):
    classifier = Pipeline([("prep", preprocessor()),
                           ("model", LogisticRegression(class_weight="balanced", max_iter=3000, C=.5))])
    margin = Pipeline([("prep", preprocessor()), ("model", Ridge(alpha=8.0))])
    x = train[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    classifier.fit(x, train["target"].astype(int))
    margin.fit(x, train["margin"])
    return classifier, margin


def logit(p):
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p)).reshape(-1, 1)


def fit_platt(raw_probability, y):
    calibrator = LogisticRegression(C=1e6, max_iter=2000)
    calibrator.fit(logit(raw_probability), np.asarray(y, dtype=int))
    return calibrator


def calibrated(calibrator, raw_probability):
    return calibrator.predict_proba(logit(raw_probability))[:, 1]


def select_threshold(probability, y):
    best = (0.5, -1.0, -1.0)
    for threshold in np.arange(.30, .701, .005):
        pred = (probability >= threshold).astype(int)
        score = balanced_accuracy_score(y, pred)
        accuracy = accuracy_score(y, pred)
        candidate = (float(threshold), float(score), float(accuracy))
        if (candidate[1], candidate[2], -abs(candidate[0] - .5)) > (best[1], best[2], -abs(best[0] - .5)):
            best = candidate
    return best[0]


def raw_threshold(value):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return np.nan
    text = str(value).strip().replace("．", ".")
    if "半" in text:
        left = text.split("半", 1)[0]
        return (float(left) if left else 0.0) + .5
    try:
        return float(text)
    except ValueError:
        return np.nan


def add_handicaps(df, cache_path: Path):
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    columns = {name: [] for name in [
        "hawks_handicap", "opponent_handicap", "hawks_handicap_raw", "opponent_handicap_raw",
        "giving_side", "adjusted_margin", "handicap_result", "predicted_handicap_result",
        "handicap_hit",
    ]}
    for _, row in df.iterrows():
        item = cache.get(row["date"].strftime("%Y-%m-%d"), {}) or {}
        if row["home"] == 1:
            hawks = item.get("home_handicap"); opp = item.get("away_handicap")
            hawks_raw = item.get("home_handicap_raw"); opp_raw = item.get("away_handicap_raw")
        else:
            hawks = item.get("away_handicap"); opp = item.get("home_handicap")
            hawks_raw = item.get("away_handicap_raw"); opp_raw = item.get("home_handicap_raw")
        hawks_limit = raw_threshold(hawks_raw if hawks_raw is not None else hawks)
        opp_limit = raw_threshold(opp_raw if opp_raw is not None else opp)
        if not np.isnan(hawks_limit):
            giving, adjusted, predicted = "ソフトバンク", row["margin"] - hawks_limit, row["predicted_margin"] - hawks_limit
        elif not np.isnan(opp_limit):
            giving, adjusted, predicted = row["opponent"], row["margin"] + opp_limit, row["predicted_margin"] + opp_limit
        else:
            giving, adjusted, predicted = "", np.nan, np.nan
        result = "対象外" if np.isnan(adjusted) else ("勝" if adjusted > 0 else "敗" if adjusted < 0 else "分")
        predicted_result = "" if np.isnan(predicted) else ("勝" if predicted > 0 else "敗")
        hit = np.nan if result in {"対象外", "分"} else predicted_result == result
        values = [hawks, opp, hawks_raw, opp_raw, giving, adjusted, result, predicted_result, hit]
        for name, value in zip(columns, values): columns[name].append(value)
    for name, values in columns.items(): df[name] = values
    return df


def metrics(label, frame):
    y = frame["target"].astype(int)
    pred = frame["prediction"].astype(int)
    hp = frame["handicap_hit"].dropna()
    print(f"\n========== {label} ==========")
    print(f"試合数: {len(frame)}")
    print(f"通常的中率: {accuracy_score(y, pred)*100:.1f}% ({int((y == pred).sum())}/{len(y)})")
    print(f"勝予測/敗予測: {int(pred.sum())}/{int((1-pred).sum())}")
    print(f"Brier: {brier_score_loss(y, frame['calibrated_probability']):.4f}")
    print(f"LogLoss: {log_loss(y, frame['calibrated_probability'], labels=[0,1]):.4f}")
    if len(hp): print(f"ハンデ的中率: {hp.astype(bool).mean()*100:.1f}% ({int(hp.astype(bool).sum())}/{len(hp)})")
    else: print("ハンデ的中率: 対象なし")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/hawks_games_starter_history.json")
    parser.add_argument("--cache", default="data/handicap_cache.json")
    parser.add_argument("--output", default="data/handicap_backtest_v2.csv")
    args = parser.parse_args()
    frame = make_features(load_games(Path(args.input)))
    frame = frame.dropna(subset=["target", "margin"]).reset_index(drop=True)
    train, validation, test = (frame[frame.season == year].copy() for year in [2024, 2025, 2026])
    if min(len(train), len(validation), len(test)) == 0:
        raise SystemExit("2024・2025・2026のいずれかの試合データがありません")
    classifier, margin_model = fit_models(train)
    features = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    val_raw = classifier.predict_proba(validation[features])[:, 1]
    calibrator = fit_platt(val_raw, validation["target"])
    val_cal = calibrated(calibrator, val_raw)
    threshold = select_threshold(val_cal, validation["target"].astype(int))
    for split, name in [(validation, "2025校正"), (test, "2026最終検証")]:
        split["raw_probability"] = classifier.predict_proba(split[features])[:, 1]
        split["calibrated_probability"] = calibrated(calibrator, split["raw_probability"])
        split["prediction"] = (split["calibrated_probability"] >= threshold).astype(int)
        split["predicted_margin"] = margin_model.predict(split[features])
        split["AI予測"] = np.where(split["prediction"] == 1, "勝", "敗")
        split["AI勝率"] = np.where(split["prediction"] == 1, split["calibrated_probability"],
                                  1 - split["calibrated_probability"]) * 100
        add_handicaps(split, Path(args.cache))
        split["通常的中"] = split["prediction"] == split["target"].astype(int)
        metrics(name, split)
    result = pd.concat([validation.assign(split="2025_calibration"),
                        test.assign(split="2026_final_test")], ignore_index=True)
    rename = {"date": "試合日", "opponent": "対戦相手", "hawks_score": "ホークス得点",
              "opponent_score": "相手得点", "hawks_handicap": "ホークスハンデ",
              "opponent_handicap": "相手ハンデ", "hawks_handicap_raw": "ホークスハンデ原表記",
              "opponent_handicap_raw": "相手ハンデ原表記", "giving_side": "ハンデを出す側",
              "adjusted_margin": "ハンデ補正後点差", "handicap_result": "ハンデ勝敗",
              "predicted_handicap_result": "AIハンデ予測", "handicap_hit": "ハンデ的中",
              "raw_probability": "未校正ホークス勝率", "calibrated_probability": "校正済ホークス勝率",
              "predicted_margin": "予測点差"}
    result = result.rename(columns=rename)
    result["試合日"] = pd.to_datetime(result["試合日"]).dt.strftime("%Y-%m-%d")
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"\n判定閾値（2025のみで決定）: {threshold:.3f}")
    print(f"出力: {args.output}")
    print("注意: 2026年は学習・校正・閾値選択に一切使用していません。")


if __name__ == "__main__":
    main()
