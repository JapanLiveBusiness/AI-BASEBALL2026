from pathlib import Path

import streamlit as st

_STYLE = Path(__file__).with_name("global_styles.html")

def render_global_styles() -> None:
    st.markdown(_STYLE.read_text(encoding="utf-8"), unsafe_allow_html=True)
