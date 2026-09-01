from pathlib import Path
import json
import streamlit as st

from studio_theme import apply_studio_theme, render_topbar, render_hero, render_section, render_nav_links

st.set_page_config(page_title="AI予測 | MY AI BASEBALL", page_icon="⚾", layout="wide")
apply_studio_theme()
render_topbar("AI PREDICTION")
render_hero(
    "本日のAI予測",
    "勝率・予想スコア・信頼度を1画面で比較。AI Baseball Studioのメインデザインに統一しています。",
    kicker="TODAY / NPB / AI PREDICTION",
    accent="AI予測",
)
render_nav_links()

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "today_ai_predictions.json"

if not DATA_FILE.exists():
    st.warning("本日の予想データがまだ登録されていません。")
    st.stop()

with DATA_FILE.open("r", encoding="utf-8") as f:
    payload = json.load(f)

games = sorted(payload.get("games", []), key=lambda x: x.get("rank", 999))
render_section("DAILY BOARD", f"{payload.get('date', '')} NPB 全試合予想")

if not games:
    st.info("AI予測データを同期中です。")
    st.stop()

for game in games:
    rank = game.get("rank")
    home = game.get("home", "-")
    away = game.get("away", "-")
    pick = game.get("pick", "-")
    prob = game.get("win_probability", 0)
    score = game.get("predicted_score", "-")
    confidence = game.get("confidence", "-")

    c1, c2, c3, c4 = st.columns([0.7, 2.4, 1.8, 1.4])
    with c1:
        st.markdown(f'<div class="studio-rank">{rank}</div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f"### {home} vs {away}")
        st.caption(f"予想スコア {score}")
    with c3:
        st.metric("勝利予想", pick, f"{prob}%")
    with c4:
        st.metric("信頼度", confidence)
    st.progress(max(0, min(100, int(prob))) / 100)
    st.divider()

best = games[0]
render_section("TOP RECOMMENDATION", "本日の最上位予想")
left, mid, right = st.columns([1.6, 1, 1])
left.markdown(f"## {best.get('pick', '-')}")
left.caption(f"{best.get('home', '-')} vs {best.get('away', '-')} / 予想スコア {best.get('predicted_score', '-')}")
mid.metric("推定勝率", f"{best.get('win_probability', '-')}%")
right.metric("信頼度", best.get("confidence", "-"))

st.caption("※勝率・予想スコアはAI予測値であり、試合結果を保証するものではありません。")