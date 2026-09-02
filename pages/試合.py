from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st
import streamlit.components.v1 as components

from display_games import select_display_games
from studio_theme import apply_studio_theme, render_hero, render_nav_links, render_section, render_topbar
from team_branding import TEAM_BADGE_CSS, team_badge

JST = ZoneInfo("Asia/Tokyo")
REPO_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PROD_DATA_DIR = Path("/app/data")
LIVE_STATUSES = {"live", "in_progress", "playing", "試合中", "開催中"}
FINAL_STATUSES = {"final", "finished", "completed", "終了", "試合終了"}

st.set_page_config(
    page_title="試合 | AI BASEBALL STUDIO",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def data_path(name: str) -> Path:
    prod = PROD_DATA_DIR / name
    if prod.exists() and prod.stat().st_size:
        return prod
    return REPO_DATA_DIR / name


def load_json(name: str, fallback):
    try:
        return json.loads(data_path(name).read_text(encoding="utf-8"))
    except Exception:
        return fallback


def status_key(game: dict) -> str:
    return str(game.get("status") or "scheduled").strip().lower()


def is_live(game: dict) -> bool:
    key = status_key(game)
    return key in LIVE_STATUSES or any(token in key for token in ("live", "progress", "試合中"))


def is_final(game: dict) -> bool:
    key = status_key(game)
    return key in FINAL_STATUSES or any(token in key for token in ("final", "finish", "終了"))


def status_label(game: dict) -> tuple[str, str]:
    if is_live(game):
        return "LIVE", "live"
    if is_final(game):
        return "終了", "final"
    return str(game.get("time") or "開始前"), "scheduled"


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


apply_studio_theme()
render_topbar("GAMES / LIVE")
render_hero(
    "本日の試合",
    "NPBの対戦カード、開始時刻、球場、スコア、AI予測を一画面で確認。リアルタイム更新は試合中だけ有効になります。",
    kicker="AI BASEBALL STUDIO / MATCH CENTER",
    accent="試合",
)
render_nav_links()

payload = load_json("npb_today.json", {"games": []})
predictions = load_json("today_ai_predictions.json", {"games": []})
games = select_display_games(payload)
pred_by_game = prediction_index(predictions)
now = datetime.now(JST)
updated_at = payload.get("updated_at") or "--"
live_games = [game for game in games if is_live(game)]

st.markdown(
    f"""
<style>
{TEAM_BADGE_CSS}
.game-summary{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:14px 0 18px}}.game-kpi{{background:#11161b;border:1px solid rgba(255,255,255,.09);border-radius:13px;padding:14px}}.game-kpi span{{display:block;font-size:8px;letter-spacing:.18em;color:#d6ad39;font-weight:900}}.game-kpi strong{{display:block;margin-top:7px;font-size:22px;color:#fff}}.game-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}}.game-card{{background:#11161b;border:1px solid rgba(255,255,255,.09);border-radius:15px;padding:17px;box-shadow:0 8px 24px rgba(0,0,0,.12)}}.game-card.live{{border-color:#d5aa14;box-shadow:0 0 0 2px rgba(241,196,15,.10)}}.game-head{{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:14px}}.game-time{{font-size:10px;color:#9199a3}}.game-status{{font-size:9px;font-weight:950;border-radius:999px;padding:5px 9px;background:#242a31;color:#cbd1d7}}.game-status.live{{background:#171717;color:#f1c40f}}.game-status.final{{background:#242a31;color:#d8dde2}}.matchup{{display:grid;grid-template-columns:1fr 56px 1fr;gap:8px;align-items:center}}.team-side{{min-width:0}}.team-side.right{{text-align:right}}.team-heading{{display:flex;align-items:center;gap:9px;min-width:0}}.team-side.right .team-heading{{justify-content:flex-end}}.team-name{{font-size:18px;font-weight:900;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#fff}}.team-score{{font-size:31px;font-weight:950;line-height:1;margin-top:6px;color:#fff}}.vs{{text-align:center;color:#9b9387;font-size:10px;font-weight:900}}.game-meta{{border-top:1px solid rgba(255,255,255,.08);margin-top:14px;padding-top:12px;display:flex;justify-content:space-between;gap:12px;font-size:9px;color:#929aa4}}.prediction{{margin-top:11px;padding:10px 12px;border-radius:10px;background:#0b0e11;color:#fff;display:flex;justify-content:space-between;align-items:center;gap:12px}}.prediction span{{font-size:9px;color:#bbb}}.prediction strong{{font-size:14px;color:#f1c40f;display:flex;align-items:center;gap:7px}}.empty-games{{padding:28px;background:#11161b;border:1px dashed rgba(255,255,255,.14);border-radius:14px;color:#8f98a2;text-align:center;font-size:12px}}.sync-note{{margin:10px 0 16px;padding:10px 12px;border-radius:10px;background:#2b240d;border:1px solid #6f5a18;font-size:10px;color:#dfc46b}}
@media(max-width:850px){{.game-summary{{grid-template-columns:repeat(2,1fr)}}.game-grid{{grid-template-columns:1fr}}}}@media(max-width:520px){{.game-summary{{grid-template-columns:1fr 1fr}}.team-name{{font-size:15px}}.team-score{{font-size:27px}}.matchup{{grid-template-columns:1fr 42px 1fr}}.game-meta{{flex-direction:column;gap:4px}}}}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    f"""
<div class="game-summary">
  <div class="game-kpi"><span>DISPLAY GAMES</span><strong>{len(games)}</strong></div>
  <div class="game-kpi"><span>LIVE NOW</span><strong>{len(live_games)}</strong></div>
  <div class="game-kpi"><span>DATA UPDATED</span><strong style="font-size:13px">{html.escape(str(updated_at))}</strong></div>
  <div class="game-kpi"><span>JST</span><strong>{now.strftime('%H:%M')}</strong></div>
</div>
""",
    unsafe_allow_html=True,
)

if live_games:
    st.markdown(
        '<div class="sync-note">● 試合中のため30秒ごとに画面を自動更新します。試合がない時間帯は自動更新しません。</div>',
        unsafe_allow_html=True,
    )
    components.html(
        """
<script>
window.setTimeout(function () {
  try { window.parent.location.reload(); } catch (e) {}
}, 30000);
</script>
""",
        height=0,
    )

render_section("MATCH CENTER", "試合一覧")

if not games:
    st.markdown(
        '<div class="empty-games">本日または直近の試合データがありません。次回データ同期後に自動表示されます。</div>',
        unsafe_allow_html=True,
    )
else:
    cards = []
    for game in games:
        home_raw = str(game.get("home") or "---")
        away_raw = str(game.get("away") or "---")
        home = html.escape(home_raw)
        away = html.escape(away_raw)
        venue = html.escape(str(game.get("venue") or "会場未定"))
        game_date = html.escape(str(game.get("date") or payload.get("date") or ""))
        label, cls = status_label(game)
        pred = pred_by_game.get((home_raw, away_raw), {})
        pick_raw = str(pred.get("pick") or "")
        pick = html.escape(pick_raw)
        prob = pred.get("win_probability")
        pred_html = ""
        if pick:
            prob_label = f"{float(prob):.1f}%" if isinstance(prob, (int, float)) else "--"
            pred_html = f'<div class="prediction"><span>AI PICK</span><strong>{team_badge(pick_raw, size="sm")}{pick} · {prob_label}</strong></div>'
        cards.append(
            f'''<article class="game-card {"live" if cls == "live" else ""}">
  <div class="game-head"><div class="game-time">{game_date} · {html.escape(str(game.get("time") or "--:--"))} · {venue}</div><div class="game-status {cls}">{html.escape(label)}</div></div>
  <div class="matchup">
    <div class="team-side"><div class="team-heading">{team_badge(away_raw, size="md")}<div class="team-name">{away}</div></div><div class="team-score">{score_text(game.get("away_score"))}</div></div>
    <div class="vs">VS</div>
    <div class="team-side right"><div class="team-heading"><div class="team-name">{home}</div>{team_badge(home_raw, size="md")}</div><div class="team-score">{score_text(game.get("home_score"))}</div></div>
  </div>
  <div class="game-meta"><span>STATUS: {html.escape(str(game.get("status") or "scheduled"))}</span><span>RESULT: {html.escape(str(game.get("result_source") or "NPB公式"))}</span></div>
  {pred_html}
</article>'''
        )
    st.markdown(f'<div class="game-grid">{"".join(cards)}</div>', unsafe_allow_html=True)

st.caption("リアルタイム更新は試合中のみ。表示データは本番共有データを優先して読み込みます。")
