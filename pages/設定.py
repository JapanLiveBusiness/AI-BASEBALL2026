import streamlit as st

from studio_theme import apply_studio_theme, render_hero, render_topbar

st.set_page_config(
    page_title="設定 | AI BASEBALL STUDIO",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

apply_studio_theme()
render_topbar("SETTINGS")
render_hero(
    "設定",
    "AI BASEBALL STUDIO の表示・研究環境に関する基本情報を確認できます。",
    kicker="AI BASEBALL STUDIO / SETTINGS",
)

st.markdown("### 研究環境")
st.write("このページは研究用サイトの設定・状態確認用です。")
st.info("現在、ユーザーごとの保存設定は未実装です。必要な設定項目を追加できます。")

if st.button("トップページへ戻る", type="primary"):
    st.switch_page("main.py")
