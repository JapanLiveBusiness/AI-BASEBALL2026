import streamlit as st

from auth import current_username, logout
from research_state import current_slate, data_health_rows, freshness, load_json
from studio_theme import apply_studio_theme, render_hero, render_section, render_topbar

st.set_page_config(
    page_title="設定 | AI BASEBALL STUDIO",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

apply_studio_theme()
render_topbar("SETTINGS / STATUS")
render_hero(
    "設定・システム状態",
    "ログイン情報、データ同期状態、現在の試合表示基準を確認できます。",
    kicker="AI BASEBALL STUDIO / SETTINGS",
)

slate = current_slate()
schedule = slate["schedule"]
predictions = load_json("today_ai_predictions.json", {"games": []})
schedule_state = freshness(schedule)
prediction_state = freshness(predictions)

render_section("ACCOUNT", "ログイン")
c1, c2 = st.columns([2, 1])
c1.metric("ログインユーザー", current_username())
c2.metric("認証", "Clerk / Access")
if st.button("ログアウト", use_container_width=True):
    logout()

render_section("DISPLAY", "試合表示ルール")
d1, d2, d3 = st.columns(3)
d1.metric("現在の表示日", slate.get("display_date") or "--")
d2.metric("表示試合数", len(slate.get("games") or []))
switch_at = slate.get("switch_at")
d3.metric("次回切替", switch_at.strftime("%m/%d %H:%M") if switch_at else "次カード待ち")
st.caption("次の試合日の最初の試合開始2時間前に、直前カードから次のカードへ切り替わります。")

render_section("SYNC", "データ鮮度")
s1, s2 = st.columns(2)
s1.metric("試合データ", f"{schedule_state['label']} / {schedule_state['date']}")
s2.metric("AI予測", f"{prediction_state['label']} / {prediction_state['date']}")
if schedule_state["level"] == "stale":
    st.warning("試合データの日付が現在日付と一致していません。同期ジョブまたはデータ生成処理の確認が必要です。")
if prediction_state["level"] == "stale":
    st.warning("AI予測データの日付が現在日付と一致していません。古い予測を『本日の予測』として扱わないよう各画面で日付照合します。")

render_section("DATA HEALTH", "データファイル状態")
st.dataframe(data_health_rows(), hide_index=True, use_container_width=True)

render_section("QUICK LINKS", "管理メニュー")
q1, q2, q3 = st.columns(3)
q1.page_link("pages/レポート.py", label="統計・モデル検証", icon="📈", use_container_width=True)
q2.page_link("pages/予想結果.py", label="予想結果・検証履歴", icon="✅", use_container_width=True)
q3.page_link("pages/試合.py", label="試合センター", icon="⚾", use_container_width=True)

st.caption("AI BASEBALL STUDIO / research environment status")
