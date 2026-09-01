import streamlit as st
from studio_pages import setup, load_json, rows, first, money

setup("PERFORMANCE", "AI予測精度とベット成績の集計")

history = rows(load_json("game_history.json", []))
bets = rows(load_json("bet_records.json", []))

def is_hit(x):
    return str(first(x, "prediction_result", "result", "hit", default="")).lower() in ("win","hit","true","1","的中")

hits = sum(is_hit(x) for x in history)
accuracy = (hits / len(history) * 100) if history else 0
profit = sum(int(first(x, "profit", default=0) or 0) for x in bets)
settled = [x for x in bets if x.get("status") == "final" or x.get("result")]

c1, c2, c3, c4 = st.columns(4)
c1.metric("AI検証数", len(history))
c2.metric("AI的中率", f"{accuracy:.1f}%")
c3.metric("確定ベット", len(settled))
c4.metric("累計収支", money(profit))

if history:
    st.subheader("直近の予測判定")
    chart_rows = []
    running = 0
    for i, item in enumerate(history[-50:], 1):
        running += 1 if is_hit(item) else 0
        chart_rows.append({"試合": i, "累計的中率": running / i * 100})
    st.line_chart(chart_rows, x="試合", y="累計的中率")

if bets:
    st.subheader("収支推移")
    running = 0
    chart_rows = []
    for i, item in enumerate(bets, 1):
        running += int(first(item, "profit", default=0) or 0)
        chart_rows.append({"記録": i, "累計収支": running})
    st.bar_chart(chart_rows, x="記録", y="累計収支")
