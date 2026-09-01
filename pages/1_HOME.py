import streamlit as st
from studio_pages import setup, load_json, rows, first, percent, money, updated_at

setup("HOME", "本日の試合・AI予測・運用成績をひと目で確認")

predictions = rows(load_json("today_ai_predictions.json", []))
history = rows(load_json("game_history.json", []))
summary = load_json("bet_summary.json", {})

c1, c2, c3, c4 = st.columns(4)
c1.metric("本日の対象試合", len(predictions))
c2.metric("予測保存数", len(history))
c3.metric("今週の未精算収支", money(summary.get("weekly_unsettled_profit", 0)))
c4.metric("データ更新", updated_at())

st.subheader("本日のAI注目カード")
if predictions:
    ranked = sorted(predictions, key=lambda x: float(first(x, "confidence", "win_probability", "probability", default=0) or 0), reverse=True)
    for item in ranked[:6]:
        left, mid, right = st.columns([3, 1, 1])
        left.markdown(f"**{first(item,'away_team','team')} vs {first(item,'home_team','opponent')}**")
        mid.metric("AI勝率", percent(first(item, "win_probability", "probability", "confidence", default=0)))
        right.write(first(item, "prediction", "pick", "recommended_team", default="分析中"))
else:
    st.info("本日のAI予測データを待機しています。")

st.page_link("app.py", label="既存の試合分析画面を開く", icon="⚾")
