from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import html
import json

import streamlit as st

from bet_analytics import calculate_hit_rate, point_delta

JST = ZoneInfo("Asia/Tokyo")
DATA_DIRS = [Path("/app/data"), Path(__file__).resolve().parent / "data"]

TEAM_MARKS = [
    (("読売ジャイアンツ", "巨人", "Yomiuri Giants"), "G", "#f36c21", "#111111"),
    (("阪神タイガース", "阪神", "Hanshin Tigers"), "T", "#f4c300", "#111111"),
    (("横浜DeNAベイスターズ", "DeNA", "横浜", "BayStars"), "DB", "#0876bd", "#ffffff"),
    (("広島東洋カープ", "広島", "カープ", "Carp"), "C", "#d71920", "#ffffff"),
    (("中日ドラゴンズ", "中日", "Dragons"), "D", "#1655a5", "#ffffff"),
    (("東京ヤクルトスワローズ", "ヤクルト", "Swallows"), "S", "#0a3765", "#ffffff"),
    (("福岡ソフトバンクホークス", "ソフトバンク", "ソフト", "ホークス", "Hawks"), "H", "#f3d321", "#111111"),
    (("北海道日本ハムファイターズ", "日本ハム", "日ハム", "Fighters"), "F", "#0b3158", "#ffffff"),
    (("千葉ロッテマリーンズ", "ロッテ", "Marines"), "M", "#111111", "#ffffff"),
    (("東北楽天ゴールデンイーグルス", "楽天", "Eagles"), "E", "#8c1531", "#ffffff"),
    (("オリックス・バファローズ", "オリックス", "Buffaloes"), "B", "#172a53", "#d7b65d"),
    (("埼玉西武ライオンズ", "西武", "Lions"), "L", "#1d4f91", "#ffffff"),
]

st.set_page_config(
    page_title="AI BASEBALL STUDIO | RESEARCH",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def load_json(name, fallback):
    for directory in DATA_DIRS:
        path = directory / name
        try:
            if path.is_file() and path.stat().st_size:
                value = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(value, dict) and "games" in value and not value.get("games"):
                    continue
                return value
        except Exception:
            continue
    return fallback


def esc(value, fallback="-"):
    if value in (None, ""):
        value = fallback
    return html.escape(str(value))


def team_badge(team, *, show_name=True, size="md"):
    name = str(team or "-")
    mark, bg, fg = "⚾", "#30363d", "#ffffff"
    for aliases, candidate_mark, candidate_bg, candidate_fg in TEAM_MARKS:
        if any(alias.lower() in name.lower() for alias in aliases):
            mark, bg, fg = candidate_mark, candidate_bg, candidate_fg
            break
    badge = (
        f"<span class='team-badge team-badge-{size}' "
        f"style='--team-bg:{bg};--team-fg:{fg}'>{esc(mark)}</span>"
    )
    if not show_name:
        return badge
    return f"<span class='team-name'>{badge}<b>{esc(name)}</b></span>"


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
    }


def load_analysis_records():
    current = load_json("simulation_records.json", [])
    legacy = load_json("bet_records.json", [])
    current = current if isinstance(current, list) else []
    legacy = legacy if isinstance(legacy, list) else []
    merged, seen = [], set()
    for record in [legacy_to_analysis(r) for r in legacy] + current:
        key = tuple(str(record.get(k, "")) for k in ("date", "time", "team", "opponent", "handicap"))
        if key not in seen:
            seen.add(key)
            merged.append(record)
    return merged


predictions = load_json("today_ai_predictions.json", {"games": []})
npb_today = load_json("npb_today.json", {"games": []})
analysis_records = load_analysis_records()
prediction_games = predictions.get("games", []) if isinstance(predictions, dict) else []
today_games = npb_today.get("games", []) if isinstance(npb_today, dict) else []
settled = [r for r in analysis_records if r.get("status") == "final"]
_, _, success_rate = calculate_hit_rate(settled)
total_delta = sum(point_delta(r) for r in settled)
ranked = sorted(prediction_games, key=lambda g: g.get("rank", 999))
now = datetime.now(JST)

prediction_lookup = {(str(g.get("home", "")), str(g.get("away", ""))): g for g in prediction_games}

match_rows = []
for game in sorted(today_games, key=lambda g: str(g.get("time", "99:99"))):
    home = str(game.get("home", "-"))
    away = str(game.get("away", "-"))
    pred = prediction_lookup.get((home, away), {})
    pick = str(pred.get("pick", "-"))
    try:
        p = float(pred.get("win_probability"))
    except (TypeError, ValueError):
        p = None
    if p is None:
        hp = ap = "-"
        hc = ac = ""
    elif pick == home:
        hp, ap, hc, ac = f"{p:.1f}%", f"{100-p:.1f}%", "hot", ""
    elif pick == away:
        hp, ap, hc, ac = f"{100-p:.1f}%", f"{p:.1f}%", "", "hot"
    else:
        hp = ap = "-"
        hc = ac = ""
    match_rows.append(
        f"<tr><td>{esc(game.get('time'))}</td>"
        f"<td><div class='matchup'>{team_badge(home)}<span class='vs'>vs</span>{team_badge(away)}</div></td>"
        f"<td>{esc(game.get('venue'))}</td><td class='{hc}'>{hp}</td><td class='{ac}'>{ap}</td>"
        f"<td><span class='pick'>{team_badge(pick, show_name=False, size='xs')}{esc(pick, '分析中')} 有利</span></td></tr>"
    )
match_html = "".join(match_rows) or "<tr><td colspan='6' class='empty'>本日の試合データはありません。</td></tr>"

top_rows = []
for i, game in enumerate(ranked[:3], 1):
    try:
        prob = f"{float(game.get('win_probability')):.1f}%"
    except (TypeError, ValueError):
        prob = "-"
    pick_team = game.get("pick")
    top_rows.append(
        f"<div class='rank-row'><div class='rank-no'>{i}</div>"
        f"<div class='rank-team'>{team_badge(pick_team, show_name=False, size='lg')}<div><b>{esc(pick_team)}</b>"
        f"<small>{esc(game.get('home'))} vs {esc(game.get('away'))}</small></div></div>"
        f"<div class='rank-prob'>{prob}<small>AI勝率</small></div></div>"
    )
top_html = "".join(top_rows) or "<div class='empty'>AI予測データ準備中</div>"

recent_rows = []
for record in sorted(analysis_records, key=lambda r: (str(r.get("date", "")), str(r.get("time", ""))), reverse=True)[:5]:
    result = record.get("result")
    status_class = "ok" if result == "win" else ("ng" if result == "loss" else "wait")
    status_text = "成立" if result == "win" else ("不成立" if result == "loss" else "未確定")
    delta = point_delta(record) if record.get("status") == "final" else 0.0
    recent_rows.append(
        f"<div class='history-row'><span>{esc(str(record.get('date','-'))[-5:])} {esc(record.get('time'))}</span>"
        f"<b class='history-match'>{team_badge(record.get('team'), show_name=False, size='xs')}{esc(record.get('team'))} vs {esc(record.get('opponent'))}</b>"
        f"<span>補正 {esc(record.get('handicap'), '0')}</span><span>{delta:+.1f}</span>"
        f"<em class='{status_class}'>{status_text}</em></div>"
    )
recent_html = "".join(recent_rows) or "<div class='empty'>分析履歴はまだありません。</div>"
success_text = f"{success_rate:.1f}%" if success_rate is not None else "-"
weekday = "月火水木金土日"[now.weekday()]

page_html = f"""
<style>
html,body,[data-testid='stAppViewContainer']{{background:#080b0e!important;color:#f3f5f7}}
[data-testid='stHeader'],[data-testid='stToolbar'],footer{{display:none!important}}
.block-container{{max-width:1460px!important;padding:0 26px 34px!important}}
*{{box-sizing:border-box}}.dash{{font-family:Inter,'Noto Sans JP',sans-serif;color:#f2f4f6}}.dash a{{text-decoration:none}}
.top{{height:74px;display:grid;grid-template-columns:290px 1fr 150px;align-items:center;border-bottom:1px solid #20252b;background:#07090b;margin-bottom:14px}}
.brand{{display:flex;gap:11px;align-items:center}}.logo{{width:40px;height:40px;border:2px solid #efb82e;border-radius:50%;display:grid;place-items:center;color:#efb82e;font-size:17px}}.brand b{{display:block;color:#efb82e;font-size:17px}}.brand small{{font-size:8px;color:#9ca4ad}}
.nav{{height:74px;display:flex;justify-content:center;gap:14px}}.nav a{{position:relative;min-width:66px;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#d0d5da;font-size:9px;font-weight:800;gap:5px}}.nav i{{font-style:normal;font-size:15px}}.nav a:first-child:after{{content:'';position:absolute;bottom:0;left:5px;right:5px;height:3px;background:#efb82e}}
.mode{{justify-self:end;width:140px;padding:9px;border:1px solid #c89616;border-radius:6px;text-align:center;color:#efb82e;font-size:9px;font-weight:900}}.mode small{{display:block;font-size:7px;color:#cbb56d;margin-top:2px}}
.hero{{min-height:128px;padding:20px 24px;border:1px solid #252b31;border-radius:8px;background:linear-gradient(90deg,#11161c,#0c1014);display:grid;grid-template-columns:1fr 330px;align-items:center;margin-bottom:12px}}.hero h1{{font-size:25px;margin:0 0 9px;color:#fff}}.hero p{{font-size:10px;color:#b1b8c0;margin:0;line-height:1.7}}.hero-side{{display:grid;grid-template-columns:1fr 116px;gap:14px;align-items:center}}.date{{font-size:11px;font-weight:800}}.updated{{font-size:8px;color:#89919b;margin-top:4px}}.refresh{{border:1px solid #434a52;border-radius:6px;padding:9px;color:#dfe4e8;text-align:center;font-size:8px}}
.kpis{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:12px}}.kpi{{height:103px;border:1px solid #252b31;border-radius:8px;background:#12171d;padding:14px 16px;display:grid;grid-template-columns:38px 1fr;align-items:center;gap:10px}}.kpi-icon{{color:#efb82e;font-size:27px}}.kpi label{{display:block;color:#b3bac2;font-size:9px}}.kpi strong{{display:block;font-size:27px;color:#fff;line-height:1.1}}.kpi strong.gold{{color:#efb82e}}.kpi small{{color:#87909a;font-size:8px}}.kpi small.green{{color:#4dce7e}}
.grid{{display:grid;grid-template-columns:minmax(0,1.72fr) minmax(330px,.9fr);gap:10px;margin-bottom:10px;align-items:start}}.panel{{border:1px solid #252b31;border-radius:8px;background:#0f1419;padding:11px 12px}}.panel-title{{height:30px;display:flex;align-items:center;gap:7px;font-size:17px;font-weight:900;color:#fff;margin-bottom:5px}}.panel-title.gold{{color:#efb82e}}.panel-title a{{margin-left:auto;color:#9aa2ac;font-size:8px}}.top3{{margin-left:auto;background:#3b2e0c;padding:5px 9px;border-radius:5px;font-size:8px}}
.team-badge{{display:inline-flex;align-items:center;justify-content:center;flex:none;border-radius:50%;background:var(--team-bg);color:var(--team-fg);font-weight:950;letter-spacing:-.04em;border:1px solid rgba(255,255,255,.22);box-shadow:0 2px 8px rgba(0,0,0,.28)}}.team-badge-md{{width:28px;height:28px;font-size:10px}}.team-badge-lg{{width:34px;height:34px;font-size:12px}}.team-badge-xs{{width:18px;height:18px;font-size:7px;margin-right:5px}}.team-name{{display:inline-flex;align-items:center;gap:7px}}.matchup{{display:flex;align-items:center;gap:8px}}.matchup .vs{{margin:0 2px}}.rank-team{{display:flex;align-items:center;gap:9px;min-width:0}}.history-match{{display:flex;align-items:center}}
.table-wrap{{border:1px solid #20262c;border-radius:6px;overflow:hidden}}table{{width:100%;border-collapse:collapse}}th{{background:#151b21;color:#929aa4;text-align:left;font-size:8px;padding:8px 9px}}td{{border-top:1px solid #20262c;padding:9px;font-size:10px;color:#e3e7ea;white-space:nowrap}}td:nth-child(4),td:nth-child(5){{font-size:13px;font-weight:900}}td.hot{{color:#efb82e}}.vs{{margin:0 10px;color:#8a929c}}.pick{{display:inline-flex;align-items:center;background:#654b10;color:#ffe191;border-radius:4px;padding:4px 7px;font-size:8px;font-weight:900}}.full{{display:block;margin-top:8px;border:1px solid #252b31;border-radius:5px;text-align:center;padding:8px;color:#d7dce1;font-size:9px}}
.top-card{{border-color:#efb82e;background:linear-gradient(#1a160c,#0e1114);box-shadow:0 0 20px #efb82e18}}.rank-row{{display:grid;grid-template-columns:38px 1fr 74px;gap:9px;align-items:center;background:#0b0e11;border:1px solid #252a30;border-radius:5px;padding:9px 10px;margin-bottom:7px}}.rank-no{{font-size:26px;color:#efb82e;font-weight:950;text-align:center}}.rank-row b{{font-size:11px}}.rank-row small{{display:block;color:#8c949e;font-size:8px;margin-top:3px}}.rank-prob{{text-align:right;font-size:16px;font-weight:900}}.rank-prob small{{text-align:right;font-size:7px}}
.menu-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:9px}}.menu-card{{min-height:176px;border:1px solid #252b31;border-radius:6px;background:#12171d;padding:13px 11px;text-align:center;display:flex;flex-direction:column;align-items:center}}.menu-card b{{font-size:11px}}.menu-card small{{font-size:8px;color:#9aa2ab}}.menu-icon{{font-size:30px;color:#efb82e;margin:13px 0 8px}}.menu-card p{{font-size:8px;line-height:1.55;color:#afb6be;margin:0}}.menu-link{{margin-top:auto;width:100%;border:1px solid #765912;border-radius:4px;padding:7px;color:#efb82e;font-size:8px;font-weight:900}}
.history{{display:flex;flex-direction:column;gap:4px}}.history-row{{min-height:34px;display:grid;grid-template-columns:70px 1fr 66px 48px 45px;gap:5px;align-items:center;border-bottom:1px solid #20262c;padding:5px 7px;font-size:8px}}.history-row em{{font-style:normal;justify-self:end;padding:4px 6px;border-radius:3px;font-weight:900}}.ok{{background:#103b21;color:#7de6a1}}.ng{{background:#42181c;color:#ff9499}}.wait{{background:#373216;color:#e5d174}}.empty{{font-size:9px;color:#929aa4;padding:12px}}
.foot{{border-top:1px solid #20262c;margin-top:10px;padding-top:10px;display:flex;justify-content:space-between;color:#7f8791;font-size:7px}}
@media(max-width:1100px){{.top{{grid-template-columns:230px 1fr}}.mode{{display:none}}.nav{{gap:5px}}.kpis{{grid-template-columns:repeat(3,1fr)}}.grid{{grid-template-columns:1fr}}.menu-grid{{grid-template-columns:repeat(2,1fr)}}}}@media(max-width:720px){{.block-container{{padding:0 10px 30px!important}}.top{{height:auto;grid-template-columns:1fr}}.nav{{overflow-x:auto;justify-content:flex-start;height:60px}}.hero{{grid-template-columns:1fr}}.hero-side{{margin-top:12px}}.kpis{{grid-template-columns:1fr 1fr}}.menu-grid{{grid-template-columns:1fr}}.table-wrap{{overflow-x:auto}}.team-badge-md{{width:24px;height:24px;font-size:8px}}}}
</style>
<div class="dash">
<div class="top"><div class="brand"><div class="logo">⚾</div><div><b>AI BASEBALL STUDIO</b><small>AI野球分析・シミュレーション研究所</small></div></div><nav class="nav"><a href="/"><i>⌂</i>ダッシュボード</a><a href="/試合"><i>▦</i>試合一覧</a><a href="/本日のAI予想"><i>▣</i>AIランキング</a><a href="/BET入力"><i>↗</i>シミュレーション</a><a href="/収支マップ"><i>◉</i>分析結果</a><a href="/予想結果"><i>◷</i>履歴</a><a href="/"><i>⚙</i>設定</a></nav><div class="mode">リサーチモード<small>研究・仮説検証用</small></div></div>
<div class="hero"><div><h1>野球AI分析 × 得点補正シミュレーション</h1><p>AIによる勝率予測と得点補正による感度分析で、仮説の検証とモデル精度の確認をサポートします。</p></div><div class="hero-side"><div><div class="date">▣ {now.strftime('%Y年%m月%d日')} ({weekday})</div><div class="updated">データ更新：{now.strftime('%H:%M')}</div></div><a class="refresh" href="/">⟳ データを更新</a></div></div>
<div class="kpis"><div class="kpi"><div class="kpi-icon">▣</div><div><label>本日の試合数</label><strong>{len(today_games)}</strong><small>試合</small></div></div><div class="kpi"><div class="kpi-icon">♕</div><div><label>AI評価数</label><strong>{len(prediction_games)}</strong><small class="green">本日のAI予測</small></div></div><div class="kpi"><div class="kpi-icon">↗</div><div><label>分析シミュレーション</label><strong>{len(analysis_records)}</strong><small>累計シナリオ</small></div></div><div class="kpi"><div class="kpi-icon">◎</div><div><label>仮説成立率</label><strong>{success_text}</strong><small class="green">確定データ</small></div></div><div class="kpi"><div class="kpi-icon">◉</div><div><label>総評価スコア差</label><strong class="gold">{total_delta:+.1f}</strong><small>研究指標</small></div></div></div>
<div class="grid"><section class="panel"><div class="panel-title">⚾ 今日の試合カード</div><div class="table-wrap"><table><thead><tr><th>開始時間</th><th>対戦カード</th><th>球場</th><th>AI勝率（ホーム）</th><th>AI勝率（ビジター）</th><th>評価</th></tr></thead><tbody>{match_html}</tbody></table></div><a class="full" href="/試合">全試合を見る ›</a></section><aside class="panel top-card"><div class="panel-title gold">♕ 今日のTOP AI評価<span class="top3">TOP 3</span></div>{top_html}<a class="full" href="/本日のAI予想">AIランキングを見る ›</a></aside></div>
<div class="grid"><section class="panel"><div class="panel-title">♜ 研究・分析メニュー</div><div class="menu-grid"><div class="menu-card"><b>得点補正シミュレーション</b><small>（得点補正設定）</small><div class="menu-icon">☷</div><p>得点補正値を設定して<br>モデル結果の変化を分析</p><a class="menu-link" href="/BET入力">シミュレーション開始 ›</a></div><div class="menu-card"><b>感度分析結果</b><small>（シミュレーション実行）</small><div class="menu-icon">▥</div><p>得点補正による成立率変化と<br>評価スコアを確認</p><a class="menu-link" href="/収支マップ">結果を見る ›</a></div><div class="menu-card"><b>シミュレーション履歴</b><small>（過去の分析）</small><div class="menu-icon">↶</div><p>これまでの分析シナリオと<br>履歴を確認</p><a class="menu-link" href="/予想結果">履歴を見る ›</a></div><div class="menu-card"><b>統計・レポート</b><small>（分析レポート）</small><div class="menu-icon">▤</div><p>成立率・スコア推移など<br>各種レポートを確認</p><a class="menu-link" href="/本日のAI予想">レポートを見る ›</a></div></div></section><aside class="panel"><div class="panel-title">↗ 最近の感度分析結果<a href="/収支マップ">すべて見る</a></div><div class="history">{recent_html}</div><a class="full" href="/収支マップ">すべての履歴を見る ›</a></aside></div>
<div class="foot"><span>ⓘ 本システムは研究・仮説検証を目的とした分析環境です。</span><span>© 2026 AI BASEBALL STUDIO.</span></div>
</div>
"""

st.html(page_html)
