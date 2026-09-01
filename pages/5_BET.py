import streamlit as st
from studio_pages import setup, load_json, rows, first, money

setup("BET", "ベット記録・精算状況・週間収支")

summary = load_json("bet_summary.json", {})
records = rows(load_json("bet_records.json", []))
c1, c2, c3 = st.columns(3)
c1.metric("期間", f"{summary.get('week_start','-')} 〜 {summary.get('week_end','-')}")
c2.metric("今週の未精算収支", money(summary.get("weekly_unsettled_profit", 0)))
c3.metric("記録数", len(records))

if not records:
    st.info("ベット記録はまだありません。")
else:
    for item in reversed(records):
        with st.container(border=True):
            a, b, c = st.columns([3, 1, 1])
            a.markdown(f"**{first(item,'team')} vs {first(item,'opponent')}**")
            a.caption(f"{first(item,'date')} {first(item,'time',default='')} / ハンデ {first(item,'handicap',default=0)}")
            b.metric("判定", first(item, "result", default="PENDING"))
            c.metric("収支", money(first(item, "profit", default=0)))
            st.caption("精算済み" if item.get("settled") else "未精算")
