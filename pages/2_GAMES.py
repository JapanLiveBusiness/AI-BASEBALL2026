import streamlit as st
from studio_pages import setup, load_json, rows, first, game_label

setup("GAMES", "本日および保存済みの試合カード一覧")

games = rows(load_json("today_ai_predictions.json", []))
if not games:
    games = rows(load_json("game_history.json", []))

if not games:
    st.info("表示できる試合データがまだありません。")
else:
    for game in games:
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1.4, 1.4])
            c1.markdown(f"### {game_label(game)}")
            c1.caption(str(first(game, "date", "game_date", default="日付未取得")))
            c2.metric("開始", first(game, "time", "start_time", default="-"))
            c3.metric("会場", first(game, "venue", "stadium", default="-"))
            status = first(game, "status", "game_status", default="試合前")
            st.caption(f"STATUS: {status}")
