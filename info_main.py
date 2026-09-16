from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import html

import streamlit as st

from auth_session import render_account_controls, require_auth0
from daily_data import load_current_daily_json

JST = ZoneInfo("Asia/Tokyo")
REPO_DATA_DIR = Path(__file__).resolve().parent / "data"

st.set_page_config(
    page_title="AI BASEBALL STUDIO | GAME INFORMATION",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="collapsed",
)

auth_user = require_auth0()
render_account_controls(auth_user)


def safe(value, fallback="--"):
    if value in (None, ""):
        value = fallback
    return html.escape(str(value))


def fmt_time(value):
    if not value:
        return "同期待ち"
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=JST)
        return dt.astimezone(JST).strftime("%Y/%m/%d %H:%M JST")
    except Exception:
        return safe(value)


def first_value(game, *keys, fallback="--"):
    for key in keys:
        value = game.get(key)
        if value not in (None, ""):
            return value
    return fallback


npb_today = load_current_daily_json("npb_today.json", {"games": []})
predictions = load_current_daily_json("today_ai_predictions.json", {"games": []})
today_games = npb_today.get("games") or []
ai_games = predictions.get("games") or []
updated_at = fmt_time(npb_today.get("updated_at") or predictions.get("updated_at"))
now = datetime.now(JST)

st.markdown(
    """
<style>
:root{--bg:#f4f1ea;--paper:#fffdf9;--ink:#111827;--muted:#6b7280;--line:#ddd6c9;--gold:#f3c400;--dark:#121212}
[data-testid="stHeader"],[data-testid="stToolbar"],footer,[data-testid="stSidebar"]{display:none!important}
[data-testid="stAppViewContainer"]{background:var(--bg)!important;color:var(--ink)!important}
.block-container{max-width:1460px!important;padding:0 28px 42px!important}
.topbar{margin:0 -28px;background:var(--dark);color:#fff;display:flex;align-items:center;justify-content:space-between;padding:18px 28px;border-bottom:2px solid rgba(243,196,0,.55)}
.brand{font-weight:950;letter-spacing:.12em}.brand span{color:var(--gold)}.sync{font-size:12px;color:#d1d5db}
.hero{margin-top:18px;border-radius:20px;padding:30px 34px;color:#fff;background:linear-gradient(135deg,#101010,#3c2c0a)}
.hero h1{margin:0!important;color:#fff!important;font-size:42px!important}.hero h1 em{color:var(--gold);font-style:normal}.hero p{color:#d1d5db;max-width:760px}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-top:14px}
.panel{background:var(--paper);border:1px solid var(--line);border-radius:18px;padding:18px}.panel h2{margin:0 0 14px!important;font-size:21px!important}
.game{display:grid;grid-template-columns:1fr auto 1fr;gap:14px;align-items:center;border-top:1px solid var(--line);padding:14px 0}.game:first-of-type{border-top:0}.team{font-size:18px;font-weight:900}.team.away{text-align:right}.score{font-size:22px;font-weight:950;min-width:96px;text-align:center}.meta{font-size:11px;color:var(--muted);margin-top:4px}.starter{font-size:12px;color:#374151;margin-top:4px}.empty{padding:18px;border:1px dashed var(--line);border-radius:12px;color:var(--muted)}
.ai-card{border-top:1px solid var(--line);padding:13px 0}.ai-card:first-of-type{border-top:0}.ai-title{font-weight:900}.ai-meta{font-size:12px;color:var(--muted);margin-top:4px}.badge{display:inline-block;background:#171717;color:var(--gold);border-radius:999px;padding:4px 8px;font-size:10px;font-weight:900;margin-right:6px}
.note{margin-top:14px;font-size:11px;color:var(--muted)}
@media(max-width:760px){.block-container{padding:0 14px 30px!important}.topbar{margin:0 -14px;padding:14px}.grid{grid-template-columns:1fr}.hero{padding:22px}.hero h1{font-size:31px!important}.game{grid-template-columns:1fr}.team.away{text-align:left}.score{text-align:left}}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    f"""
<div class="topbar">
  <div class="brand">AI <span>BASEBALL</span> STUDIO</div>
  <div class="sync">{safe(now.strftime('%Y/%m/%d %H:%M JST'))}</div>
</div>
<div class="hero">
  <h1>GAME <em>INFORMATION</em></h1>
  <p>試合情報・スコア・球場・開始時刻・予告先発など、野球情報に限定したダッシュボードです。</p>
</div>
""",
    unsafe_allow_html=True,
)

left, right = st.columns([1.35, 0.85])

with left:
    st.markdown('<div class="panel"><h2>本日の試合</h2>', unsafe_allow_html=True)
    if not today_games:
        st.markdown('<div class="empty">本日の試合データを同期中です。</div>', unsafe_allow_html=True)
    else:
        for game in today_games:
            away = first_value(game, "away", "away_team", "visitor")
            home = first_value(game, "home", "home_team")
            away_score = first_value(game, "away_score", "visitor_score", fallback="-")
            home_score = first_value(game, "home_score", fallback="-")
            status = first_value(game, "status", "game_status", fallback="試合前")
            start = first_value(game, "start_time", "time", fallback="--")
            venue = first_value(game, "stadium", "venue", fallback="--")
            away_starter = first_value(game, "away_starter", "visitor_starter", fallback="--")
            home_starter = first_value(game, "home_starter", fallback="--")
            st.markdown(
                f"""
<div class="game">
  <div class="team away">{safe(away)}<div class="starter">先発 {safe(away_starter)}</div></div>
  <div class="score">{safe(away_score)} - {safe(home_score)}<div class="meta">{safe(status)} / {safe(start)} / {safe(venue)}</div></div>
  <div class="team">{safe(home)}<div class="starter">先発 {safe(home_starter)}</div></div>
</div>
""",
                unsafe_allow_html=True,
            )
    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="panel"><h2>AI分析ステータス</h2>', unsafe_allow_html=True)
    if not ai_games:
        st.markdown('<div class="empty">AI分析データを同期中です。</div>', unsafe_allow_html=True)
    else:
        for game in ai_games[:6]:
            away = first_value(game, "away", "away_team", fallback="--")
            home = first_value(game, "home", "home_team", fallback="--")
            confidence = first_value(game, "confidence", fallback="--")
            predicted_score = first_value(game, "predicted_score", fallback="--")
            sample = first_value(game, "validation_sample_size", fallback="--")
            st.markdown(
                f"""
<div class="ai-card">
  <div class="ai-title">{safe(away)} @ {safe(home)}</div>
  <div class="ai-meta"><span class="badge">AI</span>予測スコア {safe(predicted_score)} / 信頼度 {safe(confidence)} / 検証試合数 {safe(sample)}</div>
</div>
""",
                unsafe_allow_html=True,
            )
    st.markdown(f'<div class="note">最終データ更新: {safe(updated_at)}</div></div>', unsafe_allow_html=True)

st.caption("情報表示専用モード：BET・収支・ハンデ判定機能は使用しません。")
