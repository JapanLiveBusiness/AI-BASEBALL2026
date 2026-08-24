#!/usr/bin/env python3
"""BASEBALL AI NEXT V3: leakage-safe official-game backtest.

2024 + earlier 2025 -> time-series OOF predictions for 2025
2025 OOF               -> ensemble, Platt calibration, thresholds
2024 + 2025            -> final model fitting
2026                   -> untouched final test
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import accuracy_score, balanced_accuracy_score, brier_score_loss, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backtest_with_handicap_v2 import add_handicaps, first, number, rolling_mean, team_name

OFFICIAL_TYPES = {"regular", "interleague"}
NUM = [
    "home", "games_before", "season_win_rate", "win_rate_5", "win_rate_10", "win_rate_20",
    "run_diff_5", "run_diff_10", "run_diff_20", "runs_for_5", "runs_for_10",
    "runs_against_5", "runs_against_10", "h2h_win_rate", "h2h_run_diff", "rest_days",
    "starter_win_diff", "starter_recent_diff", "starter_run_diff_advantage",
]
CAT = ["opponent", "venue", "hawks_starter", "opponent_starter", "month"]
FEATURES = NUM + CAT


def load_official(path: Path) -> pd.DataFrame:
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for r in raw:
        if str(r.get("game_type")) not in OFFICIAL_TYPES:
            continue
        date = pd.to_datetime(r.get("date"), errors="coerce")
        if pd.isna(date):
            continue
        margin = number(first(r, "run_diff", default=np.nan))
        runs_for = number(first(r, "runs_for", "hawks_score", default=np.nan))
        runs_against = number(first(r, "runs_against", "opponent_score", default=np.nan))
        if np.isnan(margin) and not np.isnan(runs_for) and not np.isnan(runs_against):
            margin = runs_for - runs_against
        starter = r.get("starter_history") or {}
        rows.append({
            "date": date.normalize(), "season": int(r.get("season", date.year)),
            "game_type": r.get("game_type"), "opponent": team_name(r.get("opponent")),
            "home": int(str(r.get("home_away", "")).lower() == "home"),
            "venue": str(r.get("venue") or "不明"),
            "hawks_starter": str(r.get("hawks_starter") or "不明"),
            "opponent_starter": str(r.get("opponent_starter") or "不明"),
            "hawks_score": runs_for, "opponent_score": runs_against, "margin": margin,
            "starter_win_diff": number(starter.get("win_pct_diff", 0.0)),
            "starter_recent_diff": number(starter.get("recent3_diff", 0.0)),
            "starter_run_diff_advantage": number(starter.get("run_diff_advantage", 0.0)),
        })
    df = pd.DataFrame(rows).sort_values(["date", "opponent"]).drop_duplicates(
        ["date", "opponent"], keep="last"
    ).reset_index(drop=True)
    df["target"] = np.where(df.margin > 0, 1, np.where(df.margin < 0, 0, np.nan))
    return df.dropna(subset=["target", "margin"]).reset_index(drop=True)


def feature_engineer(games: pd.DataFrame) -> pd.DataFrame:
    out, history = [], []
    for _, g in games.iterrows():
        season_prior = [x for x in history if x["season"] == g["season"]]
        all_prior = history
        h2h = [x for x in all_prior if x["opponent"] == g["opponent"]][-20:]
        wins = [float(x["margin"] > 0) for x in season_prior]
        margins = [x["margin"] for x in season_prior]
        last_date = all_prior[-1]["date"] if all_prior else None
        rest = min(max((g["date"] - last_date).days - 1, 0), 14) if last_date is not None else 3
        row = g.to_dict()
        row.update({
            "month": str(g["date"].month), "games_before": len(season_prior),
            "season_win_rate": rolling_mean(wins, 999, .5),
            "win_rate_5": rolling_mean(wins, 5, .5), "win_rate_10": rolling_mean(wins, 10, .5),
            "win_rate_20": rolling_mean(wins, 20, .5),
            "run_diff_5": rolling_mean(margins, 5), "run_diff_10": rolling_mean(margins, 10),
            "run_diff_20": rolling_mean(margins, 20),
            "runs_for_5": rolling_mean([x["hawks_score"] for x in season_prior], 5, 3.5),
            "runs_for_10": rolling_mean([x["hawks_score"] for x in season_prior], 10, 3.5),
            "runs_against_5": rolling_mean([x["opponent_score"] for x in season_prior], 5, 3.5),
            "runs_against_10": rolling_mean([x["opponent_score"] for x in season_prior], 10, 3.5),
            "h2h_win_rate": rolling_mean([float(x["margin"] > 0) for x in h2h], 20, .5),
            "h2h_run_diff": rolling_mean([x["margin"] for x in h2h], 20), "rest_days": rest,
        })
        out.append(row)
        history.append(g.to_dict())
    return pd.DataFrame(out)


def linear_classifier():
    prep = ColumnTransformer([
        ("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("std", StandardScaler())]), NUM),
        ("cat", Pipeline([("imp", SimpleImputer(strategy="most_frequent")),
                          ("oh", OneHotEncoder(handle_unknown="ignore"))]), CAT),
    ])
    return Pipeline([("prep", prep),
                     ("model", LogisticRegression(class_weight="balanced", C=.25, max_iter=4000))])


def tree_classifier():
    prep = ColumnTransformer([
        ("num", SimpleImputer(strategy="median"), NUM),
        ("cat", Pipeline([("imp", SimpleImputer(strategy="most_frequent")),
                          ("ord", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1))]), CAT),
    ])
    return Pipeline([("prep", prep), ("model", HistGradientBoostingClassifier(
        learning_rate=.035, max_iter=180, max_leaf_nodes=9, min_samples_leaf=18,
        l2_regularization=2.0, random_state=42))])


def margin_model():
    prep = ColumnTransformer([
        ("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("std", StandardScaler())]), NUM),
        ("cat", Pipeline([("imp", SimpleImputer(strategy="most_frequent")),
                          ("oh", OneHotEncoder(handle_unknown="ignore"))]), CAT),
    ])
    return Pipeline([("prep", prep), ("model", Ridge(alpha=12.0))])


def logit(p):
    p = np.clip(np.asarray(p, float), 1e-5, 1 - 1e-5)
    return np.log(p / (1 - p)).reshape(-1, 1)


def timed_oof(train_2024, validation_2025):
    rows = []
    dates = sorted(validation_2025.date.unique())
    # Monthly expanding folds prevent any later-2025 result leaking into earlier predictions.
    months = sorted({pd.Timestamp(d).to_period("M") for d in dates})
    for month in months:
        valid = validation_2025[validation_2025.date.dt.to_period("M") == month].copy()
        prior = pd.concat([train_2024, validation_2025[validation_2025.date < valid.date.min()]])
        if len(prior) < 80 or valid.empty:
            continue
        lin, tree, margin = linear_classifier(), tree_classifier(), margin_model()
        lin.fit(prior[FEATURES], prior.target.astype(int))
        tree.fit(prior[FEATURES], prior.target.astype(int))
        margin.fit(prior[FEATURES], prior.margin)
        valid["p_linear"] = lin.predict_proba(valid[FEATURES])[:, 1]
        valid["p_tree"] = tree.predict_proba(valid[FEATURES])[:, 1]
        valid["predicted_margin"] = margin.predict(valid[FEATURES])
        rows.append(valid)
    if not rows:
        raise RuntimeError("2025年OOF予測を作成できません")
    return pd.concat(rows).sort_values("date").reset_index(drop=True)


def select_blend(oof):
    best = None
    for weight in np.arange(0, 1.01, .05):
        p = weight * oof.p_linear.to_numpy() + (1 - weight) * oof.p_tree.to_numpy()
        score = brier_score_loss(oof.target.astype(int), p)
        if best is None or score < best[1]:
            best = (float(weight), float(score))
    return best[0]


def select_decision_threshold(p, y):
    candidates = []
    for threshold in np.arange(.35, .651, .005):
        pred = (p >= threshold).astype(int)
        candidates.append((balanced_accuracy_score(y, pred), accuracy_score(y, pred), threshold))
    return float(max(candidates)[2])


def select_confidence_threshold(confidence, hit):
    # Freeze on 2025 only. Require useful coverage; never manufacture an 80% figure.
    choices = []
    for threshold in np.arange(.55, .851, .01):
        selected = confidence >= threshold
        n = int(selected.sum())
        if n >= 15:
            choices.append((float(hit[selected].mean()), n, float(threshold)))
    if not choices:
        return .80
    eligible = [x for x in choices if x[0] >= .80]
    return max(eligible, key=lambda x: (x[1], x[0]))[2] if eligible else max(choices)[2]


def report(label, df):
    hit = df["通常的中"].astype(bool)
    hh = df["handicap_hit"].dropna().astype(bool)
    chosen = df[df["厳選予測"]]
    print(f"\n========== {label} ==========")
    print(f"公式戦: {len(df)}")
    print(f"通常的中率: {hit.mean()*100:.1f}% ({int(hit.sum())}/{len(hit)})")
    print(f"勝予測/敗予測: {(df.AI予測 == '勝').sum()}/{(df.AI予測 == '敗').sum()}")
    print(f"Brier: {brier_score_loss(df.target.astype(int), df.校正済ホークス勝率):.4f}")
    print(f"LogLoss: {log_loss(df.target.astype(int), df.校正済ホークス勝率, labels=[0,1]):.4f}")
    print(f"ハンデ的中率: {hh.mean()*100:.1f}% ({int(hh.sum())}/{len(hh)})" if len(hh) else "ハンデ対象なし")
    print(f"厳選予測: {len(chosen)}")
    if len(chosen):
        print(f"厳選的中率: {chosen['通常的中'].astype(bool).mean()*100:.1f}% "
              f"({int(chosen['通常的中'].astype(bool).sum())}/{len(chosen)})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/hawks_games_starter_history.json")
    ap.add_argument("--cache", default="data/handicap_cache.json")
    ap.add_argument("--output", default="data/handicap_backtest_v3.csv")
    args = ap.parse_args()
    data = feature_engineer(load_official(Path(args.input)))
    y2024, y2025, y2026 = (data[data.season == y].copy() for y in [2024, 2025, 2026])
    oof = timed_oof(y2024, y2025)
    weight = select_blend(oof)
    raw_oof = weight * oof.p_linear.to_numpy() + (1 - weight) * oof.p_tree.to_numpy()
    calibrator = LogisticRegression(C=1e6, max_iter=2000).fit(logit(raw_oof), oof.target.astype(int))
    calibrated_oof = calibrator.predict_proba(logit(raw_oof))[:, 1]
    threshold = select_decision_threshold(calibrated_oof, oof.target.astype(int).to_numpy())
    pred_oof = (calibrated_oof >= threshold).astype(int)
    confidence_oof = np.where(pred_oof == 1, calibrated_oof, 1 - calibrated_oof)
    confidence_threshold = select_confidence_threshold(confidence_oof, pred_oof == oof.target.astype(int).to_numpy())

    final_train = pd.concat([y2024, y2025]).sort_values("date")
    lin, tree, margin = linear_classifier(), tree_classifier(), margin_model()
    lin.fit(final_train[FEATURES], final_train.target.astype(int))
    tree.fit(final_train[FEATURES], final_train.target.astype(int))
    margin.fit(final_train[FEATURES], final_train.margin)

    def finish(frame, split):
        frame = frame.copy()
        frame["p_linear"] = lin.predict_proba(frame[FEATURES])[:, 1]
        frame["p_tree"] = tree.predict_proba(frame[FEATURES])[:, 1]
        raw = weight * frame.p_linear.to_numpy() + (1 - weight) * frame.p_tree.to_numpy()
        frame["未校正ホークス勝率"] = raw
        frame["校正済ホークス勝率"] = calibrator.predict_proba(logit(raw))[:, 1]
        frame["prediction"] = (frame["校正済ホークス勝率"] >= threshold).astype(int)
        frame["AI予測"] = np.where(frame.prediction == 1, "勝", "敗")
        frame["AI勝率"] = np.where(frame.prediction == 1, frame["校正済ホークス勝率"],
                                  1 - frame["校正済ホークス勝率"]) * 100
        frame["predicted_margin"] = margin.predict(frame[FEATURES])
        frame = add_handicaps(frame, Path(args.cache))
        frame["通常的中"] = frame.prediction == frame.target.astype(int)
        frame["厳選予測"] = frame.AI勝率 >= confidence_threshold * 100
        frame["split"] = split
        return frame

    # OOF rows are the honest 2025 report; final model is never evaluated on its 2025 training rows.
    val = oof.copy()
    val["未校正ホークス勝率"] = raw_oof
    val["校正済ホークス勝率"] = calibrated_oof
    val["prediction"] = pred_oof
    val["AI予測"] = np.where(pred_oof == 1, "勝", "敗")
    val["AI勝率"] = confidence_oof * 100
    val = add_handicaps(val, Path(args.cache))
    val["通常的中"] = val.prediction == val.target.astype(int)
    val["厳選予測"] = val.AI勝率 >= confidence_threshold * 100
    val["split"] = "2025_oof_calibration"
    test = finish(y2026, "2026_final_test")
    report("2025時系列OOF", val)
    report("2026完全未使用・最終検証", test)
    out = pd.concat([val, test], ignore_index=True)
    out["date"] = pd.to_datetime(out.date).dt.strftime("%Y-%m-%d")
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"\n線形モデル比率: {weight:.2f} / 木モデル比率: {1-weight:.2f}")
    print(f"通常勝敗閾値（2025固定）: {threshold:.3f}")
    print(f"厳選信頼度閾値（2025固定）: {confidence_threshold*100:.1f}%")
    print(f"出力: {args.output}")
    print("2026年はモデル・校正・閾値・厳選条件の決定に使用していません。")


if __name__ == "__main__":
    main()
