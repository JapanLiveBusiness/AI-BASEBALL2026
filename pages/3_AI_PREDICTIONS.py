import streamlit as st
from studio_pages import setup, load_json, rows, first, percent, game_label

setup("AI PREDICTIONS", "NPB全試合の勝率予測を高い順に表示")

items = rows(load_json("today_ai_predictions.json", []))
if not items:
    st.info("本日の予測データを待機しています。")
else:
    def score(x):
        try:
            return float(first(x, "win_probability", "probability", "confidence", default=0) or 0)
        except Exception:
            return 0
    for rank, item in enumerate(sorted(items, key=score, reverse=True), 1):
        with st.container(border=True):
            a, b, c = st.columns([.5, 3, 1.2])
            a.markdown(f"## {rank}")
            b.markdown(f"### {game_label(item)}")
            b.write(f"AI予想: **{first(item, 'prediction', 'pick', 'recommended_team', default='分析中')}**")
            reason = first(item, "reason", "analysis", "comment", default="")
            if reason:
                b.caption(str(reason))
            c.metric("勝率", percent(first(item, "win_probability", "probability", "confidence", default=0)))
