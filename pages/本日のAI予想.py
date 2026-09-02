from __future__ import annotations

import streamlit as st

from daily_board import coverage, merge_daily_board
from research_state import current_slate, prediction_for_display
from studio_theme import apply_studio_theme, render_topbar, render_hero, render_section, render_nav_links
from team_branding import TEAM_BADGE_CSS, team_badge

st.set_page_config(page_title="AI予測 | AI BASEBALL STUDIO", page_icon="⚾", layout="wide")
apply_studio_theme()
render_topbar("AI PREDICTION")
render_hero(
    "本日のAI予測",
    "セ・パ両リーグの全開催試合を対象に、表示日と一致するAI予測だけを比較します。",
    kicker="TODAY / NPB / AI PREDICTION",
    accent="AI予測",
)
render_nav_links()

st.markdown(
    f"""
<style>
{TEAM_BADGE_CSS}
.ai-match-title{{display:flex;align-items:center;gap:8px;flex-wrap:wrap}}.ai-vs{{color:#7f8791;font-size:12px}}.ai-pick-label{{display:flex;align-items:center;gap:8px;font-size:20px;font-weight:900}}.ai-best{{display:flex;align-items:center;gap:10px}}.league-chip{{display:inline-flex;margin-left:8px;padding:3px 7px;border-radius:999px;border:1px solid rgba(255,255,255,.14);font-size:8px;color:#9aa4ae}}
</style>
""",
    unsafe_allow_html=True,
)

slate = current_slate(lead_hours=2)
display_date = slate.get("display_date")
schedule = {
    "date": display_date,
    "updated_at": (slate.get("schedule") or {}).get("updated_at"),
    "games": list(slate.get("games") or []),
}
payload = prediction_for_display(display_date)
games = merge_daily_board(schedule, payload)
status = coverage(games)

render_section("DAILY BOARD", f"{display_date or '--'} NPB セ・パ全開催試合の予想と結果")

if not games:
    st.info("表示対象日の試合データを同期中です。")
    st.stop()

if str(payload.get("date") or "") != str(display_date or "") or not payload.get("games"):
    st.warning(
        f"{display_date or '表示日'} のAI予測はまだ生成されていません。"
        "試合カードは表示し、予測欄は分析待ちとして表示します。"
    )
elif not status["complete"]:
    st.warning(
        f"全{status['games']}試合中、予想済みは{status['predicted']}試合です。"
        "未生成の試合は分析待ちとして表示します。"
    )


def probability_value(game):
    try:
        return float(game.get("win_probability"))
    except (TypeError, ValueError):
        return -1.0


def league_label(game):
    if game.get("league"):
        return str(game.get("league"))
    central = {"巨人", "阪神", "DeNA", "横浜", "広島", "中日", "ヤクルト"}
    pacific = {"ソフトバンク", "ソフト", "ホークス", "日本ハム", "日ハム", "ロッテ", "楽天", "オリックス", "西武"}
    home = str(game.get("home") or "")
    away = str(game.get("away") or "")
    names = {home, away}
    has_c = any(any(alias in name for alias in central) for name in names)
    has_p = any(any(alias in name for alias in pacific) for name in names)
    if has_c and not has_p:
        return "セ・リーグ"
    if has_p and not has_c:
        return "パ・リーグ"
    return "交流戦" if has_c and has_p else "NPB"


ordered_games = sorted(
    games,
    key=lambda game: (
        probability_value(game),
        -int(game.get("rank") or 999),
    ),
    reverse=True,
)

for display_rank, game in enumerate(ordered_games, start=1):
    source_rank = game.get("rank")
    home = game.get("home", "-")
    away = game.get("away", "-")
    pick = game.get("pick")
    prob = game.get("win_probability")
    score = game.get("predicted_score") or "-"
    confidence = game.get("confidence") or "-"
    home_score = game.get("home_score")
    away_score = game.get("away_score")
    result = game.get("actual_result", "未確定")
    verified = game.get("verified")
    has_prediction = bool(pick) and probability_value(game) >= 0

    c1, c2, c3, c4 = st.columns([0.7, 2.4, 1.8, 1.4])
    with c1:
        st.markdown(
            f'<div class="studio-rank">{display_rank if has_prediction else "—"}</div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="ai-match-title">{team_badge(home, size="md")}<strong>{home}</strong>'
            f'<span class="ai-vs">vs</span>{team_badge(away, size="md")}<strong>{away}</strong>'
            f'<span class="league-chip">{league_label(game)}</span></div>',
            unsafe_allow_html=True,
        )
        st.caption(f"開始 {game.get('time') or '--:--'} / 球場 {game.get('venue') or '-'} / 予想スコア {score if has_prediction else '-'}")
    with c3:
        if has_prediction:
            st.markdown(
                f'<div class="ai-pick-label">{team_badge(pick, size="sm")}<span>{pick}</span></div>',
                unsafe_allow_html=True,
            )
            st.caption(f"推定勝率 {float(prob):.1f}%")
        else:
            st.markdown('<div class="ai-pick-label"><span>分析待ち</span></div>', unsafe_allow_html=True)
            st.caption("当日予測の生成待ち")
    with c4:
        st.metric("信頼度", confidence if has_prediction else "-")

    if has_prediction:
        st.progress(max(0.0, min(100.0, float(prob))) / 100.0)
    else:
        st.progress(0)

    if result != "未確定":
        verdict = "一致" if verified is True else "不一致" if verified is False else "判定対象外"
        st.markdown(f"結果: **{away} {away_score} - {home_score} {home}** ／ 勝者 **{result}** ／ {verdict}")
    else:
        st.caption(f"試合結果: 未確定（{game.get('status') or '開始前'}）")
    st.divider()

ranked = [game for game in ordered_games if game.get("pick") and probability_value(game) >= 0]
best = ranked[0] if ranked else None
render_section("TOP AI PROBABILITY", "当日NPB全試合の最高AI勝率")
if best:
    left, mid, right = st.columns([1.6, 1, 1])
    left.markdown(
        f'<div class="ai-best">{team_badge(best.get("pick"), size="lg")}<h2 style="margin:0">{best.get("pick", "-")}</h2></div>',
        unsafe_allow_html=True,
    )
    left.caption(
        f"{league_label(best)} / {best.get('home', '-')} vs {best.get('away', '-')} / "
        f"予想スコア {best.get('predicted_score', '-')}"
    )
    mid.metric("推定勝率", f"{float(best.get('win_probability')):.1f}%")
    right.metric("信頼度", best.get("confidence", "-"))
else:
    st.info("当日予測が生成されると、セ・パ両リーグを通した最高AI勝率の試合をここに表示します。")

st.caption("※AI勝率は野球モデルの分析値です。試合結果を保証するものではありません。")
