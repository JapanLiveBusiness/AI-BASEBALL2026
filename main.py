from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import html

import streamlit as st

JST = ZoneInfo("Asia/Tokyo")
DATA_DIR = Path(__file__).resolve().parent / "data"

st.set_page_config(
    page_title="AI BASEBALL STUDIO | GAME INTELLIGENCE",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def load_json(name, fallback):
    try:
        return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))
    except Exception:
        return fallback


predictions = load_json("today_ai_predictions.json", {"games": []})
npb_today = load_json("npb_today.json", {"games": []})
bet_summary = load_json("bet_summary.json", {})

prediction_games = sorted(predictions.get("games") or [], key=lambda x: x.get("rank", 999))
today_games = npb_today.get("games") or []
best = prediction_games[0] if prediction_games else {}
now = datetime.now(JST)

best_pick = html.escape(str(best.get("pick") or "データ同期中"))
best_match = html.escape(
    f"{best.get('home', '---')} vs {best.get('away', '---')}" if best else "本日の予測データを取得中"
)
best_prob = best.get("win_probability")
best_prob_label = f"{float(best_prob):.1f}%" if isinstance(best_prob, (int, float)) else "--"
updated_at = html.escape(str(predictions.get("updated_at") or npb_today.get("updated_at") or "--"))
weekly_profit = bet_summary.get("weekly_unsettled_profit")
profit_label = f"¥{int(weekly_profit):,}" if isinstance(weekly_profit, (int, float)) else "--"

teams = [
    ("H", "ソフトバンク"), ("F", "日本ハム"), ("E", "楽天"), ("L", "西武"),
    ("M", "ロッテ"), ("B", "オリックス"), ("G", "巨人"), ("T", "阪神"),
    ("DB", "DeNA"), ("C", "広島"), ("S", "ヤクルト"), ("D", "中日"),
]

rank_cards = []
for idx, game in enumerate(prediction_games[:3], start=1):
    rank_cards.append(
        f'''<div class="pick-row"><div class="rank">{idx}</div><div class="pick-main"><strong>{html.escape(str(game.get('pick') or '--'))}</strong><span>{html.escape(str(game.get('home') or '--'))} vs {html.escape(str(game.get('away') or '--'))}</span></div><div class="pick-prob">{game.get('win_probability', '--')}%</div></div>'''
    )
rank_html = "".join(rank_cards) or '<div class="empty">予測データを同期中です。</div>'
team_html = "".join(
    f'<div class="team"><b>{abbr}</b><span>{name}</span></div>' for abbr, name in teams
)

st.markdown(
    r'''
<style>
:root{--bg:#f2eee6;--paper:#fffdf9;--ink:#151515;--muted:#746e64;--line:#dcd4c7;--gold:#f3c400;--gold2:#b98a13;--dark:#171717;--dark2:#222;}
[data-testid="stHeader"],[data-testid="stToolbar"],footer,[data-testid="stSidebar"]{display:none!important}
[data-testid="stAppViewContainer"]{background:var(--bg)!important;color:var(--ink)!important}
.block-container{max-width:1480px!important;padding:0 24px 46px!important}

.topbar{height:66px;margin:0 -24px;background:#141414;color:#fff;display:flex;align-items:center;padding:0 26px;border-bottom:2px solid rgba(243,196,0,.4);gap:22px}
.brand{display:flex;align-items:center;gap:11px;min-width:260px}.logo{width:38px;height:38px;border-radius:10px;background:var(--gold);color:#111;display:grid;place-items:center;font-weight:1000;font-size:20px;font-style:italic}.brand-title{font-size:14px;font-weight:950;letter-spacing:.12em}.brand-sub{font-size:7px;color:#aaa;letter-spacing:.35em;margin-top:4px}.nav{display:flex;gap:22px;align-items:center;justify-content:center;flex:1}.nav span{font-size:10px;color:#bbb;white-space:nowrap}.nav .active{color:var(--gold);font-weight:900}.status{font-size:9px;border:1px solid #444;border-radius:999px;padding:7px 10px;color:#ddd}

.shell{padding-top:18px}.hero-grid{display:grid;grid-template-columns:7fr 5fr;gap:14px}.hero{min-height:214px;border-radius:18px;background:radial-gradient(circle at 82% 20%,rgba(194,143,24,.48),transparent 36%),linear-gradient(135deg,#111 0%,#18140d 55%,#382a0c 100%);color:#fff;padding:28px 30px;position:relative;overflow:hidden}.hero:after{content:"";position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,.022) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.022) 1px,transparent 1px);background-size:34px 34px}.eyebrow{position:relative;z-index:1;font-size:9px;letter-spacing:.27em;color:#f4cf52;font-weight:900}.hero h1{position:relative;z-index:1;font-size:44px!important;line-height:1!important;margin:10px 0 8px!important;color:#fff!important;font-style:italic;letter-spacing:-.04em}.hero h1 em{color:var(--gold);font-style:normal}.hero p{position:relative;z-index:1;font-size:12px;color:#cfcac0;line-height:1.65;max-width:640px}.chips{position:relative;z-index:1;display:flex;gap:7px;flex-wrap:wrap;margin-top:18px}.chip{font-size:9px;border:1px solid rgba(255,255,255,.24);border-radius:999px;padding:6px 9px;background:rgba(0,0,0,.2)}.chip.hot{background:var(--gold);border-color:var(--gold);color:#111;font-weight:900}

.snapshot{display:grid;grid-template-columns:1fr 1fr;gap:10px}.metric-card{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:17px;min-height:102px}.metric-card.dark{background:var(--dark);border-color:#282828;color:#fff}.label{font-size:8px;letter-spacing:.2em;color:var(--gold2);font-weight:950}.metric-card.dark .label{color:#f4ce46}.value{font-size:29px;font-weight:950;margin:9px 0 2px;line-height:1}.metric-card.dark .value{color:#fff}.desc{font-size:10px;color:var(--muted);line-height:1.5}.metric-card.dark .desc{color:#aaa}

.main-grid{display:grid;grid-template-columns:7fr 5fr;gap:14px;margin-top:14px}.panel{background:rgba(255,255,255,.54);border:1px solid var(--line);border-radius:16px;padding:14px}.panel-title{display:flex;justify-content:space-between;align-items:end;margin:2px 2px 10px}.panel-title h2{font-size:21px!important;margin:0!important}.panel-title small{font-size:9px;color:var(--muted)}
.pick-row{display:grid;grid-template-columns:42px 1fr 72px;align-items:center;gap:11px;background:var(--paper);border:1px solid var(--line);border-radius:11px;padding:12px 13px;margin-bottom:7px}.rank{width:32px;height:32px;border-radius:50%;display:grid;place-items:center;background:#181818;color:var(--gold);font-weight:950}.pick-main{display:flex;flex-direction:column}.pick-main strong{font-size:16px}.pick-main span{font-size:9px;color:var(--muted);margin-top:3px}.pick-prob{text-align:right;font-size:18px;font-weight:950}.empty{background:var(--paper);border:1px dashed var(--line);border-radius:11px;padding:20px;color:var(--muted);font-size:11px}

.action-grid{display:grid;grid-template-columns:1fr 1fr;gap:9px}.action{min-height:114px;background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:15px}.action.primary{background:#181818;color:#fff;border-color:#282828}.action b{display:block;font-size:15px;margin:8px 0 5px}.action p{font-size:9px;line-height:1.55;color:var(--muted);margin:0}.action.primary p{color:#aaa}.action .arrow{font-size:19px;color:var(--gold);font-weight:900}

.teams-wrap{margin-top:14px}.teams-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}.teams-head b{font-size:11px}.teams-head span{font-size:9px;color:var(--muted)}.teams{display:grid;grid-template-columns:repeat(12,1fr);gap:6px}.team{background:var(--paper);border:1px solid var(--line);border-radius:9px;min-height:64px;padding:7px 4px;text-align:center;display:flex;flex-direction:column;justify-content:center}.team b{width:29px;height:29px;border-radius:50%;background:#1a1a1a;color:var(--gold);display:grid;place-items:center;margin:0 auto 4px;font-size:9px}.team span{font-size:7px;font-weight:800;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}

.footer-grid{display:grid;grid-template-columns:8fr 4fr;gap:14px;margin-top:14px}.system{background:#181818;border-radius:14px;color:#fff;padding:18px 20px;display:flex;justify-content:space-between;align-items:center}.system strong{font-size:17px}.system p{font-size:9px;color:#aaa;margin:4px 0 0}.live{color:var(--gold);font-size:10px;border:1px solid #444;border-radius:999px;padding:9px 12px;font-weight:900}.domain-card{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:16px}.domain-card strong{font-size:12px}.domain-card div{font-size:9px;color:var(--muted);margin-top:6px;overflow-wrap:anywhere}

div[data-testid="stPageLink"] a{background:var(--paper)!important;color:var(--ink)!important;border:1px solid var(--line)!important;border-radius:999px!important;font-weight:850!important;padding:9px 13px!important}div[data-testid="stPageLink"] a:hover{border-color:var(--gold)!important}
.links{margin-top:16px}

@media(max-width:1100px){.nav{display:none}.brand{flex:1}.hero-grid,.main-grid,.footer-grid{grid-template-columns:1fr}.teams{grid-template-columns:repeat(6,1fr)}}
@media(max-width:700px){.block-container{padding:0 10px 34px!important}.topbar{margin:0 -10px;padding:0 12px;height:60px}.status{display:none}.shell{padding-top:10px}.hero{min-height:194px;padding:22px 18px}.hero h1{font-size:34px!important}.snapshot{grid-template-columns:1fr 1fr}.metric-card{min-height:92px;padding:14px}.value{font-size:24px}.main-grid{gap:10px}.action-grid{grid-template-columns:1fr}.teams{grid-template-columns:repeat(4,1fr)}.system{align-items:flex-start;gap:12px}.live{font-size:8px}}
</style>
''',
    unsafe_allow_html=True,
)

st.markdown(
    f'''
<div class="topbar">
  <div class="brand"><div class="logo">M</div><div><div class="brand-title">AI BASEBALL STUDIO</div><div class="brand-sub">GAME INTELLIGENCE</div></div></div>
  <div class="nav"><span class="active">HOME</span><span>GAMES</span><span>AI PREDICTION</span><span>RESULTS</span><span>BET</span><span>PERFORMANCE</span></div>
  <div class="status">JST {now.strftime('%H:%M')} · LIVE</div>
</div>
<div class="shell">
  <div class="hero-grid">
    <section class="hero">
      <div class="eyebrow">AI BASEBALL STUDIO / NPB 2026</div>
      <h1>GAME <em>INTELLIGENCE</em></h1>
      <p>試合、AI予測、ハンデ、BET、収支を一つの画面に集約。重要な判断材料を先に、詳細分析をその次に配置するダッシュボードへ再設計しました。</p>
      <div class="chips"><span class="chip hot">PRODUCTION</span><span class="chip">UPDATE {now.strftime('%H:%M:%S')}</span><span class="chip">DATA {updated_at}</span></div>
    </section>
    <section class="snapshot">
      <div class="metric-card dark"><div class="label">TOP AI PICK</div><div class="value">{best_pick}</div><div class="desc">{best_match}</div></div>
      <div class="metric-card"><div class="label">WIN PROBABILITY</div><div class="value">{best_prob_label}</div><div class="desc">本日の最高評価</div></div>
      <div class="metric-card"><div class="label">TODAY GAMES</div><div class="value">{len(today_games)}</div><div class="desc">NPB 対象試合</div></div>
      <div class="metric-card"><div class="label">WEEKLY P/L</div><div class="value">{profit_label}</div><div class="desc">BET集計</div></div>
    </section>
  </div>

  <div class="main-grid">
    <section class="panel">
      <div class="panel-title"><h2>今日のAIランキング</h2><small>TOP 3 / CONFIDENCE</small></div>
      {rank_html}
    </section>
    <section class="panel">
      <div class="panel-title"><h2>クイック操作</h2><small>WORKSPACE</small></div>
      <div class="action-grid">
        <div class="action primary"><span class="arrow">↗</span><b>AI予測</b><p>勝率・予測スコア・信頼度を確認</p></div>
        <div class="action"><span class="arrow">＋</span><b>BET入力</b><p>当日のBETとハンデを登録</p></div>
        <div class="action"><span class="arrow">⌁</span><b>収支マップ</b><p>的中率・ROI・累積収支を確認</p></div>
        <div class="action"><span class="arrow">◎</span><b>AI詳細</b><p>詳細分析と試合データを確認</p></div>
      </div>
    </section>
  </div>

  <section class="panel teams-wrap">
    <div class="teams-head"><b>12球団クイックビュー</b><span>NPB TEAMS</span></div>
    <div class="teams">{team_html}</div>
  </section>

  <div class="footer-grid">
    <section class="system"><div><strong>AI prediction engine</strong><p>先発・直近成績・対戦相性・球場・ハンデ・BET結果を継続同期</p></div><div class="live">● MONITORING</div></section>
    <section class="domain-card"><strong>Production</strong><div>ai-baseball-studio.f-polaris.jp</div></section>
  </div>
</div>
''',
    unsafe_allow_html=True,
)

st.markdown('<div class="links"></div>', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.page_link("pages/本日のAI予想.py", label="AI予測を開く", icon="🤖", use_container_width=True)
with c2:
    st.page_link("pages/BET入力.py", label="BET入力を開く", icon="✍️", use_container_width=True)
with c3:
    st.page_link("pages/収支マップ.py", label="収支マップ", icon="📈", use_container_width=True)
with c4:
    st.page_link("pages/AI詳細.py", label="AI詳細", icon="⚾", use_container_width=True)
