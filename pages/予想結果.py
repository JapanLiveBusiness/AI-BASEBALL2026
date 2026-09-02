from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from prediction_metrics import build_prediction_metrics
from studio_theme import apply_studio_theme, render_hero, render_nav_links, render_section, render_topbar

PROD_DATA_DIR = Path("/app/data")
REPO_DATA_DIR = Path(__file__).resolve().parents[1] / "data"

st.set_page_config(
    page_title="予想結果 | AI BASEBALL STUDIO",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def active_data_dir() -> Path:
    return PROD_DATA_DIR if (PROD_DATA_DIR / "game_history.json").exists() else REPO_DATA_DIR


def pct(value):
    return "--" if value is None else f"{float(value):.1f}%"


def brier_label(value):
    return "--" if value is None else f"{float(value):.4f}"


apply_studio_theme()
render_topbar("RESULTS / VERIFIED")
render_hero(
    "予想結果",
    "試合前に固定したAI予測と実際の勝敗を照合します。結果確定後に予測値を書き換えず、的中率と確率精度を検証します。",
    kicker="AI BASEBALL STUDIO / VERIFICATION",
    accent="結果",
)
render_nav_links()

metrics = build_prediction_metrics(active_data_dir())
games = metrics.get("games") or []
verified_count = int(metrics.get("verified_count") or 0)
hits = int(metrics.get("hits") or 0)
hit_rate = metrics.get("hit_rate")
brier = metrics.get("brier_score")
misses = verified_count - hits

high_conf = [g for g in games if abs(float(g.get("probability", 50)) - 50) >= 10]
high_hits = sum(1 for g in high_conf if g.get("hit"))
high_rate = (high_hits / len(high_conf) * 100.0) if high_conf else None

st.markdown(
    """
<style>
.result-kpis{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:14px 0 20px}.result-kpi{background:#fffdf8;border:1px solid #ddd5c8;border-radius:13px;padding:15px}.result-kpi span{display:block;font-size:8px;letter-spacing:.16em;color:#a77e11;font-weight:900}.result-kpi strong{display:block;font-size:24px;margin-top:7px}.result-table{display:flex;flex-direction:column;gap:8px}.result-row{display:grid;grid-template-columns:120px 1fr 110px 90px 90px;align-items:center;gap:10px;background:#fffdf8;border:1px solid #ddd5c8;border-radius:12px;padding:12px 14px}.result-row.hit{border-left:4px solid #2f8f57}.result-row.miss{border-left:4px solid #b64848}.result-date{font-size:10px;color:#746f66}.result-match strong{font-size:14px}.result-match span{display:block;font-size:9px;color:#746f66;margin-top:3px}.result-prob{font-weight:900;text-align:right}.result-actual{text-align:center;font-weight:900}.result-badge{justify-self:end;border-radius:999px;padding:5px 9px;font-size:9px;font-weight:950}.result-badge.hit{background:#e8f6ee;color:#217043}.result-badge.miss{background:#fdecec;color:#9d3636}.empty-results{padding:28px;background:#fffdf8;border:1px dashed #d8d0c3;border-radius:14px;color:#746f66;text-align:center;font-size:12px}.verify-note{padding:11px 13px;border-radius:10px;background:#191919;color:#fff;font-size:10px;line-height:1.6;margin-bottom:16px}.verify-note b{color:#f1c40f}
@media(max-width:980px){.result-kpis{grid-template-columns:repeat(3,1fr)}.result-row{grid-template-columns:100px 1fr 90px 72px}.result-badge{display:none}}@media(max-width:650px){.result-kpis{grid-template-columns:1fr 1fr}.result-row{grid-template-columns:1fr 78px}.result-date{grid-column:1/-1}.result-match{grid-column:1}.result-prob{grid-column:2}.result-actual{grid-column:1/-1;text-align:left}.result-badge{display:none}}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    f"""
<div class="result-kpis">
  <div class="result-kpi"><span>VERIFIED</span><strong>{verified_count}</strong></div>
  <div class="result-kpi"><span>HITS</span><strong>{hits}</strong></div>
  <div class="result-kpi"><span>MISSES</span><strong>{misses}</strong></div>
  <div class="result-kpi"><span>HIT RATE</span><strong>{pct(hit_rate)}</strong></div>
  <div class="result-kpi"><span>BRIER SCORE</span><strong>{brier_label(brier)}</strong></div>
</div>
<div class="verify-note"><b>高信頼帯</b>：60%以上または40%以下の予測を対象にした的中率は <b>{pct(high_rate)}</b>（{high_hits}/{len(high_conf)}）です。Brier Scoreは低いほど確率予測の精度が高い指標です。</div>
""",
    unsafe_allow_html=True,
)

render_section("VERIFIED RESULTS", "試合別の予想結果")

if not games:
    st.markdown(
        '<div class="empty-results">検証可能な終了試合がまだありません。試合結果が保存されると自動的に集計されます。</div>',
        unsafe_allow_html=True,
    )
else:
    rows = []
    for game in sorted(games, key=lambda x: str(x.get("date") or ""), reverse=True):
        hit = bool(game.get("hit"))
        cls = "hit" if hit else "miss"
        badge = "的中" if hit else "外れ"
        rows.append(
            f'''<div class="result-row {cls}">
  <div class="result-date">{game.get('date') or '--'}</div>
  <div class="result-match"><strong>ソフトバンク vs {game.get('opponent') or '--'}</strong><span>GAME ID: {game.get('game_id') or '--'}</span></div>
  <div class="result-prob">AI {pct(game.get('probability'))}</div>
  <div class="result-actual">実績 {game.get('result') or '--'}</div>
  <div class="result-badge {cls}">{badge}</div>
</div>'''
        )
    st.markdown(f'<div class="result-table">{"".join(rows)}</div>', unsafe_allow_html=True)

st.caption("試合前予測は固定値として検証し、引き分け・未終了試合は的中率計算から除外します。")


@st.cache_data(max_entries=2)
def load_historical_report(path: str):
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


historical_path = active_data_dir() / "historical_backtest_report.json"
if not historical_path.exists():
    historical_path = REPO_DATA_DIR / "historical_backtest_report.json"
historical = load_historical_report(str(historical_path))

render_section("HISTORICAL VALIDATION", "過去データ・年度別・モデル別バックテスト")
if not historical:
    st.info("長期バックテスト結果はまだ生成されていません。")
else:
    model_labels = {
        "historical_baseline": "過去勝率ベースライン",
        "logistic_rolling": "ロジスティック回帰",
        "gradient_rolling": "勾配ブースティング",
    }
    overall = historical.get("overall") or []
    recommended = historical.get("recommended_model")
    with st.container(horizontal=True):
        st.metric("元データ", f"{int(historical.get('source_games') or 0):,}試合", border=True)
        st.metric("公式戦評価対象", f"{int(historical.get('evaluated_games') or 0):,}試合", border=True)
        st.metric("検証年度", f"{len(historical.get('evaluated_seasons') or [])}シーズン", border=True)
        st.metric("推奨モデル", model_labels.get(recommended, recommended or "--"), border=True)

    overall_rows = [
        {
            "モデル": model_labels.get(row.get("model"), row.get("model")),
            "検証試合": int(row.get("games") or 0),
            "的中率": float(row.get("accuracy") or 0),
            "Brier Score": float(row.get("brier") or 0),
            "LogLoss": float(row.get("log_loss") or 0),
        }
        for row in overall
    ]
    st.dataframe(
        overall_rows,
        hide_index=True,
        column_config={
            "的中率": st.column_config.NumberColumn(format="%.2f%%"),
            "Brier Score": st.column_config.NumberColumn(format="%.4f"),
            "LogLoss": st.column_config.NumberColumn(format="%.4f"),
        },
        key="historical_overall_models",
    )

    season_rows = [
        {
            "年度": int(row.get("season") or 0),
            "モデル": model_labels.get(row.get("model"), row.get("model")),
            "学習期間": f"〜{int(row.get('train_through') or 0)}",
            "試合数": int(row.get("games") or 0),
            "的中率": float(row.get("accuracy") or 0),
            "Brier Score": float(row.get("brier") or 0),
            "LogLoss": float(row.get("log_loss") or 0),
        }
        for row in historical.get("by_season") or []
    ]
    st.dataframe(
        season_rows,
        hide_index=True,
        column_config={
            "的中率": st.column_config.NumberColumn(format="%.2f%%"),
            "Brier Score": st.column_config.NumberColumn(format="%.4f"),
            "LogLoss": st.column_config.NumberColumn(format="%.4f"),
        },
        key="historical_by_season",
    )
    st.caption(
        f"対象期間: {historical.get('source_start', '--')}〜{historical.get('source_end', '--')}。"
        "各年度は、それ以前の年度だけで学習するウォークフォワード方式です。引き分けと未来情報は除外しています。"
    )
