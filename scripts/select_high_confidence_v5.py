#!/usr/bin/env python3
"""V5: select high-confidence NPB games from pregame-only matchup evidence.

2024: model training
2025: calibration and selection-rule decision
2026: untouched final evaluation
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, brier_score_loss, log_loss

from backtest_all_teams_v4 import (
    BASE, ROLL, CAT, features, load_games, logit, models, official_ranges,
)

EXTRA = [
    "pair_games", "pair_home_rate", "home_season_rate", "away_season_rate",
    "home_venue_rate", "away_venue_rate", "season_games_min",
]


def wilson_lower(hits: int, games: int, z: float = 1.96) -> float:
    if games <= 0:
        return 0.0
    p = hits / games
    den = 1 + z * z / games
    return (p + z * z / (2 * games) - z * np.sqrt((p * (1-p) + z*z/(4*games))/games)) / den


def add_pregame_context(df: pd.DataFrame) -> pd.DataFrame:
    pair = defaultdict(list)
    season = defaultdict(list)
    venue = defaultdict(list)
    rows = []
    for _, g in df.sort_values(["date", "home", "away"]).iterrows():
        h, a, y, v = g.home, g.away, int(g.season), str(g.venue)
        ph = pair[(h, a)]
        sh, sa = season[(y, h)], season[(y, a)]
        vh, va = venue[(h, v)], venue[(a, v)]
        row = {
            "date": g.date, "home": h, "away": a,
            "pair_games": len(ph),
            "pair_home_rate": float(np.mean(ph)) if ph else .5,
            "home_season_rate": float(np.mean(sh)) if sh else .5,
            "away_season_rate": float(np.mean(sa)) if sa else .5,
            "home_venue_rate": float(np.mean(vh)) if vh else .5,
            "away_venue_rate": float(np.mean(va)) if va else .5,
            "season_games_min": min(len(sh), len(sa)),
        }
        rows.append(row)
        win = float(g.target)
        pair[(h, a)].append(win)
        pair[(a, h)].append(1-win)
        season[(y, h)].append(win); season[(y, a)].append(1-win)
        venue[(h, v)].append(win); venue[(a, v)].append(1-win)
    return pd.DataFrame(rows)


def predict_sets(data: pd.DataFrame):
    nums = BASE + ROLL + EXTRA
    X = nums + CAT
    tr = data[data.season == 2024]
    va = data[data.season == 2025].copy()
    te = data[data.season == 2026].copy()

    lin, tree = models(nums)
    lin.fit(tr[X], tr.target.astype(int)); tree.fit(tr[X], tr.target.astype(int))
    pl = lin.predict_proba(va[X])[:, 1]; pt = tree.predict_proba(va[X])[:, 1]
    _, weight = min(
        (brier_score_loss(va.target, .05*i*pl + (1-.05*i)*pt), .05*i)
        for i in range(21)
    )
    raw = weight*pl + (1-weight)*pt
    calibrator = LogisticRegression(C=1e6, max_iter=2000).fit(logit(raw), va.target.astype(int))
    pv = calibrator.predict_proba(logit(raw))[:, 1]
    threshold = max(
        (balanced_accuracy_score(va.target, (pv >= t).astype(int)), t)
        for t in np.arange(.40, .651, .005)
    )[1]

    both = pd.concat([tr, va])
    lin, tree = models(nums)
    lin.fit(both[X], both.target.astype(int)); tree.fit(both[X], both.target.astype(int))
    rawt = weight*lin.predict_proba(te[X])[:, 1] + (1-weight)*tree.predict_proba(te[X])[:, 1]
    pt = calibrator.predict_proba(logit(rawt))[:, 1]

    for frame, probs in ((va, pv), (te, pt)):
        frame["prob_home"] = probs
        frame["prediction"] = (probs >= threshold).astype(int)
        frame["confidence"] = np.where(frame.prediction == 1, probs, 1-probs)
        frame["predicted_historical_rate"] = np.where(
            frame.prediction == 1, frame.pair_home_rate, 1-frame.pair_home_rate
        )
        frame["form_agreement"] = np.where(
            frame.prediction == 1,
            frame.home_season_rate >= frame.away_season_rate,
            frame.away_season_rate >= frame.home_season_rate,
        )
        frame["hit"] = frame.prediction == frame.target.astype(int)
    return va, te, weight, threshold


def mask_rule(df, rule):
    m = (
        (df.confidence >= rule["confidence"]) &
        (df.pair_games >= rule["pair_games"]) &
        (df.predicted_historical_rate >= rule["historical_rate"]) &
        (df.season_games_min >= rule["season_games"])
    )
    if rule["form_agreement"]:
        m &= df.form_agreement
    return m


def choose_rule(validation):
    candidates = []
    for conf in np.arange(.52, .751, .01):
        for pg in (0, 3, 5, 8, 12):
            for hr in (.50, .55, .60, .65, .70):
                for sg in (0, 5, 10, 20):
                    for agree in (False, True):
                        rule = dict(confidence=float(conf), pair_games=pg,
                                    historical_rate=hr, season_games=sg,
                                    form_agreement=agree)
                        selected = validation[mask_rule(validation, rule)]
                        n = len(selected)
                        if n < 20:
                            continue
                        hits = int(selected.hit.sum())
                        candidates.append((hits/n, wilson_lower(hits, n), n, rule))
    if not candidates:
        return None, None
    qualified = [x for x in candidates if x[0] >= .75 and x[1] >= .60]
    # 75%以上を満たす中で対象試合数を最大化。なければWilson下限が最大の規則。
    best = max(qualified, key=lambda x: (x[2], x[1])) if qualified else max(candidates, key=lambda x: (x[1], x[2]))
    return best[3], best


def summarize(label, df):
    n = len(df); hits = int(df.hit.sum()) if n else 0
    return {
        "period": label, "games": n, "hits": hits,
        "accuracy": hits/n*100 if n else np.nan,
        "wilson_lower_95": wilson_lower(hits, n)*100 if n else np.nan,
        "average_model_probability": df.confidence.mean()*100 if n else np.nan,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", default="data/all_games_2024_2026.json")
    ap.add_argument("--hawks", default="data/hawks_games_starter_history_corrected.json")
    ap.add_argument("--out", default="data")
    args = ap.parse_args()

    ranges = official_ranges(args.hawks)
    raw = load_games(args.games, ranges)
    base = features(raw)
    context = add_pregame_context(raw)
    data = base.merge(context, on=["date", "home", "away"], how="left", validate="one_to_one")
    va, te, weight, threshold = predict_sets(data)
    rule, validation_result = choose_rule(va)
    if rule is None:
        raise SystemExit("2025年で最低20試合を満たす選定規則がありません。")

    va["high_confidence"] = mask_rule(va, rule)
    te["high_confidence"] = mask_rule(te, rule)
    va_sel = va[va["high_confidence"]].copy()
    te_sel = te[te["high_confidence"]].copy()

    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    columns = [
        "date", "home", "away", "home_score", "away_score", "venue",
        "prob_home", "prediction", "confidence", "pair_games",
        "predicted_historical_rate", "home_season_rate", "away_season_rate",
        "form_agreement", "high_confidence", "hit",
    ]
    pd.concat([
        va.assign(split="2025_rule_selection"),
        te.assign(split="2026_final_test"),
    ])[columns + ["split"]].to_csv(out/"high_confidence_v5_all.csv", index=False, encoding="utf-8-sig")
    te_sel[columns].to_csv(out/"high_confidence_v5_2026.csv", index=False, encoding="utf-8-sig")
    report = pd.DataFrame([summarize("2025_rule_selection", va_sel), summarize("2026_final_test", te_sel)])
    report.to_csv(out/"high_confidence_v5_summary.csv", index=False, encoding="utf-8-sig")

    print("モデル線形比率:", weight)
    print("勝敗閾値:", threshold)
    print("2025年だけで固定した選定規則:", rule)
    print(report.to_string(index=False))
    print("\n採択基準: 2026年20試合以上・的中率75%以上・Wilson下限60%以上")
    deploy = len(te_sel) >= 20 and te_sel.hit.mean() >= .75 and wilson_lower(int(te_sel.hit.sum()), len(te_sel)) >= .60
    print("本番採択:", "可" if deploy else "不可")
    print("注意: 2026年の結果は選定規則の作成に使用していません。")


if __name__ == "__main__":
    main()
