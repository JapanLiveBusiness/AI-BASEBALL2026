from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st
import streamlit.components.v1 as components

from display_games import select_display_context
from studio_theme import apply_studio_theme, render_nav_links, render_topbar
from team_branding import TEAM_BADGE_CSS, team_badge

JST = ZoneInfo("Asia/Tokyo")
REPO_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PROD_DATA_DIR = Path("/app/data")
SLATE_ARCHIVE = PROD_DATA_DIR / "npb_slates_archive.json"
LIVE_STATUSES = {"live", "in_progress", "playing", "試合中", "開催中"}
FINAL_STATUSES = {"final", "finished", "completed", "終了", "試合終了"}
HAWKS_ALIASES = ("ソフトバンク", "ホークス", "福岡ソフトバンク")

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


def load_archive() -> list[dict]:
    try:
        data = json.loads(SLATE_ARCHIVE.read_text(encoding="utf-8"))
        return list(data if isinstance(data, list) else [])
    except Exception:
        return []


def archive_current_slate(payload: dict) -> list[dict]:
    archive = load_archive()
    slate_date = str(payload.get("date") or "")
    games = list(payload.get("games") or [])
    if not slate_date or not games:
        return archive

    compact = {
        "date": slate_date,
        "updated_at": payload.get("updated_at"),
        "games": games,
    }
    archive = [row for row in archive if str(row.get("date") or "") != slate_date]
    archive.append(compact)
    archive.sort(key=lambda row: str(row.get("date") or ""))
    archive = archive[-14:]

    try:
        PROD_DATA_DIR.mkdir(parents=True, exist_ok=True)
        SLATE_ARCHIVE.write_text(
            json.dumps(archive, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass
    return archive


def status_key(game: dict) -> str:
    return str(game.get("status") or "scheduled").strip().lower()


def is_live(game: dict) -> bool:
    key = status_key(game)
    return key in LIVE_STATUSES or any(token in key for token in ("live", "progress", "試合中"))


def is_final(game: dict) -> bool:
    key = status_key(game)
    return key in FINAL_STATUSES or any(token in key for token in ("final", "finish", "終了"))


def status_label(game: dict) -> str:
    if is_live(game):
        inning = str(game.get("inning") or game.get("inning_text") or "").strip()
        return f"LIVE {inning}".strip()
    if is_final(game):
        return "試合終了"
    return "試合開始前"


def score_value(value) -> str:
    return "-" if value is None or value == "" else html.escape(str(value))


def prediction_index(payload: dict) -> dict[tuple[str, str], dict]:
    out = {}
    for row in payload.get("games") or []:
        home = str(row.get("home") or "")
        away = str(row.get("away") or "")
        if home and away:
            out[(home, away)] = row
    return out


def game_prediction(predictions: dict, game: dict, display_date: str | None, payload_date: str) -> dict:
    if str(game.get("date") or display_date or "") != str(payload_date or ""):
        return {}
    return predictions.get((str(game.get("home") or ""), str(game.get("away") or "")), {})


def featured_game(games: list[dict]) -> dict | None:
    for game in games:
        joined = f"{game.get('home', '')} {game.get('away', '')}"
        if any(alias in joined for alias in HAWKS_ALIASES):
            return game
    return games[0] if games else None


def starter_name(game: dict, side: str) -> str:
    if side == "home":
        keys = ("home_starter", "home_pitcher", "starter_home")
    else:
        keys = ("away_starter", "away_pitcher", "starter_away")
    for key in keys:
        value = str(game.get(key) or "").strip()
        if value:
            return value
    return "発表待ち"


def starter_meta(game: dict, side: str) -> str:
    wins = game.get(f"{side}_starter_wins")
    losses = game.get(f"{side}_starter_losses")
    era = game.get(f"{side}_starter_era")
    if wins is None and losses is None and era is None:
        return "成績データ取得待ち"
    wins_text = "－" if wins is None else str(wins)
    losses_text = "－" if losses is None else str(losses)
    era_text = "－" if era is None else str(era)
    return f"{wins_text}勝 {losses_text}敗 ｜ 防御率 {era_text}"


def recent_summary(game: dict) -> str:
    for key in ("recent_record", "recent_5", "head_to_head_recent"):
        value = str(game.get(key) or "").strip()
        if value:
            return value
    return "データ取得待ち"


apply_studio_theme()
render_topbar("GAMES / LIVE")
render_nav_links()

payload = load_json("npb_today.json", {"games": []})
prediction_payload = load_json("today_ai_predictions.json", {"games": []})
archive = archive_current_slate(payload)
previous_payloads = [
    row for row in archive
    if str(row.get("date") or "") != str(payload.get("date") or "")
]
now = datetime.now(JST)
display = select_display_context(
    payload,
    previous_payloads=previous_payloads,
    now=now,
    lead_hours=2,
)
games = list(display["games"] or [])
display_date = display["display_date"]
next_date = display["next_date"]
switch_at = display["switch_at"]
is_previous_preview = display["is_previous_preview"]
updated_at = payload.get("updated_at") or "--"
pred_by_game = prediction_index(prediction_payload)
live_games = [game for game in games if is_live(game)]
featured = featured_game(games)

st.markdown(
    f"""
<style>
{TEAM_BADGE_CSS}
.block-container{{max-width:1440px!important}}
.premium-shell{{margin:0 0 22px;padding:12px 18px 18px;border-radius:0 0 20px 20px;background:linear-gradient(145deg,#06090d,#0c1218 68%,#05080b);box-shadow:0 18px 44px rgba(5,12,20,.24);color:#fff}}
.premium-news{{display:flex;align-items:center;gap:18px;min-height:54px;padding:0 20px;border:1px solid rgba(219,177,59,.75);border-radius:15px;background:rgba(4,8,11,.86);font-weight:850}}
.premium-news .dot{{width:12px;height:12px;border-radius:50%;background:#ef2632;box-shadow:0 0 12px rgba(239,38,50,.55)}}
.premium-news .source{{padding-right:18px;border-right:1px solid rgba(255,255,255,.18)}}
.premium-news .auto{{margin-left:auto;padding:7px 13px;border:1px solid #d8ae34;border-radius:10px;color:#f4cc55;font-size:.78rem;white-space:nowrap}}
.premium-card{{overflow:hidden;margin-top:8px;border-radius:20px;background:#fff;color:#10151d;box-shadow:0 12px 34px rgba(0,0,0,.28)}}
.premium-score{{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;min-height:155px;padding:26px 38px 18px}}
.premium-team{{display:flex;align-items:center;gap:18px;min-width:0}}.premium-team.right{{justify-content:flex-end;text-align:right}}
.premium-team .team-badge-lg{{width:82px;height:82px;font-size:27px;border:1px solid #edf0f3;box-shadow:0 6px 20px rgba(14,26,42,.14)}}
.premium-team-name{{font-size:1.45rem;font-weight:950;color:#10151d}}.premium-team-sub{{margin-top:4px;color:#687383;font-size:.74rem;font-weight:750}}.premium-team-record{{margin-top:8px;color:#394455;font-size:.78rem;font-weight:800}}
.premium-scoreline{{text-align:center;padding:0 28px;min-width:220px}}.premium-scoreline .numbers{{font-size:3.9rem;line-height:1;font-weight:950;letter-spacing:.04em;color:#10151d}}.premium-scoreline .accent{{color:#d51e2a}}
.premium-status{{display:inline-flex;margin-top:12px;padding:6px 13px;border-radius:999px;background:#0a0e13;color:#fff;font-size:.74rem;font-weight:900}}
.premium-venue{{margin-top:12px;font-weight:900;color:#202a38}}.premium-time{{margin-top:4px;color:#6d7785;font-size:.8rem;font-weight:750}}
.premium-result{{display:flex;justify-content:center;gap:24px;padding:13px;border-top:1px solid #eef0f2;color:#1b2028;font-weight:900}}
.premium-ai{{display:grid;grid-template-columns:auto 230px 1fr auto;align-items:center;gap:18px;margin:18px;padding:24px;border:1px solid #e7eaee;border-radius:16px;box-shadow:0 5px 20px rgba(10,25,42,.05)}}
.premium-bot{{display:grid;place-items:center;width:64px;height:64px;border-radius:50%;background:#075c37;color:#fff;font-size:1.8rem}}
.premium-ai-label{{font-weight:850;color:#1a2432}}.premium-prob{{color:#2daf68;font-size:2.8rem;font-weight:950;line-height:1.05}}.premium-pick{{color:#687383;font-size:.78rem;font-weight:800}}
.premium-track{{height:15px;overflow:hidden;border-radius:999px;background:#e0e4e9}}.premium-track>span{{display:block;height:100%;border-radius:inherit;background:linear-gradient(90deg,#28b563,#54c883)}}
.premium-confidence{{text-align:center;font-weight:850;color:#303a47}}.premium-confidence b{{display:block;color:#27ae65;font-size:1.5rem}}
.premium-detail-title{{margin:0 18px;padding:18px 22px;border-radius:14px 14px 0 0;background:#070b0f;color:#fff;font-weight:900}}
.premium-details{{display:grid;grid-template-columns:repeat(3,1fr);margin:0 18px 18px;border:1px solid #e5e8ec;border-top:0;border-radius:0 0 14px 14px}}
.premium-detail{{padding:18px;border-right:1px solid #e8ebee}}.premium-detail:last-child{{border-right:0}}.premium-detail small{{display:block;margin-bottom:9px;color:#677383;font-weight:750}}.premium-detail b{{font-size:1rem;color:#17233a}}.premium-detail .green{{color:#20a95e}}
.premium-starters{{display:grid;grid-template-columns:1fr auto 1fr;align-items:stretch;gap:14px;margin:0 18px 18px}}
.premium-starter{{display:flex;align-items:center;gap:14px;padding:16px;border:1px solid #e3e8ee;border-radius:14px;background:#f8fafc}}.premium-starter.right{{text-align:right;justify-content:flex-end}}
.pitcher-icon{{display:grid;place-items:center;width:58px;height:58px;flex:0 0 58px;border-radius:50%;background:#0d1722;color:#fff;font-size:1.45rem}}
.starter-label{{font-size:.75rem;color:#697686;font-weight:800}}.starter-name{{margin-top:3px;font-size:1.1rem;color:#152131;font-weight:950}}.starter-meta{{margin-top:4px;font-size:.76rem;color:#6b7583;font-weight:700}}.starter-vs{{display:grid;place-items:center;color:#7a8490;font-weight:950}}
.premium-foot{{display:flex;justify-content:space-between;padding:4px 8px 2px;color:#aab2bc;font-size:.74rem}}
.preview-note{{margin:12px 0 0;padding:11px 13px;border-radius:10px;background:#111b25;border:1px solid #28435d;font-size:10px;color:#b9d8f5}}.preview-note strong{{color:#fff}}
.results-section{{margin:20px 0 24px}}.results-title{{display:flex;align-items:center;gap:9px;margin-bottom:12px;font-size:1.08rem;font-weight:950;color:#fff}}
.results-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}}.result-card{{background:#fff;border:1px solid #e2e7ed;border-radius:15px;padding:16px;color:#111821;box-shadow:0 7px 22px rgba(0,0,0,.14)}}
.result-head{{display:flex;justify-content:space-between;gap:10px;color:#718094;font-size:.78rem;font-weight:750}}.result-status{{font-weight:950;color:#334155}}.result-status.live{{color:#d72632}}
.result-match{{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:12px;margin-top:14px}}.result-team{{display:flex;align-items:center;gap:8px;font-weight:950}}.result-team.right{{justify-content:flex-end;text-align:right}}.result-score{{font-size:2rem;font-weight:950;color:#111821;white-space:nowrap}}.result-meta{{display:flex;justify-content:space-between;gap:10px;margin-top:13px;padding-top:10px;border-top:1px solid #edf0f3;color:#6e7a8b;font-size:.75rem}}
.ai-chip{{display:inline-flex;align-items:center;gap:6px;padding:5px 8px;border-radius:999px;background:#eef8f2;color:#16854c;font-weight:900}}
.empty-state{{padding:28px;border:1px dashed rgba(255,255,255,.18);border-radius:14px;color:#9ca8b6;text-align:center;background:#0c1117}}
@media(max-width:900px){{.premium-score{{grid-template-columns:1fr;gap:18px;text-align:center;padding:24px 20px}}.premium-team,.premium-team.right{{justify-content:center;text-align:center}}.premium-team.right{{flex-direction:row-reverse}}.premium-scoreline{{order:2}}.premium-team:first-child{{order:1}}.premium-team.right{{order:3}}.premium-ai{{grid-template-columns:auto 1fr;}}.premium-track{{grid-column:1/-1}}.premium-confidence{{grid-column:1/-1}}.premium-details{{grid-template-columns:1fr}}.premium-detail{{border-right:0;border-bottom:1px solid #e8ebee}}.premium-detail:last-child{{border-bottom:0}}.premium-starters{{grid-template-columns:1fr}}.starter-vs{{min-height:20px}}.results-grid{{grid-template-columns:1fr}}}}
@media(max-width:620px){{.premium-shell{{padding:8px}}.premium-news{{flex-wrap:wrap;gap:8px;padding:10px 12px}}.premium-news .source{{border-right:0;padding-right:0}}.premium-news .auto{{margin-left:0}}.premium-team .team-badge-lg{{width:58px;height:58px;font-size:20px}}.premium-team-name{{font-size:1.15rem}}.premium-scoreline .numbers{{font-size:3rem}}.premium-ai{{margin:12px;padding:16px}}.premium-prob{{font-size:2.2rem}}.premium-detail-title,.premium-details,.premium-starters{{margin-left:12px;margin-right:12px}}}}
</style>
""",
    unsafe_allow_html=True,
)

if not games or featured is None:
    st.markdown('<div class="premium-shell"><div class="empty-state">表示できる試合データがありません。次回データ同期後に自動表示されます。</div></div>', unsafe_allow_html=True)
else:
    home_raw = str(featured.get("home") or "---")
    away_raw = str(featured.get("away") or "---")
    home = html.escape(home_raw)
    away = html.escape(away_raw)
    venue = html.escape(str(featured.get("venue") or "会場未定"))
    game_time = html.escape(str(featured.get("time") or "--:--"))
    featured_date = str(featured.get("date") or display_date or "")
    feature_pred = game_prediction(pred_by_game, featured, display_date, str(payload.get("date") or ""))
    pick_raw = str(feature_pred.get("pick") or "AI分析待ち")
    prob = feature_pred.get("win_probability")
    try:
        probability = float(prob)
    except (TypeError, ValueError):
        probability = 50.0
    confidence = str(feature_pred.get("confidence") or "-")
    current_status = status_label(featured)
    refresh_label = "↻ LIVE自動更新（15秒）" if live_games else "試合中のみ自動更新"

    preview_html = ""
    if is_previous_preview and switch_at is not None:
        preview_html = (
            '<div class="preview-note">現在は '
            f'<strong>{html.escape(str(display_date))}</strong> の試合を表示中です。'
            f'次の試合カード <strong>{html.escape(str(next_date))}</strong> は '
            f'<strong>{switch_at.strftime("%m/%d %H:%M")}</strong>（最初の試合開始2時間前）に自動切替します。</div>'
        )

    result_html = ""
    if is_final(featured):
        result_html = '<div class="premium-result"><span>FINAL</span><span>試合終了</span></div>'
    elif is_live(featured):
        result_html = '<div class="premium-result"><span style="color:#d72632">● LIVE</span><span>試合速報更新中</span></div>'

    if feature_pred:
        ai_html = (
            f'<div class="premium-ai">'
            f'<div class="premium-bot">🤖</div>'
            f'<div><div class="premium-ai-label">AI 勝率予測</div>'
            f'<div class="premium-prob">{probability:.1f}%</div>'
            f'<div class="premium-pick">注目チーム：{html.escape(pick_raw)}</div></div>'
            f'<div class="premium-track"><span style="width:{max(0.0, min(100.0, probability)):.1f}%"></span></div>'
            f'<div class="premium-confidence">信頼度<b>{html.escape(confidence)}</b></div>'
            f'</div>'
        )
    else:
        ai_html = (
            '<div class="premium-ai"><div class="premium-bot">🤖</div>'
            '<div><div class="premium-ai-label">AI 勝率予測</div><div class="premium-prob" style="color:#7a8490">--</div><div class="premium-pick">分析データ待ち</div></div>'
            '<div class="premium-track"><span style="width:0%"></span></div><div class="premium-confidence">信頼度<b style="color:#7a8490">-</b></div></div>'
        )

    feature_html = f"""
<div class="premium-shell">
  <div class="premium-news">
    <span class="dot"></span><span class="source">NPB公式速報</span>
    <span>{html.escape(featured_date)}</span><span>{venue}</span>
    <span class="auto">{refresh_label}</span>
  </div>
  {preview_html}
  <div class="premium-card">
    <div class="premium-score">
      <div class="premium-team">
        {team_badge(away_raw, size="lg")}
        <div><div class="premium-team-name">{away}</div><div class="premium-team-sub">AWAY</div><div class="premium-team-record">{html.escape(starter_name(featured, "away"))} 先発予定</div></div>
      </div>
      <div class="premium-scoreline">
        <div class="numbers">{score_value(featured.get("away_score"))} − <span class="accent">{score_value(featured.get("home_score"))}</span></div>
        <span class="premium-status">{html.escape(current_status)}</span>
        <div class="premium-venue">{venue}</div><div class="premium-time">{game_time} 開始予定</div>
      </div>
      <div class="premium-team right">
        <div><div class="premium-team-name">{home}</div><div class="premium-team-sub">HOME</div><div class="premium-team-record">{html.escape(starter_name(featured, "home"))} 先発予定</div></div>
        {team_badge(home_raw, size="lg")}
      </div>
    </div>
    {result_html}
    {ai_html}
    <div class="premium-detail-title">☷　詳細情報</div>
    <div class="premium-details">
      <div class="premium-detail"><small>対戦成績（直近）</small><b class="green">{html.escape(recent_summary(featured))}</b></div>
      <div class="premium-detail"><small>球場</small><b>{venue}</b></div>
      <div class="premium-detail"><small>開始時間</small><b>{game_time}</b></div>
    </div>
    <div class="premium-starters">
      <div class="premium-starter"><div class="pitcher-icon">⚾</div><div><div class="starter-label">{away} 予告先発</div><div class="starter-name">{html.escape(starter_name(featured, "away"))}</div><div class="starter-meta">{html.escape(starter_meta(featured, "away"))}</div></div></div>
      <div class="starter-vs">VS</div>
      <div class="premium-starter right"><div><div class="starter-label">{home} 予告先発</div><div class="starter-name">{html.escape(starter_name(featured, "home"))}</div><div class="starter-meta">{html.escape(starter_meta(featured, "home"))}</div></div><div class="pitcher-icon">⚾</div></div>
    </div>
  </div>
  <div class="premium-foot"><span>※ リアルタイム更新は試合中のみ有効です</span><span>データ更新：{html.escape(str(updated_at))}</span></div>
</div>
"""
    st.markdown(feature_html, unsafe_allow_html=True)

    st.markdown('<div class="results-section"><div class="results-title"><span>⚾</span>NPB 試合一覧</div>', unsafe_allow_html=True)
    result_cards = []
    for game in games:
        if game is featured:
            continue
        home_raw = str(game.get("home") or "---")
        away_raw = str(game.get("away") or "---")
        venue = html.escape(str(game.get("venue") or "会場未定"))
        pred = game_prediction(pred_by_game, game, display_date, str(payload.get("date") or ""))
        pred_chip = ""
        if pred:
            p_pick = html.escape(str(pred.get("pick") or ""))
            p_prob = pred.get("win_probability")
            p_prob_text = f"{float(p_prob):.0f}%" if isinstance(p_prob, (int, float)) else "--"
            pred_chip = f'<span class="ai-chip">AI {p_pick} {p_prob_text}</span>'
        status = status_label(game)
        status_class = "live" if is_live(game) else ""
        result_cards.append(
            f'''<article class="result-card">
  <div class="result-head"><span>{html.escape(str(game.get("time") or "--:--"))} · {venue}</span><span class="result-status {status_class}">{html.escape(status)}</span></div>
  <div class="result-match">
    <div class="result-team">{team_badge(away_raw, size="md")}<span>{html.escape(away_raw)}</span></div>
    <div class="result-score">{score_value(game.get("away_score"))} − {score_value(game.get("home_score"))}</div>
    <div class="result-team right"><span>{html.escape(home_raw)}</span>{team_badge(home_raw, size="md")}</div>
  </div>
  <div class="result-meta"><span>{pred_chip or "AI分析待ち"}</span><span>{html.escape(str(game.get("result_source") or "NPB公式"))}</span></div>
</article>'''
        )

    if result_cards:
        st.markdown(f'<div class="results-grid">{"".join(result_cards)}</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="empty-state">この表示日には他の試合カードはありません。</div></div>', unsafe_allow_html=True)

if live_games:
    components.html(
        """
<script>
window.setTimeout(function () {
  try { window.parent.location.reload(); } catch (e) {}
}, 15000);
</script>
""",
        height=0,
    )

st.caption(
    f"切替基準: 次の試合日の最初の試合開始2時間前。表示日: {display_date or '--'}。"
    "リアルタイム同期は試合中のみ実行します。"
)
