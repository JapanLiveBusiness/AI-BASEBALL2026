from pathlib import Path
import json
import streamlit as st

st.set_page_config(page_title="本日のAI予想", page_icon="⚾", layout="wide")

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "today_ai_predictions.json"

st.title("⚾ 本日のAI予想")
st.caption("HAWKS AI Daily Prediction / 勝率が高い順")

if not DATA_FILE.exists():
    st.warning("本日の予想データがまだ登録されていません。")
    st.stop()

with DATA_FILE.open("r", encoding="utf-8") as f:
    payload = json.load(f)

games = sorted(payload.get("games", []), key=lambda x: x.get("rank", 999))

st.subheader(f"{payload.get('date', '')} NPB 全試合予想")

for game in games:
    rank = game.get("rank")
    home = game.get("home")
    away = game.get("away")
    pick = game.get("pick")
    prob = game.get("win_probability")
    score = game.get("predicted_score")
    confidence = game.get("confidence")

    if rank == 1:
        medal = "🥇"
    elif rank == 2:
        medal = "🥈"
    elif rank == 3:
        medal = "🥉"
    else:
        medal = f"{rank}位"

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([1.0, 2.5, 2.0, 1.5])
        with c1:
            st.markdown(f"### {medal}")
        with c2:
            st.markdown(f"**{home} vs {away}**")
            st.caption(f"予想スコア {score}")
        with c3:
            st.metric("勝利予想", pick, f"{prob}%")
        with c4:
            st.metric("信頼度", confidence)
        st.progress(max(0, min(100, int(prob))) / 100)

if games:
    best = games[0]
    st.success(
        f"本日の最上位予想：{best.get('pick')}　"
        f"推定勝率 {best.get('win_probability')}%　"
        f"予想スコア {best.get('predicted_score')}"
    )

st.caption("※勝率・予想スコアはAI予測値であり、試合結果を保証するものではありません。")
