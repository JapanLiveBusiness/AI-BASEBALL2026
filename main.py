from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
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
                value = json.loads(path.read_text(encoding="utf-8"))
                return value
        except Exception:
            continue
    return fallback


predictions = load_json("today_ai_predictions.json", {"games": []})
npb_today = load_json("npb_today.json", {"games": []})
sim_records = load_json("bet_records.json", [])

prediction_games = predictions.get("games") or []
today_games = npb_today.get("games") or []
if not isinstance(sim_records, list):
    sim_records = []

settled = [r for r in sim_records if r.get("status") == "final"]
_, decided, hit_rate = calculate_hit_rate(settled)
total_delta = sum(point_delta(r) for r in settled)
now = datetime.now(JST)

render_topbar("PRIVATE RESEARCH")
render_hero(
    "AI BASEBALL RESEARCH STUDIO",
    "NPBの試合情報とAI予測を確認し、任意の仮想ハンデ条件で予測仮説を検証する個人用研究環境です。金銭取引や実際の賭けには接続しません。",
    kicker="NPB 2026 / PRIVATE ANALYTICS",
    accent="RESEARCH",
)

st.caption(f"最終表示更新: {now.strftime('%Y-%m-%d %H:%M:%S')} JST")

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("本日の試合", f"{len(today_games)}")
m2.metric("AI予測カード", f"{len(prediction_games)}")
m3.metric("確定シナリオ", f"{len(settled)}")
m4.metric("命中率", f"{hit_rate:.1f}%" if hit_rate is not None else "-")
m5.metric("累積仮想ポイント差", f"{total_delta:+.0f} pt")

render_section("WORKSPACE", "研究メニュー")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.page_link("pages/試合.py", label="⚾ 試合情報", use_container_width=True)
    st.caption("本日の対戦カード・試合状況を確認")
with c2:
    st.page_link("pages/本日のAI予想.py", label="🤖 AI予測", use_container_width=True)
    st.caption("勝率・予測スコア・モデル評価を確認")
with c3:
    st.page_link("pages/BET入力.py", label="🧪 シミュレーション入力", use_container_width=True)
    st.caption("任意の仮想ハンデ条件で仮説を登録")
with c4:
    st.page_link("pages/収支マップ.py", label="📊 シミュレーション結果", use_container_width=True)
    st.caption("命中率・条件別比較・仮想ポイント推移")

render_section("AI RANKING", "本日のAI評価")
if not prediction_games:
    st.info("本日のAI予測データはまだありません。")
else:
    ranked = sorted(prediction_games, key=lambda g: g.get("rank", 999))[:6]
    for idx, game in enumerate(ranked, start=1):
        home = game.get("home", "-")
        away = game.get("away", "-")
        pick = game.get("pick", "-")
        probability = game.get("win_probability")
        probability_text = f"{float(probability):.1f}%" if isinstance(probability, (int, float)) else "-"
        r1, r2, r3 = st.columns([1, 5, 2])
        r1.markdown(f"### {idx}")
        r2.markdown(f"**{home} vs {away}**  ")
        r2.caption(f"AI評価: {pick}")
        r3.metric("AI勝率", probability_text)

render_section("SIMULATION", "最近の仮説検証")
if not sim_records:
    st.info("シミュレーション記録はまだありません。")
else:
    recent = sorted(
        sim_records,
        key=lambda r: (str(r.get("date", "")), str(r.get("time", "")), str(r.get("created_at", ""))),
        reverse=True,
    )[:8]
    rows = []
    for record in recent:
        rows.append({
            "日付": record.get("date", "-"),
            "カード": f"{record.get('team', '-')} vs {record.get('opponent', '-')}",
            "仮想ハンデ": record.get("handicap", 0),
            "状態": "確定" if record.get("status") == "final" else "未確定",
            "ポイント差": f"{point_delta(record):+.0f} pt" if record.get("status") == "final" else "-",
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)

st.caption("AI BASEBALL STUDIO / 個人研究用・仮説検証環境")
