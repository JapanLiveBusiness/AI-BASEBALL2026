from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import html
import json

import streamlit as st

from bet_analytics import calculate_hit_rate, point_delta
from studio_theme import apply_studio_theme

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

st.markdown(
    r'''
<style>
.reference-dashboard{width:100%;max-width:1400px;margin:0 auto;color:#f3f5f7}
.reference-dashboard a{text-decoration:none}
.ref-topbar{height:74px;margin:0 -2px 14px;display:grid;grid-template-columns:290px 1fr 150px;align-items:center;border-bottom:1px solid rgba(255,255,255,.08);background:#07090b}
.ref-brand{display:flex;align-items:center;gap:11px;padding-left:4px}.ref-logo{width:38px;height:38px;border:2px solid #f0b82f;border-radius:50%;display:grid;place-items:center;color:#f0b82f;font-size:17px}.ref-brand-title{color:#f0b82f;font-size:17px;font-weight:950;letter-spacing:.02em}.ref-brand-sub{font-size:8px;color:#aab0b8;margin-top:2px}
.ref-nav{height:74px;display:flex;justify-content:center;align-items:stretch;gap:18px}.ref-nav a{position:relative;min-width:62px;color:#c7ccd2;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:9px;font-weight:850;gap:4px}.ref-nav a .ico{font-size:15px;color:#e7eaee}.ref-nav a:first-child{color:#fff}.ref-nav a:first-child:after{content:"";position:absolute;height:3px;background:#f0b82f;left:4px;right:4px;bottom:0;border-radius:3px 3px 0 0}.ref-mode{justify-self:end;width:140px;border:1px solid rgba(240,184,47,.65);border-radius:6px;text-align:center;padding:9px 8px;color:#f0b82f;font-size:10px;font-weight:900;line-height:1.35}.ref-mode small{display:block;color:#d2b865;font-size:7px;margin-top:2px}
.ref-hero{min-height:128px;border:1px solid rgba(255,255,255,.10);border-radius:8px;background:linear-gradient(90deg,#11161c 0%,#0e1217 72%,#0b0e12 100%);display:grid;grid-template-columns:1fr 330px;align-items:center;padding:18px 24px;margin-bottom:12px;overflow:hidden;position:relative}.ref-hero:after{content:"";position:absolute;inset:0;background:radial-gradient(ellipse at 28% -20%,rgba(255,255,255,.06),transparent 38%);pointer-events:none}.ref-hero-copy{position:relative;z-index:1}.ref-hero-title{font-size:26px;font-weight:950;color:#fff;letter-spacing:.01em;margin-bottom:8px}.ref-hero-desc{font-size:11px;color:#b5bbc4;line-height:1.65;max-width:740px}.ref-hero-side{position:relative;z-index:1;display:grid;grid-template-columns:1fr 116px;align-items:center;gap:16px}.ref-date{font-size:12px;font-weight:850;color:#eceff2}.ref-updated{font-size:8px;color:#9098a2;margin-top:4px}.ref-refresh{border:1px solid rgba(255,255,255,.26);border-radius:6px;color:#e8ebee;padding:9px 10px;text-align:center;font-size:9px;font-weight:850;background:rgba(255,255,255,.02)}
.ref-kpis{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:12px}.ref-kpi{height:103px;border:1px solid rgba(255,255,255,.09);border-radius:8px;background:linear-gradient(180deg,#151a20,#11161b);padding:14px 16px;display:grid;grid-template-columns:38px 1fr;align-items:center;gap:10px}.ref-kpi-icon{font-size:27px;color:#f0b82f}.ref-kpi-label{font-size:9px;color:#bcc2ca;margin-bottom:3px}.ref-kpi-value{font-size:27px;color:#fff;font-weight:950;line-height:1}.ref-kpi-value.gold{color:#f0b82f}.ref-kpi-note{font-size:8px;color:#8e96a1;margin-top:6px}.ref-kpi-note.up{color:#4bd07f}
.ref-main-grid,.ref-bottom-grid{display:grid;grid-template-columns:minmax(0,1.72fr) minmax(330px,.90fr);gap:10px;align-items:start}.ref-main-grid{margin-bottom:10px}.ref-panel{border:1px solid rgba(255,255,255,.09);border-radius:8px;background:#101419;padding:11px 12px}.ref-panel-title{height:30px;display:flex;align-items:center;gap:8px;font-size:17px;color:#fff;font-weight:950;margin-bottom:5px}.ref-panel-title .gold{color:#f0b82f}.ref-panel-title .right-link{margin-left:auto;color:#9da5af;font-size:8px;font-weight:750}.ref-panel-title .top3{margin-left:auto;background:#3b2e0d;color:#f0b82f;padding:5px 9px;border-radius:5px;font-size:8px}
.ref-table-wrap{overflow:hidden;border:1px solid rgba(255,255,255,.06);border-radius:6px}.ref-table{width:100%;border-collapse:collapse}.ref-table th{background:#151b21;color:#959da7;text-align:left;font-size:8px;font-weight:850;padding:8px 9px}.ref-table td{border-top:1px solid rgba(255,255,255,.06);padding:9px;font-size:10px;color:#e7eaed;white-space:nowrap}.ref-table td:nth-child(4),.ref-table td:nth-child(5){font-size:13px;font-weight:900}.ref-table .goldprob{color:#f0b82f}.ref-team{font-weight:900;color:#fff}.ref-pick{display:inline-block;padding:4px 7px;border-radius:4px;background:#6d5111;color:#ffe49a;font-size:8px;font-weight:900}.ref-full-link{display:block;margin-top:8px;border:1px solid rgba(255,255,255,.10);border-radius:5px;color:#e6e9ed;text-align:center;padding:8px;font-size:9px}
.ref-top-card{border:1px solid #f0b82f;border-radius:8px;background:linear-gradient(180deg,#1b160a,#11120f);padding:11px 12px;box-shadow:0 0 22px rgba(240,184,47,.11)}.ref-ai-row{display:grid;grid-template-columns:38px 1fr 72px;align-items:center;gap:9px;background:#0c0f13;border:1px solid rgba(255,255,255,.08);border-radius:5px;padding:9px 10px;margin-bottom:7px}.ref-ai-rank{font-size:26px;color:#f0b82f;font-weight:950;text-align:center}.ref-ai-name{font-size:11px;color:#fff;font-weight:900}.ref-ai-match{font-size:8px;color:#8f97a1;margin-top:3px}.ref-ai-prob{text-align:right;font-size:16px;color:#fff;font-weight:950}.ref-ai-label{text-align:right;font-size:7px;color:#939ba5;margin-top:2px}
.ref-research-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:9px}.ref-research-card{min-height:176px;border:1px solid rgba(255,255,255,.08);border-radius:6px;background:linear-gradient(180deg,#151a20,#11161b);padding:14px 12px;display:flex;flex-direction:column;align-items:center;text-align:center}.ref-research-title{font-size:12px;color:#fff;font-weight:900}.ref-research-sub{font-size:8px;color:#a7aeb7;margin-top:2px}.ref-research-icon{font-size:31px;color:#f0b82f;margin:13px 0 7px}.ref-research-desc{font-size:9px;color:#b4bbc4;line-height:1.55;min-height:42px}.ref-research-link{margin-top:auto;width:100%;border:1px solid rgba(240,184,47,.42);border-radius:4px;color:#f0b82f;font-size:9px;font-weight:900;padding:7px 5px}
.ref-analysis-list{display:flex;flex-direction:column;gap:5px}.ref-analysis-row{min-height:34px;display:grid;grid-template-columns:70px 1fr 68px 52px 45px;align-items:center;gap:5px;background:#11161b;border-bottom:1px solid rgba(255,255,255,.05);padding:5px 7px;font-size:8px;color:#dfe3e7}.ref-chip{justify-self:end;padding:4px 6px;border-radius:3px;font-size:7px;font-weight:950}.ref-win{background:#103b21;color:#7be5a0}.ref-loss{background:#42181c;color:#ff9298}.ref-pending{background:#383316;color:#e5cf70}.ref-footer{margin-top:10px;border-top:1px solid rgba(255,255,255,.08);padding-top:10px;display:flex;justify-content:space-between;font-size:7px;color:#7f8791}
@media(max-width:1100px){.ref-topbar{grid-template-columns:230px 1fr}.ref-mode{display:none}.ref-nav{gap:8px}.ref-kpis{grid-template-columns:repeat(3,1fr)}.ref-main-grid,.ref-bottom-grid{grid-template-columns:1fr}.ref-research-grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:720px){.ref-topbar{grid-template-columns:1fr;height:auto;padding:8px 0}.ref-nav{overflow-x:auto;justify-content:flex-start;height:58px}.ref-brand{padding-left:0}.ref-hero{grid-template-columns:1fr;padding:16px}.ref-hero-side{margin-top:14px}.ref-kpis{grid-template-columns:1fr 1fr}.ref-research-grid{grid-template-columns:1fr}.ref-table-wrap{overflow-x:auto}.ref-analysis-row{grid-template-columns:1fr 1fr}.ref-analysis-row>:nth-child(n+3){display:none}}
</style>
''',
    unsafe_allow_html=True,
)


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
    }


def load_analysis_records():
    current = load_json("simulation_records.json", [])
    legacy = load_json("bet_records.json", [])
    if not isinstance(current, list):
        current = []
    if not isinstance(legacy, list):
        legacy = []
    merged, seen = [], set()
    for record in [legacy_to_analysis(r) for r in legacy] + current:
        key = (str(record.get("date", "")), str(record.get("time", "")), str(record.get("team", "")), str(record.get("opponent", "")), str(record.get("handicap", "")))
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

prediction_lookup = {(str(g.get("home", "")), str(g.get("away", ""))): g for g in prediction_games}

match_rows = []
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
        home_cls = away_cls = ""
    elif pick == home:
        home_prob, away_prob = f"{p:.1f}%", f"{100-p:.1f}%"
        home_cls, away_cls = "goldprob", ""
    elif pick == away:
        home_prob, away_prob = f"{100-p:.1f}%", f"{p:.1f}%"
        home_cls, away_cls = "", "goldprob"
    else:
        home_prob = away_prob = "-"
        home_cls = away_cls = ""
    match_rows.append(
        f"<tr><td>{esc(game.get('time'))}</td><td><span class='ref-team'>{esc(home)}</span>　vs　<span class='ref-team'>{esc(away)}</span></td><td>{esc(game.get('venue'))}</td><td class='{home_cls}'>{home_prob}</td><td class='{away_cls}'>{away_prob}</td><td><span class='ref-pick'>{esc(pick, '分析中')} 有利</span></td></tr>"
    )
match_html = "".join(match_rows) if match_rows else "<tr><td colspan='6'>本日の試合データはありません。</td></tr>"

top_rows = []
for idx, game in enumerate(ranked[:3], start=1):
    probability = game.get("win_probability")
    try:
        probability_text = f"{float(probability):.1f}%"
    except (TypeError, ValueError):
        probability_text = "-"
    top_rows.append(
        f"<div class='ref-ai-row'><div class='ref-ai-rank'>{idx}</div><div><div class='ref-ai-name'>{esc(game.get('pick'))}</div><div class='ref-ai-match'>{esc(game.get('home'))} vs {esc(game.get('away'))}</div></div><div><div class='ref-ai-prob'>{probability_text}</div><div class='ref-ai-label'>AI勝率</div></div></div>"
    )
top_html = "".join(top_rows) if top_rows else "<div style='font-size:9px;color:#929aa4;padding:10px'>AI予測データ準備中</div>"

recent = sorted(analysis_records, key=lambda r: (str(r.get("date", "")), str(r.get("time", ""))), reverse=True)[:5]
recent_rows = []
for record in recent:
    result = record.get("result")
    if result == "win":
        chip = "<span class='ref-chip ref-win'>成立</span>"
    elif result == "loss":
        chip = "<span class='ref-chip ref-loss'>不成立</span>"
    else:
        chip = "<span class='ref-chip ref-pending'>未確定</span>"
    delta = point_delta(record) if record.get("status") == "final" else 0.0
    date_short = str(record.get("date", "-"))[-5:]
    recent_rows.append(
        f"<div class='ref-analysis-row'><div>{esc(date_short)} {esc(record.get('time'))}</div><div>{esc(record.get('team'))} vs {esc(record.get('opponent'))}</div><div>補正 {esc(record.get('handicap'), '0')}</div><div>{delta:+.1f}</div><div>{chip}</div></div>"
    )
recent_html = "".join(recent_rows) if recent_rows else "<div style='font-size:9px;color:#929aa4;padding:10px'>分析履歴はまだありません。</div>"

success_text = f"{success_rate:.1f}%" if success_rate is not None else "-"

page_html = f'''
<div class="reference-dashboard">
  <div class="ref-topbar">
    <div class="ref-brand">
      <div class="ref-logo">⚾</div>
      <div><div class="ref-brand-title">AI BASEBALL STUDIO</div><div class="ref-brand-sub">AI野球分析・シミュレーション研究所</div></div>
    </div>
    <nav class="ref-nav">
      <a href="/" target="_self"><span class="ico">⌂</span><span>ダッシュボード</span></a>
      <a href="/試合" target="_self"><span class="ico">▦</span><span>試合一覧</span></a>
      <a href="/本日のAI予想" target="_self"><span class="ico">▣</span><span>AIランキング</span></a>
      <a href="/BET入力" target="_self"><span class="ico">↗</span><span>シミュレーション</span></a>
      <a href="/収支マップ" target="_self"><span class="ico">◉</span><span>分析結果</span></a>
      <a href="/予想結果" target="_self"><span class="ico">◷</span><span>履歴</span></a>
      <a href="/" target="_self"><span class="ico">⚙</span><span>設定</span></a>
    </nav>
    <div class="ref-mode">リサーチモード<small>研究・仮説検証用</small></div>
  </div>

  <div class="ref-hero">
    <div class="ref-hero-copy">
      <div class="ref-hero-title">野球AI分析 × 得点補正シミュレーション</div>
      <div class="ref-hero-desc">AIによる勝率予測と得点補正（ハンデ）による感度分析で、仮説の検証とモデル精度の確認をサポートします。</div>
    </div>
    <div class="ref-hero-side">
      <div><div class="ref-date">▣ {now.strftime('%Y年%m月%d日')} ({'月火水木金土日'[now.weekday()]})</div><div class="ref-updated">データ更新：{now.strftime('%H:%M')}</div></div>
      <a class="ref-refresh" href="/" target="_self">⟳ データを更新</a>
    </div>
  </div>

  <div class="ref-kpis">
    <div class="ref-kpi"><div class="ref-kpi-icon">▣</div><div><div class="ref-kpi-label">本日の試合数</div><div class="ref-kpi-value">{len(today_games)}</div><div class="ref-kpi-note">試合</div></div></div>
    <div class="ref-kpi"><div class="ref-kpi-icon">♕</div><div><div class="ref-kpi-label">AI評価数</div><div class="ref-kpi-value">{len(prediction_games)}</div><div class="ref-kpi-note up">本日のAI予測</div></div></div>
    <div class="ref-kpi"><div class="ref-kpi-icon">↗</div><div><div class="ref-kpi-label">分析シミュレーション</div><div class="ref-kpi-value">{len(analysis_records)}</div><div class="ref-kpi-note">累計シナリオ</div></div></div>
    <div class="ref-kpi"><div class="ref-kpi-icon">◎</div><div><div class="ref-kpi-label">仮説成立率</div><div class="ref-kpi-value">{success_text}</div><div class="ref-kpi-note up">確定データ</div></div></div>
    <div class="ref-kpi"><div class="ref-kpi-icon">◉</div><div><div class="ref-kpi-label">総評価スコア差</div><div class="ref-kpi-value gold">{total_delta:+.1f}</div><div class="ref-kpi-note">研究指標</div></div></div>
  </div>

  <div class="ref-main-grid">
    <section class="ref-panel">
      <div class="ref-panel-title">⚾ 今日の試合カード</div>
      <div class="ref-table-wrap"><table class="ref-table"><thead><tr><th>開始時間</th><th>対戦カード</th><th>球場</th><th>AI勝率（ホーム）</th><th>AI勝率（ビジター）</th><th>評価</th></tr></thead><tbody>{match_html}</tbody></table></div>
      <a class="ref-full-link" href="/試合" target="_self">全試合を見る　›</a>
    </section>

    <aside class="ref-top-card">
      <div class="ref-panel-title"><span class="gold">♕ 今日のTOP AI評価</span><span class="top3">TOP 3</span></div>
      {top_html}
      <a class="ref-full-link" href="/本日のAI予想" target="_self">AIランキングを見る　›</a>
    </aside>
  </div>

  <div class="ref-bottom-grid">
    <section class="ref-panel">
      <div class="ref-panel-title">♜ 研究・分析メニュー</div>
      <div class="ref-research-grid">
        <div class="ref-research-card"><div class="ref-research-title">得点補正シミュレーション</div><div class="ref-research-sub">（ハンデ設定）</div><div class="ref-research-icon">☷</div><div class="ref-research-desc">得点補正値を設定して<br>勝率の変化を分析</div><a class="ref-research-link" href="/BET入力" target="_self">シミュレーション開始　›</a></div>
        <div class="ref-research-card"><div class="ref-research-title">感度分析結果</div><div class="ref-research-sub">（シミュレーション実行）</div><div class="ref-research-icon">▥</div><div class="ref-research-desc">得点補正による成立率変化と<br>評価スコアを確認</div><a class="ref-research-link" href="/収支マップ" target="_self">結果を見る　›</a></div>
        <div class="ref-research-card"><div class="ref-research-title">シミュレーション履歴</div><div class="ref-research-sub">（過去の分析）</div><div class="ref-research-icon">↶</div><div class="ref-research-desc">これまでのシミュレーション<br>履歴を確認</div><a class="ref-research-link" href="/予想結果" target="_self">履歴を見る　›</a></div>
        <div class="ref-research-card"><div class="ref-research-title">統計・レポート</div><div class="ref-research-sub">（分析レポート）</div><div class="ref-research-icon">▤</div><div class="ref-research-desc">成立率・スコア推移など<br>各種レポートを確認</div><a class="ref-research-link" href="/本日のAI予想" target="_self">レポートを見る　›</a></div>
      </div>
    </section>

    <aside class="ref-panel">
      <div class="ref-panel-title">↗ 最近の感度分析結果<a class="right-link" href="/収支マップ" target="_self">すべて見る</a></div>
      <div class="ref-analysis-list">{recent_html}</div>
      <a class="ref-full-link" href="/収支マップ" target="_self">すべての履歴を見る　›</a>
    </aside>
  </div>

  <div class="ref-footer"><span>ⓘ 本システムは研究・仮説検証を目的としたシミュレーション環境です。</span><span>© 2026 AI BASEBALL STUDIO. All rights reserved.</span></div>
</div>
'''

# Streamlit's Markdown parser treats indented HTML after blank lines as code blocks.
# Collapse the generated markup before rendering so every panel stays real HTML.
page_html = "".join(line.strip() for line in page_html.splitlines())
st.markdown(page_html, unsafe_allow_html=True)
