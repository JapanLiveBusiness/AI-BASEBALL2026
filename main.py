from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import html
import json

import streamlit as st

from bet_analytics import calculate_hit_rate, point_delta
from studio_theme import apply_studio_theme, render_topbar, render_hero

JST = ZoneInfo("Asia/Tokyo")
REPO_DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIRS = [Path("/app/data"), REPO_DATA_DIR]

st.set_page_config(
    page_title="AI BASEBALL STUDIO | RESEARCH",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="collapsed",
)
apply_studio_theme()


def load_json(name, fallback):
    for directory in DATA_DIRS:
        try:
            path = directory / name
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
    return fallback


def esc(value, fallback="-"):
    if value in (None, ""):
        value = fallback
    return html.escape(str(value))


def legacy_to_analysis(record):
    try:
        weight = abs(float(record.get("bet_units") or 0))
    except (TypeError, ValueError):
        weight = 0.0
    result = record.get("result")
    delta = weight if result == "win" else (-weight if result == "loss" else 0.0)
    return {
        "date": record.get("date"),
        "time": record.get("time"),
        "team": record.get("team"),
        "opponent": record.get("opponent"),
        "handicap": record.get("handicap", 0),
        "status": record.get("status", "pending"),
        "result": result,
        "point_delta": delta,
        "team_score": record.get("team_score"),
        "opponent_score": record.get("opponent_score"),
    }


def load_analysis_records():
    current = load_json("simulation_records.json", [])
    legacy = load_json("bet_records.json", [])
    if not isinstance(current, list):
        current = []
    if not isinstance(legacy, list):
        legacy = []

    merged = []
    seen = set()
    for record in [legacy_to_analysis(r) for r in legacy] + current:
        key = (
            str(record.get("date", "")),
            str(record.get("time", "")),
            str(record.get("team", "")),
            str(record.get("opponent", "")),
            str(record.get("handicap", "")),
        )
        if key in seen:
            continue
        seen.add(key)
        merged.append(record)
    return merged


predictions = load_json("today_ai_predictions.json", {"games": []})
npb_today = load_json("npb_today.json", {"games": []})
analysis_records = load_analysis_records()

prediction_games = predictions.get("games") or []
today_games = npb_today.get("games") or []
settled = [r for r in analysis_records if r.get("status") == "final"]
_, _, success_rate = calculate_hit_rate(settled)
total_delta = sum(point_delta(r) for r in settled)
now = datetime.now(JST)
ranked = sorted(prediction_games, key=lambda g: g.get("rank", 999))

prediction_lookup = {}
for game in prediction_games:
    key = (str(game.get("home", "")), str(game.get("away", "")))
    prediction_lookup[key] = game

render_topbar("リサーチモード")
render_hero(
    "野球AI分析 × 得点補正シミュレーション",
    "AIによる勝率予測と得点補正による感度分析で、仮説の検証とモデル精度の確認をサポートします。",
    kicker=f"{now.strftime('%Y年%m月%d日')} / データ更新 {now.strftime('%H:%M')}",
)

# KPI row
st.markdown('<div class="kpi-grid">', unsafe_allow_html=True)
kpis = [
    ("🗓", "本日の試合数", f"{len(today_games)}", "試合"),
    ("🏆", "AI評価数", f"{len(prediction_games)}", "本日の予測"),
    ("📈", "分析シミュレーション", f"{len(analysis_records)}", "累計シナリオ"),
    ("🎯", "仮説成立率", f"{success_rate:.1f}%" if success_rate is not None else "-", "確定データ"),
    ("◎", "総評価スコア差", f"{total_delta:+.1f}", "研究指標"),
]
for icon, label, value, note in kpis:
    value_cls = " gold" if label == "総評価スコア差" else ""
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-icon">{icon}</div><div><div class="kpi-label">{label}</div><div class="kpi-value{value_cls}">{value}</div><div class="kpi-note">{note}</div></div></div>',
        unsafe_allow_html=True,
    )
st.markdown('</div>', unsafe_allow_html=True)

# Middle row: games + top AI
left, right = st.columns([1.65, 0.85], gap="small")
with left:
    rows = []
    for game in sorted(today_games, key=lambda g: str(g.get("time", "99:99"))):
        home = str(game.get("home", "-"))
        away = str(game.get("away", "-"))
        pred = prediction_lookup.get((home, away), {})
        pick = str(pred.get("pick", "-"))
        probability = pred.get("win_probability")
        try:
            p = float(probability)
        except (TypeError, ValueError):
            p = None

        if p is None:
            home_prob = away_prob = "-"
        elif pick == home:
            home_prob, away_prob = f"{p:.1f}%", f"{100-p:.1f}%"
        elif pick == away:
            home_prob, away_prob = f"{100-p:.1f}%", f"{p:.1f}%"
        else:
            home_prob = away_prob = "-"

        rows.append(
            f"<tr><td>{esc(game.get('time'))}</td><td><span class='team-strong'>{esc(home)}</span>　vs　<span class='team-strong'>{esc(away)}</span></td><td>{esc(game.get('venue'))}</td><td class='prob-gold'>{home_prob}</td><td class='prob-muted'>{away_prob}</td><td><span class='pick-chip'>{esc(pick, 'AI分析中')}</span></td></tr>"
        )

    table_html = "".join(rows) if rows else "<tr><td colspan='6'>本日の試合データはありません。</td></tr>"
    st.markdown(
        f'''<div class="dashboard-panel">
<div class="dashboard-title">⚾ 今日の試合カード</div>
<table class="match-table"><thead><tr><th>開始時間</th><th>対戦カード</th><th>球場</th><th>AI勝率（ホーム）</th><th>AI勝率（ビジター）</th><th>AI評価</th></tr></thead><tbody>{table_html}</tbody></table>
<a class="research-link" href="/試合" target="_self">全試合を見る　›</a>
</div>''',
        unsafe_allow_html=True,
    )

with right:
    top_rows = []
    for idx, game in enumerate(ranked[:3], start=1):
        probability = game.get("win_probability")
        probability_text = f"{float(probability):.1f}%" if isinstance(probability, (int, float)) else "-"
        top_rows.append(
            f'''<div class="top-ai-row"><div class="top-ai-rank">{idx}</div><div><div class="top-ai-name">{esc(game.get('pick'))}</div><div class="top-ai-meta">{esc(game.get('home'))} vs {esc(game.get('away'))}</div></div><div><div class="top-ai-prob">{probability_text}</div><div class="top-ai-meta" style="text-align:right">AI勝率</div></div></div>'''
        )
    st.markdown(
        f'''<div class="top-ai-card"><div class="dashboard-title gold">🏆 今日のTOP AI評価 <span style="margin-left:auto;font-size:9px;background:#3a2c0a;padding:5px 9px;border-radius:5px">TOP 3</span></div>{''.join(top_rows) if top_rows else '<div class="dashboard-subtle">予測データ準備中</div>'}<a class="research-link" href="/本日のAI予想" target="_self">AIランキングを見る　›</a></div>''',
        unsafe_allow_html=True,
    )

# Bottom row: research menu + recent analysis
st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)
left2, right2 = st.columns([1.65, 0.85], gap="small")
with left2:
    st.markdown('<div class="dashboard-panel"><div class="dashboard-title">🧪 研究・分析メニュー</div><div class="research-grid">', unsafe_allow_html=True)
    cards = [
        ("⚙", "得点補正シミュレーション", "得点補正値を設定してモデル結果の変化を分析", "/BET入力", "シミュレーション開始"),
        ("▥", "感度分析結果", "補正値ごとの成立率・評価スコアを確認", "/収支マップ", "結果を見る"),
        ("↶", "シミュレーション履歴", "これまでの分析シナリオと結果を確認", "/予想結果", "履歴を見る"),
        ("▤", "統計・レポート", "AI評価・精度・履歴をまとめて確認", "/本日のAI予想", "レポートを見る"),
    ]
    for icon, title, desc, href, cta in cards:
        st.markdown(
            f'''<div class="research-card"><div><div class="research-title">{title}</div><div class="research-icon">{icon}</div><div class="research-desc">{desc}</div></div><a class="research-link" href="{href}" target="_self">{cta}　›</a></div>''',
            unsafe_allow_html=True,
        )
    st.markdown('</div></div>', unsafe_allow_html=True)

with right2:
    recent = sorted(
        analysis_records,
        key=lambda r: (str(r.get("date", "")), str(r.get("time", ""))),
        reverse=True,
    )[:5]
    recent_rows = []
    for record in recent:
        result = record.get("result")
        if result == "win":
            chip = '<span class="status-chip status-win">成立</span>'
        elif result == "loss":
            chip = '<span class="status-chip status-loss">不成立</span>'
        else:
            chip = '<span class="status-chip status-pending">未確定</span>'
        delta = point_delta(record) if record.get("status") == "final" else 0.0
        recent_rows.append(
            f'''<div class="analysis-row"><div>{esc(record.get('date'))[-5:]} {esc(record.get('time'))}</div><div>{esc(record.get('team'))} vs {esc(record.get('opponent'))}</div><div>補正 {esc(record.get('handicap'), '0')}</div><div>{delta:+.1f}</div><div>{chip}</div></div>'''
        )
    st.markdown(
        f'''<div class="dashboard-panel"><div class="dashboard-title">📈 最近の感度分析結果 <a href="/収支マップ" target="_self" style="margin-left:auto;color:#9ca4ae;font-size:9px;text-decoration:none">すべて見る</a></div><div class="analysis-list">{''.join(recent_rows) if recent_rows else '<div class="dashboard-subtle">分析履歴はまだありません。</div>'}</div><a class="research-link" href="/収支マップ" target="_self">すべての履歴を見る　›</a></div>''',
        unsafe_allow_html=True,
    )

st.markdown(
    '<div class="footer-line"><span>ⓘ 本システムは研究・仮説検証を目的とした分析環境です。</span><span>© 2026 AI BASEBALL STUDIO.</span></div>',
    unsafe_allow_html=True,
)
