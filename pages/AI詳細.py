import streamlit as st

from studio_theme import apply_studio_theme, render_hero, render_topbar

st.set_page_config(page_title="AI詳細 | AI BASEBALL STUDIO", page_icon="⚾", layout="wide")
apply_studio_theme()
render_topbar("AI DETAIL")
render_hero(
    "AI詳細",
    "詳細なモデル検証・年度別精度・確率品質は統計レポートへ統合しました。旧アプリを動的実行する方式は廃止しています。",
    kicker="AI BASEBALL STUDIO / DEEP ANALYTICS",
)

st.page_link("pages/レポート.py", label="統計・モデル検証レポートを開く", icon="📈", use_container_width=True)
st.page_link("pages/本日のAI予想.py", label="本日のAI予測を開く", icon="⚾", use_container_width=True)
st.page_link("pages/予想結果.py", label="予想結果・検証履歴を開く", icon="✅", use_container_width=True)
