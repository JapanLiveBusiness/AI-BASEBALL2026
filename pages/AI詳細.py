from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

from handicap_source import fetch_hawks_handicap
from studio_theme import apply_studio_theme, render_topbar, render_hero, render_nav_links

JST = ZoneInfo("Asia/Tokyo")
_today_jst = datetime.now(JST).date()

st.set_page_config(page_title="AI詳細 | MY AI BASEBALL", page_icon="⚾", layout="wide")
apply_studio_theme()
render_topbar("AI DETAIL")
render_hero(
    "AI詳細ダッシュボード",
    "既存の高度な試合分析・ハンデ情報・予測ロジックを維持したまま、AI Baseball Studioのデザインシェルへ統合しています。",
    kicker="AI BASEBALL STUDIO / DEEP ANALYTICS",
    accent="AI詳細",
)
render_nav_links()

@st.cache_data(ttl=600, max_entries=4, show_spinner=False)
def load_live_handicap(date_value):
    return fetch_hawks_handicap(date_value, timeout=4)


_live_handicap = load_live_handicap(_today_jst)
_live_handicap_score = (
    float(_live_handicap["handicap_score"])
    if _live_handicap.get("published") and _live_handicap.get("handicap_score") is not None
    else 0.0
)
if _live_handicap.get("published"):
    st.caption(
        f"公開ハンデ: {_live_handicap.get('favored_team')} {_live_handicap.get('token')}｜10分間キャッシュ"
    )
else:
    st.info("本日の公開ハンデは未掲載または取得できません。ハンデ補正なしで詳細分析を表示します。")

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
_original_file = globals().get("__file__")
st.set_page_config = lambda *args, **kwargs: None
globals()["__file__"] = str(_app_path)
try:
    try:
        exec(compile(_app_source, str(_app_path), "exec"), globals(), globals())
    except Exception as exc:
        st.error("詳細分析の一部を読み込めませんでした。基本画面と他の機能は引き続き利用できます。")
        with st.expander("エラー情報"):
            st.code(f"{type(exc).__name__}: {exc}")
finally:
    st.set_page_config = _original_set_page_config
    globals()["__file__"] = _original_file
