#!/usr/bin/env python3
"""Audit every handicap backtest CSV without tuning on the final-test rows."""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd


def col(df, *names):
    return next((x for x in names if x in df.columns), None)


def bools(series):
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().map({"true": True, "false": False, "1": True, "0": False})


def rate(series):
    x = bools(series).dropna()
    return (float(x.mean() * 100), int(x.sum()), len(x)) if len(x) else (np.nan, 0, 0)


def summarize(path):
    df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    split = col(df, "split")
    date = col(df, "date", "試合日")
    opponent = col(df, "opponent", "対戦相手")
    venue = col(df, "venue", "球場")
    home = col(df, "home")
    pred = col(df, "AI予測")
    confidence = col(df, "AI勝率")
    normal_hit = col(df, "通常的中")
    handicap_hit = col(df, "handicap_hit", "ハンデ的中")
    margin = col(df, "predicted_margin", "予測点差")
    selected = col(df, "厳選予測")
    if not normal_hit:
        return [], [f"## {path.name}\n\n通常的中列がないため対象外。\n"]
    if date:
        df[date] = pd.to_datetime(df[date], errors="coerce")
        df["監査年度"] = df[date].dt.year
        df["監査月"] = df[date].dt.month
    rows, sections = [], [f"## {path.name}\n"]

    def add(label, group, axis="全体"):
        nrate, hits, n = rate(group[normal_hit])
        hrate, hhits, hn = rate(group[handicap_hit]) if handicap_hit else (np.nan, 0, 0)
        wins = int((group[pred] == "勝").sum()) if pred else 0
        losses = int((group[pred] == "敗").sum()) if pred else 0
        rows.append({"file": path.name, "axis": axis, "label": str(label), "games": n,
                     "hits": hits, "accuracy": nrate, "win_predictions": wins,
                     "loss_predictions": losses, "handicap_games": hn,
                     "handicap_hits": hhits, "handicap_accuracy": hrate})

    add("全体", df)
    dimensions = []
    if split: dimensions.append(("期間", split))
    if "監査年度" in df: dimensions.append(("年度", "監査年度"))
    if "監査月" in df: dimensions.append(("月", "監査月"))
    if opponent: dimensions.append(("対戦相手", opponent))
    if venue: dimensions.append(("球場", venue))
    if home: dimensions.append(("ホーム区分", home))
    for axis, key in dimensions:
        for label, group in df.groupby(key, dropna=False):
            add(label, group, axis)

    if confidence:
        df["監査勝率帯"] = pd.cut(df[confidence], [0, 55, 60, 65, 70, 75, 80, 90, 101],
                                  right=False, include_lowest=True)
        for label, group in df.groupby("監査勝率帯", observed=True):
            add(label, group, "AI勝率帯")
    if pred and margin:
        agree = ((df[pred] == "勝") & (df[margin] > 0)) | ((df[pred] == "敗") & (df[margin] < 0))
        df["監査モデル一致"] = np.where(agree, "一致", "不一致")
        for label, group in df.groupby("監査モデル一致"):
            add(label, group, "勝敗・点差モデル")
    if selected:
        mask = bools(df[selected]).fillna(False)
        add("厳選", df[mask], "厳選条件")
        add("非厳選", df[~mask], "厳選条件")

    local = pd.DataFrame([x for x in rows if x["file"] == path.name])
    sections.append("|区分|対象|試合|通常的中率|勝/敗予測|ハンデ的中率|\n")
    sections.append("|---|---:|---:|---:|---:|---:|\n")
    for _, r in local[local.axis.isin(["全体", "期間", "厳選条件"])].iterrows():
        ha = "-" if pd.isna(r.handicap_accuracy) else f"{r.handicap_accuracy:.1f}%"
        sections.append(f"|{r.axis}:{r.label}| |{r.games}|{r.accuracy:.1f}%|"
                        f"{r.win_predictions}/{r.loss_predictions}|{ha}|\n")
    sections.append("\n")
    return rows, sections


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default="data/handicap_backtest*.csv")
    ap.add_argument("--summary", default="data/model_audit_summary.csv")
    ap.add_argument("--report", default="data/model_audit_report.md")
    args = ap.parse_args()
    paths = sorted(Path(".").glob(args.glob))
    if not paths:
        raise SystemExit(f"対象なし: {args.glob}")
    all_rows, report = [], ["# BASEBALL AI NEXT 自動モデル監査\n\n",
                            "2026年は評価のみ。結果を用いた閾値変更は禁止。\n\n"]
    for path in paths:
        rows, text = summarize(path)
        all_rows.extend(rows); report.extend(text)
    summary = pd.DataFrame(all_rows)
    Path(args.summary).parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.summary, index=False, encoding="utf-8-sig")
    Path(args.report).write_text("".join(report), encoding="utf-8")
    print(f"対象CSV: {len(paths)}")
    print(f"集計行: {len(summary)}")
    print(f"CSV: {args.summary}")
    print(f"レポート: {args.report}")
    final = summary[(summary.axis == "期間") & summary.label.astype(str).str.contains("2026")]
    if len(final):
        print("\n========== 2026比較 ==========")
        print(final[["file", "games", "accuracy", "win_predictions", "loss_predictions",
                     "handicap_accuracy"]].to_string(index=False))


if __name__ == "__main__":
    main()
