from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

from handicap_source import fetch_hawks_handicap

JST = ZoneInfo("Asia/Tokyo")
_today_jst = datetime.now(JST).date()

st.set_page_config(page_title="AI詳細 | MY AI BASEBALL", page_icon="⚾", layout="wide")

_live_handicap = fetch_hawks_handicap(_today_jst)
_live_handicap_score = (
    float(_live_handicap["handicap_score"])
    if _live_handicap.get("published") and _live_handicap.get("handicap_score") is not None
    else 0.0
)

_app_path = Path(__file__).resolve().parents[1] / "app.py"
_app_source = _app_path.read_text(encoding="utf-8")
_fixed_assignment = "handicap_score = -2.0"
if _fixed_assignment not in _app_source:
    st.error("ハンデ固定値の置換対象が見つかりません。app.pyの構成を確認してください。")
    st.stop()
_app_source = _app_source.replace(
    _fixed_assignment,
    "handicap_score = _live_handicap_score",
    1,
)

_original_set_page_config = st.set_page_config
st.set_page_config = lambda *args, **kwargs: None
try:
    exec(compile(_app_source, str(_app_path), "exec"), globals(), globals())
finally:
    st.set_page_config = _original_set_page_config
