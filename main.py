from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

from bet_analytics import calculate_hit_rate, point_delta
from research_state import current_slate, freshness, load_json, prediction_for_display
from team_branding import TEAM_BADGE_CSS, team_badge

JST = ZoneInfo("Asia/Tokyo")
PROD_DATA_DIR = Path("/app/data")
REPO_DATA_DIR = Path(__file__).resolve().parent / "data"

st.set_page_config(
    page_title="AI BASEBALL STUDIO | RESEARCH",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def esc(value, fallback="-"):
    if value in (None, ""):
        value = fallback
    return html.escape(str(value))


def load_records():
    path = PROD_DATA_DIR / "simulation_records.json"
    if not path.exists():
        path = REPO_DATA_DIR / "simulation_records.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def load_report():
    path = PROD_DATA_DIR / "historical_backtest_report.json"
    if not path.exists():
        path = REPO_DATA_DIR / "historical_backtest_report.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def status_label(game):
    key = str(game.get("status") or "scheduled").lower()
    if any(token in key for token in ("live", "progress", "試合中", "開催中")):
        return "LIVE", "live"
    if any(token in key for token in ("final", "finish", "終了")):
        return "終了", "final"
    return "開始前", "scheduled"


now = datetime.now(JST)
weekday = "月火水木金土日"[now.weekday()]
slate = current_slate(now=now, lead_hours=2)
schedule = slate["schedule"]
display_date = slate.get("display_date")
display_games = list(slate.get("games") or [])
switch_at = slate.get("switch_at")
predictions = prediction_for_display(display_date)
prediction_games = list(predictions.get("games") or [])
prediction_lookup = {(str(g.get("home") or ""), str(g.get("away") or "")): g for g in prediction_games}
ranked = sorted(prediction_games, key=lambda g: int(g.get("rank") or 999))
records = load_records()
settled = [r for r in records if r.get("status") == "final"]
_, _, success_rate = calculate_hit_rate(settled)
total_delta = sum(point_delta(r) for r in settled)
report = load_report()
report_models = list(report.get("overall") or [])
best_model = min(report_models, key=lambda row: float(row.get("brier") or 999), default={})
schedule_health = freshness(schedule, now)
pred_health = freshness(load_json("today_ai_predictions.json", {"games": []}), now)
live_count = sum(1 for g in display_games if status_label(g)[1] == "live")

match_rows = []
for game in sorted(display_games, key=lambda g: str(g.get("time") or "99:99")):
    home = str(game.get("home") or "-")
    away = str(game.get("away") or "-")
    pred = prediction_lookup.get((home, away), {})
    pick = str(pred.get("pick") or "")
    prob = pred.get("win_probability")
    try:
        p = float(prob)
    except (TypeError, ValueError):
        p = None
    status, status_class = status_label(game)
    ai_text = f"{esc(pick)} {p:.1f}%" if pick and p is not None else "分析待ち"
    score = ""
    if game.get("away_score") is not None and game.get("home_score") is not None:
        score = f"{esc(game.get('away_score'))} - {esc(game.get('home_score'))}"
    match_rows.append(
        f"<tr><td>{esc(game.get('time'))}</td>"
        f"<td><div class='matchup'><b>{esc(away)}</b><span class='vs'>vs</span><b>{esc(home)}</b></div></td>"
        f"<td>{esc(game.get('venue'))}</td><td>{esc(score, '—')}</td>"
        f"<td><span class='status {status_class}'>{status}</span></td><td>{ai_text}</td></tr>"
    )
match_html = "".join(match_rows) or "<tr><td colspan='6' class='empty'>表示できる試合データがありません。</td></tr>"

top_rows = []
for i, game in enumerate(ranked[:3], 1):
    try:
        prob = f"{float(game.get('win_probability')):.1f}%"
    except (TypeError, ValueError):
        prob = "-"
    pick = str(game.get("pick") or "-")
    top_rows.append(
        f"<div class='rank-row'><div class='rank-no'>{i}</div>"
        f"<div class='rank-team'>{team_badge(pick, size='lg')}<div><b>{esc(pick)}</b>"
        f"<small>{esc(game.get('away'))} vs {esc(game.get('home'))}</small></div></div>"
        f"<div class='rank-prob'>{prob}<small>AI勝率</small></div></div>"
    )
top_html = "".join(top_rows) or "<div class='empty'>表示日のAI予測データはまだありません。</div>"

recent_rows = []
for record in sorted(records, key=lambda r: (str(r.get("date") or ""), str(r.get("time") or "")), reverse=True)[:5]:
    result = record.get("result")
    status_class = "ok" if result == "win" else ("ng" if result == "loss" else "wait")
    status_text = "成立" if result == "win" else ("不成立" if result == "loss" else "未確定")
    delta = point_delta(record) if record.get("status") == "final" else 0.0
    recent_rows.append(
        f"<div class='history-row'><span>{esc(str(record.get('date','-'))[-5:])}</span>"
        f"<b>{esc(record.get('team'))} vs {esc(record.get('opponent'))}</b>"
        f"<span>補正 {esc(record.get('handicap'), '0')}</span><span>{delta:+.0f}</span>"
        f"<em class='{status_class}'>{status_text}</em></div>"
    )
recent_html = "".join(recent_rows) or "<div class='empty'>分析履歴はまだありません。</div>"

switch_text = switch_at.strftime("%m/%d %H:%M") if switch_at else "次カード待ち"
success_text = f"{success_rate:.1f}%" if success_rate is not None else "-"
best_model_name = {
    "historical_baseline": "過去勝率ベースライン",
    "logistic_rolling": "ロジスティック回帰",
    "gradient_rolling": "勾配ブースティング",
}.get(best_model.get("model"), best_model.get("model") or "-")
best_brier = f"{float(best_model.get('brier')):.4f}" if best_model.get("brier") is not None else "-"

page_html = f"""
<style>
{TEAM_BADGE_CSS}
html,body,[data-testid='stAppViewContainer']{{background:#080b0e!important;color:#f3f5f7}}[data-testid='stHeader'],[data-testid='stToolbar'],footer{{display:none!important}}.block-container{{max-width:1460px!important;padding:0 26px 34px!important}}*{{box-sizing:border-box}}.dash{{font-family:Inter,'Noto Sans JP',sans-serif;color:#f2f4f6}}.dash a{{text-decoration:none}}
.top{{height:74px;display:grid;grid-template-columns:290px 1fr 150px;align-items:center;border-bottom:1px solid #20252b;background:#07090b;margin-bottom:14px}}.brand{{display:flex;gap:11px;align-items:center;color:inherit}}.logo{{width:40px;height:40px;border:2px solid #efb82e;border-radius:50%;display:grid;place-items:center;color:#efb82e;font-size:17px}}.brand b{{display:block;color:#efb82e;font-size:17px}}.brand small{{font-size:8px;color:#9ca4ad}}.nav{{height:74px;display:flex;justify-content:center;gap:11px}}.nav a{{min-width:64px;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#d0d5da;font-size:8px;font-weight:800;gap:5px}}.nav i{{font-style:normal;font-size:15px}}.mode{{justify-self:end;width:140px;padding:9px;border:1px solid #c89616;border-radius:6px;text-align:center;color:#efb82e;font-size:9px;font-weight:900}}.mode small{{display:block;font-size:7px;color:#cbb56d;margin-top:2px}}
.hero{{min-height:126px;padding:20px 24px;border:1px solid #252b31;border-radius:8px;background:linear-gradient(90deg,#11161c,#0c1014);display:grid;grid-template-columns:1fr 360px;align-items:center;margin-bottom:12px}}.hero h1{{font-size:25px;margin:0 0 9px;color:#fff}}.hero p{{font-size:10px;color:#b1b8c0;margin:0;line-height:1.7}}.hero-side{{display:grid;grid-template-columns:1fr 130px;gap:12px;align-items:center}}.date{{font-size:11px;font-weight:800}}.updated{{font-size:8px;color:#89919b;margin-top:4px}}.refresh{{border:1px solid #434a52;border-radius:6px;padding:9px;color:#dfe4e8;text-align:center;font-size:8px}}
.alert{{margin-bottom:12px;padding:10px 12px;border:1px solid #3e4b57;background:#111923;border-radius:7px;color:#b9c7d4;font-size:9px}}.alert b{{color:#fff}}.alert.warn{{border-color:#6d5921;background:#241e0c;color:#dfc46b}}
.kpis{{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin-bottom:12px}}.kpi{{min-height:98px;border:1px solid #252b31;border-radius:8px;background:#12171d;padding:13px 14px;display:flex;flex-direction:column;justify-content:center}}.kpi label{{color:#b3bac2;font-size:8px}}.kpi strong{{font-size:23px;color:#fff;line-height:1.2;margin-top:4px}}.kpi strong.gold{{color:#efb82e}}.kpi small{{color:#87909a;font-size:7px;margin-top:3px}}
.grid{{display:grid;grid-template-columns:minmax(0,1.72fr) minmax(330px,.9fr);gap:10px;margin-bottom:10px;align-items:start}}.panel{{border:1px solid #252b31;border-radius:8px;background:#0f1419;padding:11px 12px}}.panel-title{{min-height:30px;display:flex;align-items:center;gap:7px;font-size:16px;font-weight:900;color:#fff;margin-bottom:5px}}.panel-title.gold{{color:#efb82e}}.panel-title a{{margin-left:auto;color:#9aa2ac;font-size:8px}}.table-wrap{{border:1px solid #20262c;border-radius:6px;overflow:hidden}}table{{width:100%;border-collapse:collapse}}th{{background:#151b21;color:#929aa4;text-align:left;font-size:8px;padding:8px 9px}}td{{border-top:1px solid #20262c;padding:9px;font-size:10px;color:#e3e7ea;white-space:nowrap}}.matchup{{display:flex;align-items:center;gap:8px}}.vs{{color:#8a929c}}.status{{padding:4px 7px;border-radius:999px;background:#252b31;font-size:8px;font-weight:900}}.status.live{{background:#47171b;color:#ff9ba0}}.status.final{{background:#173721;color:#8be8ac}}.full{{display:block;margin-top:8px;border:1px solid #252b31;border-radius:5px;text-align:center;padding:8px;color:#d7dce1;font-size:9px}}
.top-card{{border-color:#efb82e;background:linear-gradient(#1a160c,#0e1114)}}.rank-row{{display:grid;grid-template-columns:38px 1fr 74px;gap:9px;align-items:center;background:#0b0e11;border:1px solid #252a30;border-radius:5px;padding:9px 10px;margin-bottom:7px}}.rank-no{{font-size:26px;color:#efb82e;font-weight:950;text-align:center}}.rank-team{{display:flex;align-items:center;gap:9px}}.rank-row b{{font-size:11px}}.rank-row small{{display:block;color:#8c949e;font-size:8px;margin-top:3px}}.rank-prob{{text-align:right;font-size:16px;font-weight:900}}.rank-prob small{{text-align:right;font-size:7px}}
.menu-grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:9px}}.menu-card{{min-height:155px;border:1px solid #252b31;border-radius:6px;background:#12171d;padding:12px 10px;text-align:center;display:flex;flex-direction:column;align-items:center}}.menu-card b{{font-size:10px}}.menu-icon{{font-size:28px;color:#efb82e;margin:12px 0 7px}}.menu-card p{{font-size:8px;line-height:1.5;color:#afb6be;margin:0}}.menu-link{{margin-top:auto;width:100%;border:1px solid #765912;border-radius:4px;padding:7px;color:#efb82e;font-size:8px;font-weight:900}}
.history{{display:flex;flex-direction:column;gap:4px}}.history-row{{min-height:34px;display:grid;grid-template-columns:55px 1fr 64px 42px 45px;gap:5px;align-items:center;border-bottom:1px solid #20262c;padding:5px 7px;font-size:8px}}.history-row em{{font-style:normal;justify-self:end;padding:4px 6px;border-radius:3px;font-weight:900}}.ok{{background:#103b21;color:#7de6a1}}.ng{{background:#42181c;color:#ff9499}}.wait{{background:#373216;color:#e5d174}}.empty{{font-size:9px;color:#929aa4;padding:12px}}.foot{{border-top:1px solid #20262c;margin-top:10px;padding-top:10px;display:flex;justify-content:space-between;color:#7f8791;font-size:7px}}
@media(max-width:1150px){{.top{{grid-template-columns:230px 1fr}}.mode{{display:none}}.nav{{gap:4px}}.kpis{{grid-template-columns:repeat(3,1fr)}}.grid{{grid-template-columns:1fr}}.menu-grid{{grid-template-columns:repeat(3,1fr)}}}}@media(max-width:720px){{.block-container{{padding:0 10px 30px!important}}.top{{height:auto;grid-template-columns:1fr}}.nav{{overflow-x:auto;justify-content:flex-start;height:60px}}.hero{{grid-template-columns:1fr}}.hero-side{{margin-top:12px}}.kpis{{grid-template-columns:1fr 1fr}}.menu-grid{{grid-template-columns:1fr}}.table-wrap{{overflow-x:auto}}}}
</style>
<div class="dash">
<div class="top"><a class="brand" href="/"><div class="logo">⚾</div><div><b>AI BASEBALL STUDIO</b><small>AI野球分析・シミュレーション研究所</small></div></a><nav class="nav"><a href="/"><i>⌂</i>DASHBOARD</a><a href="/試合"><i>▦</i>GAMES</a><a href="/本日のAI予想"><i>▣</i>AI</a><a href="/BET入力"><i>↗</i>SIMULATION</a><a href="/収支マップ"><i>◉</i>ANALYSIS</a><a href="/予想結果"><i>◷</i>HISTORY</a><a href="/レポート"><i>▤</i>REPORT</a><a href="/設定"><i>⚙</i>SETTINGS</a></nav><div class="mode">リサーチモード<small>研究・仮説検証用</small></div></div>
<div class="hero"><div><h1>野球AI分析 × モデル検証ダッシュボード</h1><p>試合カード、AI予測、感度分析、検証履歴、長期バックテストを一つの画面から確認できます。</p></div><div class="hero-side"><div><div class="date">▣ {now.strftime('%Y年%m月%d日')} ({weekday})</div><div class="updated">表示カード: {esc(display_date)} / 次回切替: {esc(switch_text)}</div></div><a class="refresh" href="/">⟳ 更新</a></div></div>
<div class="alert {'warn' if schedule_health['level'] == 'stale' or pred_health['level'] == 'stale' else ''}">データ状態：試合 <b>{esc(schedule_health['label'])}</b>（{esc(schedule_health['date'])}） / AI予測 <b>{esc(pred_health['label'])}</b>（{esc(pred_health['date'])}）。表示は次の試合日の最初の開始時刻の<b>2時間前</b>に切り替わります。</div>
<div class="kpis"><div class="kpi"><label>表示試合数</label><strong>{len(display_games)}</strong><small>{esc(display_date)}</small></div><div class="kpi"><label>LIVE</label><strong>{live_count}</strong><small>試合中のみリアルタイム更新</small></div><div class="kpi"><label>AI評価数</label><strong>{len(prediction_games)}</strong><small>表示日と一致する予測のみ</small></div><div class="kpi"><label>分析シナリオ</label><strong>{len(records)}</strong><small>累計</small></div><div class="kpi"><label>仮説成立率</label><strong>{success_text}</strong><small>確定シナリオ</small></div><div class="kpi"><label>総評価スコア差</label><strong class="gold">{total_delta:+.0f}</strong><small>研究指標</small></div></div>
<div class="grid"><section class="panel"><div class="panel-title">⚾ 試合カード</div><div class="table-wrap"><table><thead><tr><th>開始</th><th>対戦</th><th>球場</th><th>スコア</th><th>状態</th><th>AI評価</th></tr></thead><tbody>{match_html}</tbody></table></div><a class="full" href="/試合">試合センターを開く ›</a></section><aside class="panel top-card"><div class="panel-title gold">♕ TOP AI評価</div>{top_html}<a class="full" href="/本日のAI予想">AIランキングを見る ›</a></aside></div>
<div class="grid"><section class="panel"><div class="panel-title">♜ 研究・分析メニュー</div><div class="menu-grid"><div class="menu-card"><b>得点補正シミュレーション</b><div class="menu-icon">☷</div><p>得点補正値による感度を検証</p><a class="menu-link" href="/BET入力">開始 ›</a></div><div class="menu-card"><b>感度分析結果</b><div class="menu-icon">▥</div><p>成立率と評価スコアを確認</p><a class="menu-link" href="/収支マップ">結果 ›</a></div><div class="menu-card"><b>予想検証履歴</b><div class="menu-icon">↶</div><p>事前予測と実績を照合</p><a class="menu-link" href="/予想結果">履歴 ›</a></div><div class="menu-card"><b>統計・モデルレポート</b><div class="menu-icon">▤</div><p>{esc(best_model_name)} / Brier {esc(best_brier)}</p><a class="menu-link" href="/レポート">レポート ›</a></div><div class="menu-card"><b>システム状態</b><div class="menu-icon">⚙</div><p>認証・データ鮮度・切替状態</p><a class="menu-link" href="/設定">確認 ›</a></div></div></section><aside class="panel"><div class="panel-title">↗ 最近の感度分析結果<a href="/収支マップ">すべて見る</a></div><div class="history">{recent_html}</div><a class="full" href="/収支マップ">分析結果を開く ›</a></aside></div>
<div class="foot"><span>ⓘ 研究・仮説検証を目的とした分析環境です。</span><span>© 2026 AI BASEBALL STUDIO.</span></div></div>
"""

st.html(page_html)
