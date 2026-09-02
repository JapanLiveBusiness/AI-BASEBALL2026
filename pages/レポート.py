from __future__ import annotations

import json
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

from studio_theme import apply_studio_theme, render_hero, render_section, render_topbar

PROD_DATA_DIR = Path("/app/data")
REPO_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
MODEL_LABELS = {
    "historical_baseline": "過去勝率ベースライン",
    "logistic_rolling": "ロジスティック回帰",
    "gradient_rolling": "勾配ブースティング",
}

st.set_page_config(page_title="統計・レポート | AI BASEBALL STUDIO", page_icon="📈", layout="wide")
apply_studio_theme()
render_topbar("MODEL REPORT")
render_hero(
    "統計・モデル検証レポート",
    "過去データを用いたウォークフォワード検証で、モデル精度・確率品質・年度別の安定性を確認します。",
    kicker="AI BASEBALL STUDIO / MODEL VALIDATION",
)


def report_path() -> Path:
    prod = PROD_DATA_DIR / "historical_backtest_report.json"
    return prod if prod.exists() and prod.stat().st_size else REPO_DATA_DIR / "historical_backtest_report.json"


def load_report() -> dict:
    try:
        value = json.loads(report_path().read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


report = load_report()
if not report:
    st.warning("長期モデル検証データがまだ生成されていません。")
    st.stop()

overall = list(report.get("overall") or [])
by_season = list(report.get("by_season") or [])
recommended = report.get("recommended_model")

k1, k2, k3, k4 = st.columns(4)
k1.metric("元データ", f"{int(report.get('source_games') or 0):,}試合")
k2.metric("評価対象", f"{int(report.get('evaluated_games') or 0):,}試合")
k3.metric("検証シーズン", f"{len(report.get('evaluated_seasons') or [])}")
k4.metric("推奨モデル", MODEL_LABELS.get(recommended, recommended or "--"))

render_section("OVERALL", "モデル別総合評価")
overall_rows = []
for row in sorted(overall, key=lambda x: float(x.get("brier") or 999)):
    overall_rows.append({
        "モデル": MODEL_LABELS.get(row.get("model"), row.get("model")),
        "検証試合": int(row.get("games") or 0),
        "一致率": float(row.get("accuracy") or 0),
        "Brier Score": float(row.get("brier") or 0),
        "LogLoss": float(row.get("log_loss") or 0),
    })
st.dataframe(
    overall_rows,
    hide_index=True,
    use_container_width=True,
    column_config={
        "一致率": st.column_config.NumberColumn(format="%.2f%%"),
        "Brier Score": st.column_config.NumberColumn(format="%.4f"),
        "LogLoss": st.column_config.NumberColumn(format="%.4f"),
    },
)

render_section("SEASON TREND", "年度別一致率")
models = sorted({str(row.get("model")) for row in by_season if row.get("model")})
fig = go.Figure()
for model in models:
    rows = sorted((r for r in by_season if str(r.get("model")) == model), key=lambda r: int(r.get("season") or 0))
    fig.add_trace(go.Scatter(
        x=[int(r.get("season") or 0) for r in rows],
        y=[float(r.get("accuracy") or 0) for r in rows],
        mode="lines+markers",
        name=MODEL_LABELS.get(model, model),
    ))
fig.update_layout(
    height=430,
    xaxis_title="シーズン",
    yaxis_title="一致率 (%)",
    hovermode="x unified",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#c7ccd4"),
    margin=dict(l=20, r=20, t=30, b=30),
)
st.plotly_chart(fig, use_container_width=True)

render_section("SEASON DETAIL", "年度別検証テーブル")
season_rows = [{
    "年度": int(row.get("season") or 0),
    "モデル": MODEL_LABELS.get(row.get("model"), row.get("model")),
    "学習期間": f"〜{int(row.get('train_through') or 0)}",
    "試合数": int(row.get("games") or 0),
    "一致率": float(row.get("accuracy") or 0),
    "Brier Score": float(row.get("brier") or 0),
    "LogLoss": float(row.get("log_loss") or 0),
} for row in by_season]
st.dataframe(
    season_rows,
    hide_index=True,
    use_container_width=True,
    column_config={
        "一致率": st.column_config.NumberColumn(format="%.2f%%"),
        "Brier Score": st.column_config.NumberColumn(format="%.4f"),
        "LogLoss": st.column_config.NumberColumn(format="%.4f"),
    },
)

st.info(
    "Brier ScoreとLogLossは低いほど確率予測の品質が高い指標です。"
    "一致率だけでなく、確率の校正品質も合わせてモデルを評価します。"
)
st.caption(
    f"検証期間: {report.get('source_start', '--')}〜{report.get('source_end', '--')} / "
    "各シーズンはそれ以前のデータだけで学習するウォークフォワード方式です。"
)
