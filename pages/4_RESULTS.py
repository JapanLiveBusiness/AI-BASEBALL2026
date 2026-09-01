import streamlit as st
from studio_pages import setup, load_json, rows, first, game_label

setup("RESULTS", "実際の試合結果とAI予想結果を照合")

items = rows(load_json("game_history.json", []))
if not items:
    st.info("確定した試合結果はまだありません。")
else:
    wins = sum(1 for x in items if str(first(x, "prediction_result", "result", "hit", default="")).lower() in ("win","hit","true","1","的中"))
    c1, c2 = st.columns(2)
    c1.metric("検証試合数", len(items))
    c2.metric("的中数", wins)
    for item in reversed(items[-100:]):
        with st.container(border=True):
            a, b, c = st.columns([3, 1.2, 1.2])
            a.markdown(f"**{game_label(item)}**")
            a.caption(str(first(item, "date", "game_date", default="-")))
            b.metric("スコア", first(item, "score", "final_score", default="-"))
            c.metric("判定", first(item, "prediction_result", "result", "hit", default="未判定"))
