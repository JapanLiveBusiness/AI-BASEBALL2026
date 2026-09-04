from __future__ import annotations

import html
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

from game_calendar import attach_handicaps, fetch_daily_handicaps, fetch_npb_schedule_day, merge_game_sources
from studio_theme import apply_studio_theme, render_hero, render_nav_links, render_section, render_topbar

JST = ZoneInfo("Asia/Tokyo")
REPO_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PROD_DATA_DIR = Path("/app/data")
LIVE_STATUSES = {"live", "in_progress", "playing", "試合中", "開催中"}
FINAL_STATUSES = {"final", "finished", "completed", "終了", "試合終了"}

st.set_page_config(page_title="試合カレンダー | AI BASEBALL STUDIO", page_icon="⚾", layout="wide", initial_sidebar_state="collapsed")


def data_path(name: str) -> Path:
    prod = PROD_DATA_DIR / name
    return prod if prod.exists() else REPO_DATA_DIR / name


def load_json(name: str, fallback):
    try:
        return json.loads(data_path(name).read_text(encoding="utf-8"))
    except Exception:
        return fallback


def load_schedule_cache() -> dict:
    runtime_cache = PROD_DATA_DIR / "npb_schedule_cache.json"
    bundled_fallback = REPO_DATA_DIR.parent / "npb_schedule_fallback.json"
    for path in (runtime_cache, bundled_fallback):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
    return {"games": []}


@st.cache_data(ttl=600, show_spinner=False)
def cached_official_games(date_iso: str) -> list[dict]:
    return fetch_npb_schedule_day(date.fromisoformat(date_iso))


@st.cache_data(ttl=3600, show_spinner=False)
def cached_handicaps(date_iso: str) -> list[dict]:
    return fetch_daily_handicaps(date.fromisoformat(date_iso))


def status_key(game: dict) -> str:
    return str(game.get("status") or "scheduled").strip().lower()


def is_live(game: dict) -> bool:
    key = status_key(game)
    return key in LIVE_STATUSES or any(token in key for token in ("live", "progress", "試合中"))


def is_final(game: dict) -> bool:
    key = status_key(game)
    return key in FINAL_STATUSES or any(token in key for token in ("final", "finish", "終了"))


def status_label(game: dict) -> tuple[str, str]:
    key = status_key(game)
    if is_live(game):
        return "LIVE", "live"
    if is_final(game):
        return "試合終了", "final"
    if "cancel" in key or "中止" in key:
        return "中止", "cancelled"
    if key == "result_pending":
        return "結果確認中", "scheduled"
    return "開始前", "scheduled"


def score_text(value) -> str:
    return "-" if value is None or value == "" else html.escape(str(value))


def prediction_index(payload: dict) -> dict[tuple[str, str], dict]:
    out = {}
    for row in payload.get("games") or []:
        home = str(row.get("home") or "")
        away = str(row.get("away") or "")
        if home and away:
            out[(home, away)] = row
    return out


def games_for_date(selected_date: date) -> tuple[list[dict], dict, dict]:
    selected_iso = selected_date.isoformat()
    today_payload = load_json("npb_today.json", {"games": []})
    predictions = load_json("today_ai_predictions.json", {"games": []})
    history = load_json("historical_games_2017_2026.json", [])
    local_games = [
        game for game in today_payload.get("games") or []
        if str(game.get("date") or today_payload.get("date") or "") == selected_iso
    ]
    history_games = []
    for row in history if isinstance(history, list) else []:
        if str(row.get("date") or "") != selected_iso:
            continue
        game = dict(row)
        game["status"] = "final"
        game["result_source"] = game.get("result_source") or "保存済み試合結果"
        history_games.append(game)

    is_past = selected_date < datetime.now(JST).date()
    daily_results = cached_handicaps(selected_iso) if is_past else []
    official_games = [] if daily_results else cached_official_games(selected_iso)
    if not official_games:
        schedule_cache = load_schedule_cache()
        official_games = [
            game for game in schedule_cache.get("games") or []
            if str(game.get("date") or "") == selected_iso
        ]
    games = merge_game_sources(official_games, history_games, local_games, daily_results)
    if selected_date < datetime.now(JST).date():
        games = attach_handicaps(games, daily_results)

    predictions_date = str(predictions.get("date") or "")
    if predictions_date and predictions_date != selected_iso:
        predictions = {"games": []}
    return games, today_payload, predictions


def clean_venue(value) -> str:
    venue = re.sub(r"^\d{1,2}:\d{2}", "", str(value or "")).strip()
    return venue or "会場未定"


def handicap_html(game: dict, show_handicap: bool) -> str:
    if not show_handicap:
        return ""
    entries = []
    for side in ("home", "away"):
        token = game.get(f"{side}_handicap")
        if token is not None:
            team = html.escape(str(game.get(side) or ("ホーム" if side == "home" else "ビジター")))
            entries.append(f"{team} {html.escape(str(token))}")
    value = " / ".join(entries) if entries else "未掲載・未取得"
    return f'<div class="handicap"><span>HANDICAP</span><strong>{value}</strong></div>'


def set_selected_date(value: date) -> None:
    st.session_state.games_calendar_date = value


def shift_selected_date(days: int) -> None:
    current = st.session_state.get("games_calendar_date", datetime.now(JST).date())
    st.session_state.games_calendar_date = current + timedelta(days=days)


apply_studio_theme()
render_topbar("GAMES / CALENDAR")
render_hero(
    "試合カレンダー",
    "前日までの試合結果とハンデ、当日の進行状況、翌日以降の開始時刻・開催球場を日付ごとに確認できます。",
    kicker="AI BASEBALL STUDIO / MATCH CENTER",
    accent="試合",
)
render_nav_links()

today = datetime.now(JST).date()
if "games_calendar_date" not in st.session_state:
    st.session_state.games_calendar_date = today

nav_left, nav_today, nav_date, nav_right = st.columns([1, 1, 3, 1])
nav_left.button("前日", icon=":material/chevron_left:", key="games_previous_date", on_click=shift_selected_date, args=(-1,), width="stretch")
nav_today.button("今日", icon=":material/today:", key="games_today_date", on_click=set_selected_date, args=(today,), width="stretch")
selected_date = nav_date.date_input("表示日", key="games_calendar_date", format="YYYY/MM/DD", label_visibility="collapsed", width="stretch")
nav_right.button("翌日", icon=":material/chevron_right:", key="games_next_date", on_click=shift_selected_date, args=(1,), width="stretch")

st.markdown(
    """
<style>
.game-summary{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:14px 0 18px}
.game-kpi{background:#fffdf8;border:1px solid #ddd5c8;border-radius:13px;padding:14px}
.game-kpi span{display:block;font-size:8px;letter-spacing:.18em;color:#a77e11;font-weight:900}
.game-kpi strong{display:block;margin-top:7px;font-size:20px}
.game-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.game-card{background:#fffdf8;border:1px solid #ddd5c8;border-radius:15px;padding:17px;box-shadow:0 8px 24px rgba(35,29,18,.04)}
.game-card.live{border-color:#d5aa14;box-shadow:0 0 0 2px rgba(241,196,15,.10)}
.game-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:14px}
.game-time{font-size:10px;color:#746f66}
.game-status{font-size:9px;font-weight:950;border-radius:999px;padding:5px 9px;background:#efebe3;color:#5d574e}
.game-status.live{background:#171717;color:#f1c40f}.game-status.final{background:#ebe7df;color:#333}
.game-status.cancelled{background:#f6dfdf;color:#8b2525}
.matchup{display:grid;grid-template-columns:1fr 56px 1fr;gap:8px;align-items:center}
.team-side{min-width:0}.team-side.right{text-align:right}
.team-name{font-size:18px;font-weight:900;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.team-score{font-size:31px;font-weight:950;line-height:1;margin-top:6px}
.vs{text-align:center;color:#9b9387;font-size:10px;font-weight:900}
.game-meta{border-top:1px solid #e4ddd2;margin-top:14px;padding-top:12px;display:flex;justify-content:space-between;gap:12px;font-size:9px;color:#746f66}
.prediction,.handicap{margin-top:11px;padding:10px 12px;border-radius:10px;display:flex;justify-content:space-between;align-items:center;gap:12px}
.prediction{background:#191919;color:#fff}.prediction span{font-size:9px;color:#bbb}
.prediction strong{font-size:14px;color:#f1c40f}
.handicap{background:#fff4c7;border:1px solid #ead276;color:#342b13}
.handicap span{font-size:8px;letter-spacing:.14em;color:#8b7018;font-weight:900}.handicap strong{font-size:12px}
.empty-games{padding:28px;background:#fffdf8;border:1px dashed #d8d0c3;border-radius:14px;color:#746f66;text-align:center;font-size:12px}
.sync-note{margin:10px 0 16px;padding:10px 12px;border-radius:10px;background:#fff7d4;border:1px solid #e6cd69;font-size:10px;color:#65551b}
@media(max-width:850px){.game-summary{grid-template-columns:repeat(2,1fr)}.game-grid{grid-template-columns:1fr}}
@media(max-width:520px){.game-summary{grid-template-columns:1fr 1fr}.team-name{font-size:15px}.team-score{font-size:27px}}
@media(max-width:520px){.matchup{grid-template-columns:1fr 42px 1fr}.game-meta{flex-direction:column;gap:4px}}
</style>
""",
    unsafe_allow_html=True,
)

refresh_every = "30s" if selected_date == today else None


@st.fragment(run_every=refresh_every)
def render_match_center(target_date: date) -> None:
    games, today_payload, predictions = games_for_date(target_date)
    pred_by_game = prediction_index(predictions)
    live_games = [game for game in games if is_live(game)]
    date_relation = "過去の結果" if target_date < today else "本日の試合" if target_date == today else "今後の予定"
    if any(str(game.get("result_source") or "") == "ハンデの森" for game in games):
        source_label = "結果・ハンデ取得"
    elif any(str(game.get("date") or "") == str(today_payload.get("date") or "") for game in games):
        source_label = "本番共有データ"
    else:
        source_label = "NPB公式・保存データ"
    st.markdown(
        f"""<div class="game-summary">
  <div class="game-kpi"><span>SELECTED DATE</span><strong>{target_date.strftime('%Y/%m/%d')}</strong></div>
  <div class="game-kpi"><span>VIEW</span><strong>{date_relation}</strong></div>
  <div class="game-kpi"><span>GAMES / LIVE</span><strong>{len(games)} / {len(live_games)}</strong></div>
  <div class="game-kpi"><span>DATA SOURCE</span><strong style="font-size:13px">{source_label}</strong></div>
</div>""",
        unsafe_allow_html=True,
    )
    if live_games:
        st.markdown('<div class="sync-note">● 試合中のため、この試合一覧を30秒ごとに自動更新します。</div>', unsafe_allow_html=True)

    render_section("MATCH CENTER", f"{target_date.strftime('%Y年%m月%d日')}の試合")
    if not games:
        message = "この日の試合結果はまだ取得できていません。" if target_date < today else "この日の試合予定はありません。休養日、または公式日程の更新待ちです。"
        st.markdown(f'<div class="empty-games">{message}</div>', unsafe_allow_html=True)
        return

    cards = []
    for game in games:
        home_name, away_name = str(game.get("home") or "---"), str(game.get("away") or "---")
        home, away = html.escape(home_name), html.escape(away_name)
        venue = html.escape(clean_venue(game.get("venue")))
        game_date = html.escape(str(game.get("date") or target_date.isoformat()))
        label, css_class = status_label(game)
        pred = pred_by_game.get((home_name, away_name), {})
        pick = html.escape(str(pred.get("pick") or ""))
        probability = pred.get("win_probability")
        prediction_html = ""
        if pick:
            probability_label = f"{float(probability):.1f}%" if isinstance(probability, (int, float)) else "--"
            prediction_html = f'<div class="prediction"><span>AI PICK</span><strong>{pick} · {probability_label}</strong></div>'
        result_source = html.escape(str(game.get("result_source") or "NPB公式"))
        cards.append(
            f'''<article class="game-card {"live" if css_class == "live" else ""}">
  <div class="game-head">
    <div class="game-time">{game_date} · {html.escape(str(game.get("time") or "--:--"))} · {venue}</div>
    <div class="game-status {css_class}">{html.escape(label)}</div>
  </div>
  <div class="matchup">
    <div class="team-side"><div class="team-name">{away}</div><div class="team-score">{score_text(game.get("away_score"))}</div></div>
    <div class="vs">VS</div>
    <div class="team-side right"><div class="team-name">{home}</div><div class="team-score">{score_text(game.get("home_score"))}</div></div>
  </div>
  {handicap_html(game, target_date < today)}
  <div class="game-meta"><span>STATUS: {html.escape(str(game.get("status") or "scheduled"))}</span><span>SOURCE: {result_source}</span></div>
  {prediction_html}
</article>'''
        )
    st.markdown(f'<div class="game-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


render_match_center(selected_date)
st.caption("前日・翌日ボタンまたは日付欄で移動できます。過去日は試合結果と公開ハンデ、未来日は公式の開始時刻・球場を表示します。")
