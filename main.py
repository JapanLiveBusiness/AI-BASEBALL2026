from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import json

import streamlit as st

JST = ZoneInfo("Asia/Tokyo")
DATA_DIR = Path(__file__).resolve().parent / "data"

st.set_page_config(
    page_title="MY AI BASEBALL | GAME INTELLIGENCE",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def load_json(name, fallback):
    try:
        value = json.loads((DATA_DIR / name).read_text(encoding="utf-8"))
        return value
    except Exception:
        return fallback


predictions = load_json("today_ai_predictions.json", {"games": []})
npb_today = load_json("npb_today.json", {"games": []})
bet_summary = load_json("bet_summary.json", {})

prediction_games = predictions.get("games") or []
today_games = npb_today.get("games") or []
best = prediction_games[0] if prediction_games else {}

best_pick = best.get("pick") or "データ同期中"
best_prob = best.get("win_probability")
best_prob_label = f"{float(best_prob):.1f}%" if isinstance(best_prob, (int, float)) else "--"
best_match = (
    f"{best.get('home', '---')} vs {best.get('away', '---')}"
    if best else "本日の予測データを取得中"
)
updated_at = predictions.get("updated_at") or npb_today.get("updated_at") or "--"
weekly_profit = bet_summary.get("weekly_unsettled_profit")
profit_label = f"¥{int(weekly_profit):,}" if isinstance(weekly_profit, (int, float)) else "--"
now_jst = datetime.now(JST)

teams = [
    ("ソフトバンク", "H"), ("日本ハム", "F"), ("楽天", "E"), ("西武", "L"),
    ("ロッテ", "M"), ("オリックス", "B"), ("巨人", "G"), ("阪神", "T"),
    ("DeNA", "DB"), ("広島", "C"), ("ヤクルト", "S"), ("中日", "D"),
]

st.markdown(
    """
<style>
:root {
  --mab-black: #151516;
  --mab-black-2: #1c1c1e;
  --mab-gold: #f3c400;
  --mab-gold-deep: #ba8511;
  --mab-cream: #f3efe7;
  --mab-card: #fffdf9;
  --mab-line: #ded7cb;
  --mab-text: #141414;
  --mab-muted: #776f65;
}

[data-testid="stHeader"], [data-testid="stToolbar"], footer {display:none !important;}
[data-testid="stSidebar"] {display:none !important;}
[data-testid="stAppViewContainer"] {
  background: var(--mab-cream) !important;
  color: var(--mab-text) !important;
}
.block-container {
  max-width: 1440px !important;
  padding: 0 0 3rem 0 !important;
}

.mab-nav {
  min-height: 76px;
  background: var(--mab-black);
  color: white;
  display: flex;
  align-items: center;
  padding: 0 30px;
  gap: 28px;
  border-bottom: 1px solid #2a2a2c;
}
.mab-brand {display:flex; align-items:center; gap:12px; min-width:280px;}
.mab-logo {
  width: 40px; height: 40px; border-radius: 11px; background: var(--mab-gold);
  color: #111; display:flex; align-items:center; justify-content:center;
  font-weight: 1000; font-style: italic; font-size: 22px;
}
.mab-brand-title {font-weight:900; letter-spacing:.13em; font-size:15px;}
.mab-brand-sub {font-size:7px; letter-spacing:.42em; color:#b8b8b8; margin-top:4px;}
.mab-next {border:1px solid var(--mab-gold); color:var(--mab-gold); font-size:9px; padding:3px 6px;}
.mab-nav-items {display:flex; flex:1; justify-content:center; gap:30px; align-items:center;}
.mab-nav-item {font-size:10px; color:#ddd; text-align:center; line-height:1.6; white-space:nowrap;}
.mab-nav-item b {font-size:16px; display:block; color:#fff; font-weight:500;}
.mab-nav-item.active {color:var(--mab-gold); border-bottom:3px solid var(--mab-gold); padding-bottom:15px; margin-bottom:-18px;}
.mab-nav-actions {display:flex; gap:8px;}
.mab-square {border:1px solid #3b3b3d; border-radius:9px; padding:10px 12px; font-weight:800;}

.mab-hero {
  position: relative;
  overflow: hidden;
  min-height: 330px;
  padding: 42px 38px 34px;
  color: white;
  background:
    radial-gradient(circle at 80% 20%, rgba(204,151,29,.50), transparent 38%),
    linear-gradient(135deg, #111 0%, #17120a 46%, #3a2b0d 100%);
  border-bottom: 3px solid rgba(243,196,0,.35);
}
.mab-hero:after {
  content:""; position:absolute; inset:0;
  background-image: linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px);
  background-size: 44px 44px; pointer-events:none;
}
.mab-kicker {color:#f4cf52; font-size:19px; font-weight:850; letter-spacing:.05em;}
.mab-title {font-size:64px; font-weight:400; font-style:italic; letter-spacing:-.04em; line-height:.96; margin-top:9px;}
.mab-title .gold {color:#d5a31b;}
.mab-subtitle {font-family: Georgia, serif; font-size:30px; margin-top:22px;}
.mab-city {font-size:11px; letter-spacing:.55em; color:#d3cec7; margin:8px 0 18px 82px;}
.mab-chiprow {display:flex; gap:10px; margin-top:20px;}
.mab-chip {font-size:9px; border:1px solid rgba(255,255,255,.28); border-radius:20px; padding:7px 12px; background:rgba(0,0,0,.28);}
.mab-chip.primary {color:#111; background:var(--mab-gold); border-color:var(--mab-gold); font-weight:900;}

.mab-content {padding: 26px 36px 0;}
.mab-panel {
  background: rgba(255,255,255,.65); border:1px solid #d8d1c6; border-radius:18px;
  padding:16px; box-shadow:0 14px 38px rgba(25,20,12,.08);
}
.mab-grid {display:grid; grid-template-columns: 1fr 1.45fr 1.55fr; gap:10px;}
.mab-card {background:var(--mab-card); border:1px solid var(--mab-line); border-radius:10px; min-height:190px; padding:22px;}
.mab-card.accent {border-left:4px solid var(--mab-gold);}
.mab-eyebrow {font-size:9px; letter-spacing:.25em; color:#b08c18; font-weight:900;}
.mab-card h3 {font-family:Georgia,serif; font-weight:500; font-size:25px; margin:12px 0 4px; color:#151515 !important;}
.mab-big {font-size:48px; font-weight:900; margin:11px 0 0;}
.mab-muted {font-size:11px; color:var(--mab-muted); line-height:1.65;}
.mab-kpi {display:flex; align-items:end; justify-content:space-between; margin-top:22px; padding-top:16px; border-top:1px solid #e1dbd1;}
.mab-kpi strong {font-size:28px;}

.mab-team-label {font-size:10px; font-weight:800; margin:18px 0 8px;}
.mab-teams {display:grid; grid-template-columns: repeat(12, 1fr); gap:6px;}
.mab-team {background:#fff; border:1px solid #d7d0c5; border-radius:8px; padding:8px 5px; text-align:center; min-height:72px;}
.mab-team-logo {width:34px; height:34px; border-radius:50%; margin:0 auto 4px; background:#1b1b1c; color:var(--mab-gold); display:flex; align-items:center; justify-content:center; font-weight:900; font-size:11px;}
.mab-team-name {font-size:8px; font-weight:800; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}

.mab-ai-banner {margin-top:16px; border-radius:11px; background:#181819; color:#fff; min-height:112px; padding:22px 26px; display:flex; justify-content:space-between; align-items:center;}
.mab-ai-banner h3 {color:white !important; margin:5px 0; font-size:20px;}
.mab-ai-status {border:1px solid #555; border-radius:28px; padding:14px 22px; color:var(--mab-gold); font-weight:900;}

.mab-section-title {margin:30px 0 8px; font-size:11px; color:#aa8214; letter-spacing:.28em; font-weight:900;}
.mab-section-head {font-size:30px; font-family:Georgia,serif; margin-bottom:6px;}

/* Streamlit navigation buttons */
div[data-testid="stPageLink"] a {
  border:1px solid #bbb3a7 !important; border-radius:999px !important; padding:10px 16px !important;
  background:#fffdf9 !important; color:#151515 !important; font-weight:800 !important; text-decoration:none !important;
}
div[data-testid="stPageLink"] a:hover {border-color:var(--mab-gold) !important; box-shadow:0 0 0 2px rgba(243,196,0,.12);}

@media (max-width: 900px) {
  .mab-nav-items {display:none;}
  .mab-nav {padding:0 14px;}
  .mab-brand {min-width:0; flex:1;}
  .mab-hero {padding:30px 20px; min-height:280px;}
  .mab-title {font-size:42px;}
  .mab-subtitle {font-size:23px;}
  .mab-content {padding:18px 12px 0;}
  .mab-grid {grid-template-columns:1fr;}
  .mab-teams {grid-template-columns:repeat(4,1fr);}
}
</style>
""",
    unsafe_allow_html=True,
)

nav_items = [
    ("⌂", "ホーム", True), ("◉", "試合", False), ("▥", "戦績", False),
    ("◇", "AI予測", False), ("✓", "予想結果", False), ("↗", "収支マップ", False), ("✦", "AI Hero", False),
]
nav_html = "".join(
    f'<div class="mab-nav-item {"active" if active else ""}"><b>{icon}</b>{label}</div>'
    for icon, label, active in nav_items
)

st.markdown(
    f"""
<div class="mab-nav">
  <div class="mab-brand">
    <div class="mab-logo">M</div>
    <div><div class="mab-brand-title">MY AI BASEBALL</div><div class="mab-brand-sub">GAME INTELLIGENCE</div></div>
    <span class="mab-next">NEXT</span>
  </div>
  <div class="mab-nav-items">{nav_html}</div>
  <div class="mab-nav-actions"><div class="mab-square">JP</div><div class="mab-square">↻</div></div>
</div>
<div class="mab-hero">
  <div class="mab-kicker">データで、もっと野球が楽しくなる。</div>
  <div class="mab-title">MY AI <span class="gold">BASEBALL</span></div>
  <div class="mab-subtitle">GAME INTELLIGENCE 2026</div>
  <div class="mab-city">JAPAN · NPB</div>
  <div class="mab-chiprow">
    <span class="mab-chip primary">MY AI BASEBALL 03</span>
    <span class="mab-chip">◷ {now_jst.strftime('%H:%M:%S')} 更新</span>
    <span class="mab-chip">DATA {updated_at}</span>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

team_html = "".join(
    f'<div class="mab-team"><div class="mab-team-logo">{abbr}</div><div class="mab-team-name">{name}</div></div>'
    for name, abbr in teams
)

st.markdown(
    f"""
<div class="mab-content">
  <div class="mab-panel">
    <div class="mab-grid">
      <div class="mab-card">
        <div class="mab-eyebrow">TODAY'S AI PICK</div>
        <h3>{best_pick}</h3>
        <div class="mab-muted">{best_match}</div>
        <div class="mab-kpi"><span class="mab-muted">AI勝率</span><strong>{best_prob_label}</strong></div>
      </div>
      <div class="mab-card">
        <div class="mab-eyebrow">TODAY / NPB</div>
        <h3>本日の対戦カード</h3>
        <div class="mab-big">{len(today_games)}</div>
        <div class="mab-muted">共有データを監視し、試合・先発・結果を自動同期します。</div>
      </div>
      <div class="mab-card accent">
        <div class="mab-eyebrow">BET & PERFORMANCE</div>
        <h3>収支データを統合</h3>
        <div class="mab-muted">AI予測・ハンデ・BET記録・結果検証を同じダッシュボードで管理。</div>
        <div class="mab-kpi"><span class="mab-muted">週次未確定損益</span><strong>{profit_label}</strong></div>
      </div>
    </div>
    <div class="mab-team-label">12球団を切り替える</div>
    <div class="mab-teams">{team_html}</div>
    <div class="mab-ai-banner">
      <div><div class="mab-eyebrow">AI PREDICTION</div><h3>次戦の勝率予測・ハンデ・収支を統合</h3><div class="mab-muted" style="color:#aaa">先発投手、直近成績、対戦相性、球場特性、ハンデ情報を再取得します。</div></div>
      <div class="mab-ai-status">自動監視中</div>
    </div>
  </div>
  <div class="mab-section-title">FUNCTIONS</div>
  <div class="mab-section-head">機能を選択</div>
  <div class="mab-muted">既存機能を維持したまま、このデザインへ順次統合しています。</div>
</div>
""",
    unsafe_allow_html=True,
)

st.write("")
links = st.columns(4)
with links[0]:
    st.page_link("pages/本日のAI予想.py", label="AI予測", icon="🤖", use_container_width=True)
with links[1]:
    st.page_link("pages/収支マップ.py", label="収支マップ", icon="📈", use_container_width=True)
with links[2]:
    st.page_link("pages/BET入力.py", label="BET入力", icon="✍️", use_container_width=True)
with links[3]:
    st.page_link("pages/AI詳細.py", label="詳細ダッシュボード", icon="⚾", use_container_width=True)

st.caption("MY AI BASEBALL · chatgpt.site design shell / existing AI functions preserved")
