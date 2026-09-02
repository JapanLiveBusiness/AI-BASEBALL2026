from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import html
import json

import streamlit as st

from bet_analytics import calculate_hit_rate, point_delta
from studio_theme import apply_studio_theme, render_topbar, render_hero, render_section

JST = ZoneInfo("Asia/Tokyo")
REPO_DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIRS = [Path("/app/data"), REPO_DATA_DIR]

st.set_page_config(
    page_title="AI BASEBALL STUDIO | RESEARCH",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="collapsed",
)
apply_studio_theme()


def load_json(name, fallback):
    for directory in DATA_DIRS:
        try:
            path = directory / name
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
    return fallback


def esc(value, fallback="-"):
    if value in (None, ""):
        value = fallback
    return html.escape(str(value))


predictions = load_json("today_ai_predictions.json", {"games": []})
npb_today = load_json("npb_today.json", {"games": []})
analysis_records = load_json("simulation_records.json", [])

prediction_games = predictions.get("games") or []
today_games = npb_today.get("games") or []
if not isinstance(analysis_records, list):
    analysis_records = []

settled = [r for r in analysis_records if r.get("status") == "final"]
_, _, success_rate = calculate_hit_rate(settled)
total_delta = sum(point_delta(r) for r in settled)
now = datetime.now(JST)

ranked = sorted(prediction_games, key=lambda g: g.get("rank", 999))
best = ranked[0] if ranked else {}
best_pick = esc(best.get("pick"), "データ待ち")
best_match = (
    f"{esc(best.get('home'))} vs {esc(best.get('away'))}"
    if best
    else "本日の予測データを準備中"
)
best_probability = best.get("win_probability")
best_probability_text = (
    f"{float(best_probability):.1f}%"
    if isinstance(best_probability, (int, float))
    else "--"
)

render_topbar("PRIVATE RESEARCH")
render_hero(
    "AI BASEBALL RESEARCH STUDIO",
    "NPBの試合情報・AI予測・得点補正の感度分析を、ひとつの研究画面で素早く確認できます。",
    kicker=f"NPB 2026 / {now.strftime('%Y.%m.%d')} / JST {now.strftime('%H:%M')}",
    accent="RESEARCH",
)

# Overview
left, right = st.columns([1.45, 0.75])
with left:
    render_section("OVERVIEW", "今日の分析状況")
    k1, k2 = st.columns(2)
    k3, k4 = st.columns(2)
    k1.metric("本日の試合", len(today_games))
    k2.metric("AI予測カード", len(prediction_games))
    k3.metric("確定シナリオ", len(settled))
    k4.metric("仮説成立率", f"{success_rate:.1f}%" if success_rate is not None else "-")

with right:
    st.markdown(
        f'''
<div style="height:100%;min-height:272px;background:linear-gradient(145deg,#171b21,#201a0d);border:1px solid rgba(242,201,76,.20);border-radius:22px;padding:24px;box-shadow:0 16px 38px rgba(0,0,0,.18);display:flex;flex-direction:column;justify-content:space-between;">
  <div>
    <div style="font-size:8px;letter-spacing:.24em;color:#d9b94c;font-weight:950;">TODAY'S TOP AI SIGNAL</div>
    <div style="font-size:12px;color:#8f97a3;margin-top:20px;">{best_match}</div>
    <div style="font-size:30px;font-weight:950;color:#fff;margin-top:5px;line-height:1.1;">{best_pick}</div>
  </div>
  <div style="display:flex;align-items:end;justify-content:space-between;border-top:1px solid rgba(255,255,255,.08);padding-top:18px;margin-top:20px;">
    <div><div style="font-size:8px;color:#8f97a3;">AI WIN PROBABILITY</div><div style="font-size:11px;color:#c7ccd4;margin-top:4px;">最高評価カード</div></div>
    <div style="font-size:34px;color:#f2c94c;font-weight:950;">{best_probability_text}</div>
  </div>
</div>
''',
        unsafe_allow_html=True,
    )

render_section("WORKSPACE", "研究メニュー")
w1, w2, w3, w4 = st.columns(4)
with w1:
    st.page_link("pages/試合.py", label="⚾ 試合情報", use_container_width=True)
    st.caption("対戦カード・開始時刻・試合状況")
with w2:
    st.page_link("pages/本日のAI予想.py", label="🤖 AI予測", use_container_width=True)
    st.caption("勝率・予測スコア・評価順位")
with w3:
    st.page_link("pages/BET入力.py", label="🧪 感度分析", use_container_width=True)
    st.caption("得点補正値と評価ウェイトを登録")
with w4:
    st.page_link("pages/収支マップ.py", label="📊 分析結果", use_container_width=True)
    st.caption("成立率・補正値比較・スコア推移")

rank_col, recent_col = st.columns([1.1, 0.9])

with rank_col:
    render_section("AI RANKING", "本日のAI評価")
    if not ranked:
        st.info("本日のAI予測データはまだありません。")
    else:
        for idx, game in enumerate(ranked[:5], start=1):
            home = esc(game.get("home"))
            away = esc(game.get("away"))
            pick = esc(game.get("pick"))
            probability = game.get("win_probability")
            probability_text = f"{float(probability):.1f}%" if isinstance(probability, (int, float)) else "-"
            st.markdown(
                f'''
<div style="display:grid;grid-template-columns:46px 1fr 86px;gap:12px;align-items:center;background:#12161c;border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:13px 15px;margin-bottom:9px;">
  <div style="width:38px;height:38px;border-radius:12px;background:#f2c94c;color:#111;display:grid;place-items:center;font-weight:950;">{idx}</div>
  <div><div style="font-size:15px;font-weight:900;color:#fff;">{home} vs {away}</div><div style="font-size:10px;color:#8f97a3;margin-top:4px;">AI評価: {pick}</div></div>
  <div style="text-align:right;"><div style="font-size:20px;font-weight:950;color:#fff;">{probability_text}</div><div style="font-size:8px;color:#8f97a3;margin-top:2px;">WIN RATE</div></div>
</div>
''',
                unsafe_allow_html=True,
            )

with recent_col:
    render_section("SENSITIVITY", "最近の感度分析")
    if not analysis_records:
        st.info("分析シナリオはまだありません。")
    else:
        recent = sorted(
            analysis_records,
            key=lambda r: (str(r.get("date", "")), str(r.get("time", "")), str(r.get("created_at", ""))),
            reverse=True,
        )[:5]
        for record in recent:
            status = "確定" if record.get("status") == "final" else "未確定"
            delta = f"{point_delta(record):+.0f}" if record.get("status") == "final" else "-"
            st.markdown(
                f'''
<div style="background:#12161c;border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:14px 15px;margin-bottom:9px;">
  <div style="display:flex;justify-content:space-between;gap:12px;align-items:center;">
    <div><div style="font-size:13px;font-weight:900;color:#fff;">{esc(record.get('team'))} vs {esc(record.get('opponent'))}</div><div style="font-size:9px;color:#8f97a3;margin-top:4px;">{esc(record.get('date'))} {esc(record.get('time'))} / 補正 {esc(record.get('handicap'), '0')}</div></div>
    <div style="text-align:right;"><div style="font-size:16px;font-weight:950;color:#f2c94c;">{delta}</div><div style="font-size:8px;color:#8f97a3;">{status}</div></div>
  </div>
</div>
''',
                unsafe_allow_html=True,
            )

st.markdown(
    f'''
<div style="margin-top:28px;padding:14px 2px;border-top:1px solid rgba(255,255,255,.08);display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;color:#737b86;font-size:9px;">
  <span>AI BASEBALL STUDIO / PRIVATE RESEARCH</span>
  <span>Last view update: {now.strftime('%Y-%m-%d %H:%M:%S')} JST / Score delta: {total_delta:+.0f}</span>
</div>
''',
    unsafe_allow_html=True,
)
