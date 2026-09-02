import html
import streamlit as st

STUDIO_CSS = r'''
<style>
:root {
  --studio-bg:#090b0e;
  --studio-panel:#101419;
  --studio-panel-2:#151a20;
  --studio-panel-3:#0e1217;
  --studio-ink:#f4f6f8;
  --studio-muted:#8d95a0;
  --studio-gold:#f0b82f;
  --studio-gold-2:#c98d0a;
  --studio-line:rgba(255,255,255,.10);
}
html{background:var(--studio-bg)}
[data-testid="stHeader"],[data-testid="stToolbar"],footer{display:none!important}
[data-testid="stAppViewContainer"]{background:linear-gradient(180deg,#090b0e 0%,#0a0d11 100%)!important;color:var(--studio-ink)!important}
.block-container{max-width:1460px!important;padding:0 28px 46px!important}
[data-testid="stSidebar"]{background:#0d1014}
*{box-sizing:border-box}
h1,h2,h3,h4,p,label,span,div{font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
h1,h2,h3,h4{color:#fff!important}
p,label,.stCaption{color:#aab1bb!important}

.studio-topbar{margin:0 -28px 18px;min-height:76px;padding:0 28px;background:#07090b;border-bottom:1px solid rgba(255,255,255,.08);display:flex;align-items:center;gap:22px}
.studio-brand{display:flex;align-items:center;gap:12px;min-width:285px;text-decoration:none}
.studio-brand:hover .studio-brand-title{color:#ffd45a}
.studio-mark{width:42px;height:42px;border:2px solid var(--studio-gold);border-radius:50%;display:grid;place-items:center;color:var(--studio-gold);font-size:13px;font-weight:1000;background:transparent}
.studio-brand-title{font-size:17px;font-weight:950;letter-spacing:.05em;color:var(--studio-gold)}
.studio-brand-sub{font-size:8px;color:#a4abb4;margin-top:4px}
.studio-nav{display:flex;align-items:stretch;justify-content:center;gap:18px;flex:1;min-width:0}
.studio-nav a{position:relative;display:flex;align-items:center;justify-content:center;min-height:76px;padding:0 4px;color:#c8cdd4;text-decoration:none;font-size:10px;font-weight:850;white-space:nowrap}
.studio-nav a:hover{color:#fff}
.studio-nav a:first-child:after{content:"";position:absolute;left:0;right:0;bottom:0;height:3px;background:var(--studio-gold);border-radius:3px 3px 0 0}
.studio-badge{min-width:148px;text-align:center;border:1px solid rgba(240,184,47,.72);border-radius:7px;padding:11px 14px;color:var(--studio-gold);font-size:9px;font-weight:900;line-height:1.35}

.studio-hero{min-height:136px;background:linear-gradient(90deg,rgba(15,19,24,.98),rgba(11,14,18,.96));border:1px solid var(--studio-line);border-radius:10px;padding:24px 28px;margin-bottom:14px;position:relative;overflow:hidden;display:flex;flex-direction:column;justify-content:center}
.studio-hero:before{content:"";position:absolute;inset:0;background:radial-gradient(circle at 18% 10%,rgba(255,255,255,.05),transparent 28%),linear-gradient(90deg,transparent 0%,rgba(255,255,255,.015) 45%,transparent 100%);pointer-events:none}
.studio-kicker{font-size:8px;color:#a2a9b2;letter-spacing:.18em;font-weight:900;position:relative;z-index:1}
.studio-title{font-size:28px;line-height:1.1;font-weight:950;letter-spacing:-.025em;margin:7px 0 8px;position:relative;z-index:1;color:#fff}
.studio-title span{color:#fff}
.studio-subtitle{font-size:12px;line-height:1.75;color:#aeb5be;max-width:820px;position:relative;z-index:1}

.dashboard-panel{background:var(--studio-panel);border:1px solid var(--studio-line);border-radius:10px;padding:14px}
.dashboard-title{display:flex;align-items:center;gap:9px;font-size:18px;font-weight:950;color:#fff;margin:0 0 12px}
.dashboard-title.gold{color:var(--studio-gold)}
.dashboard-subtle{font-size:9px;color:#89919c}
.kpi-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:0 0 14px}
.kpi-card{background:linear-gradient(180deg,#151a20,#11161b);border:1px solid var(--studio-line);border-radius:10px;padding:16px 18px;min-height:112px;display:flex;align-items:center;gap:14px}
.kpi-icon{font-size:28px;color:var(--studio-gold);min-width:34px;text-align:center}
.kpi-label{font-size:10px;color:#b4bac3;margin-bottom:3px}
.kpi-value{font-size:28px;font-weight:950;color:#fff;line-height:1.05}
.kpi-value.gold{color:var(--studio-gold)}
.kpi-note{font-size:9px;color:#89919b;margin-top:5px}
.kpi-note.up{color:#4bd07f}

.match-table{width:100%;border-collapse:collapse;font-size:11px}
.match-table th{font-size:9px;color:#939ba6;font-weight:850;padding:9px 10px;text-align:left;border-bottom:1px solid rgba(255,255,255,.08);background:#141920}
.match-table td{padding:10px;border-bottom:1px solid rgba(255,255,255,.07);color:#e8ebef;vertical-align:middle}
.match-table tr:last-child td{border-bottom:0}
.team-strong{font-weight:900;color:#fff}.prob-gold{color:var(--studio-gold);font-weight:950;font-size:14px}.prob-muted{color:#e5e8ec;font-weight:850}
.pick-chip{display:inline-block;padding:5px 8px;border-radius:5px;background:#6d5111;color:#ffe59a;font-size:9px;font-weight:900}

.top-ai-card{background:linear-gradient(180deg,#19150b,#11120f);border:1px solid var(--studio-gold);box-shadow:0 0 0 1px rgba(240,184,47,.15),0 0 28px rgba(240,184,47,.12);border-radius:10px;padding:14px}
.top-ai-row{display:grid;grid-template-columns:36px 1fr 78px;gap:10px;align-items:center;padding:11px;border:1px solid rgba(255,255,255,.08);background:#0d1014;border-radius:7px;margin-bottom:8px}
.top-ai-rank{font-size:28px;font-weight:950;color:var(--studio-gold);text-align:center}.top-ai-name{font-size:12px;font-weight:900;color:#fff}.top-ai-prob{font-size:16px;font-weight:950;color:#fff;text-align:right}.top-ai-meta{font-size:9px;color:#969da7;margin-top:3px}

.analysis-list{display:flex;flex-direction:column;gap:7px}.analysis-row{display:grid;grid-template-columns:74px 1fr 70px 65px 52px;gap:8px;align-items:center;padding:8px 10px;background:#11161b;border:1px solid rgba(255,255,255,.07);border-radius:6px;font-size:9px;color:#d8dde3}.status-chip{justify-self:end;padding:4px 7px;border-radius:4px;font-size:8px;font-weight:950}.status-win{background:#113e24;color:#75e59c}.status-loss{background:#45191c;color:#ff9298}.status-pending{background:#3a3518;color:#e6ce6b}

.research-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.research-card{background:linear-gradient(180deg,#151a20,#11161b);border:1px solid var(--studio-line);border-radius:8px;padding:16px;text-align:center;min-height:190px;display:flex;flex-direction:column;justify-content:space-between}.research-icon{font-size:34px;color:var(--studio-gold)}.research-title{font-size:14px;font-weight:900;color:#fff}.research-sub{font-size:9px;color:#a0a8b2}.research-desc{font-size:10px;color:#b7bdc5;line-height:1.6}.research-link{display:block;margin-top:10px;padding:8px;border:1px solid rgba(240,184,47,.45);border-radius:5px;color:var(--studio-gold);text-decoration:none;font-size:10px;font-weight:900}

.section-gap{height:10px}.footer-line{margin-top:14px;padding-top:12px;border-top:1px solid rgba(255,255,255,.08);font-size:8px;color:#7e8791;display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}

@media(max-width:1100px){.studio-nav{gap:9px}.studio-nav a{font-size:8px}.studio-brand{min-width:220px}.studio-badge{display:none}.kpi-grid{grid-template-columns:repeat(3,1fr)}.research-grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:760px){.block-container{padding:0 12px 36px!important}.studio-topbar{margin:0 -12px 14px;padding:0 12px;min-height:66px}.studio-brand{min-width:auto}.studio-brand-title{font-size:12px}.studio-brand-sub{display:none}.studio-nav{overflow-x:auto;justify-content:flex-start}.studio-nav a{min-height:66px}.studio-hero{padding:20px;min-height:126px}.studio-title{font-size:23px}.kpi-grid{grid-template-columns:1fr 1fr}.research-grid{grid-template-columns:1fr}.analysis-row{grid-template-columns:1fr 1fr}.analysis-row>*:nth-child(n+3){display:none}}
</style>
'''


def apply_studio_theme():
    st.markdown(STUDIO_CSS, unsafe_allow_html=True)


def render_topbar(section="RESEARCH MODE"):
    safe_section = html.escape(str(section))
    st.markdown(f'''
<div class="studio-topbar">
  <a class="studio-brand" href="/" target="_self" aria-label="トップページへ戻る">
    <div class="studio-mark">⚾</div>
    <div><div class="studio-brand-title">AI BASEBALL STUDIO</div><div class="studio-brand-sub">AI野球分析・シミュレーション研究所</div></div>
  </a>
  <nav class="studio-nav">
    <a href="/" target="_self">DASHBOARD</a>
    <a href="/試合" target="_self">GAMES</a>
    <a href="/本日のAI予想" target="_self">AI RANKING</a>
    <a href="/BET入力" target="_self">SIMULATION</a>
    <a href="/収支マップ" target="_self">ANALYSIS</a>
    <a href="/予想結果" target="_self">HISTORY</a>
    <a href="/設定" target="_self">SETTINGS</a>
  </nav>
  <div class="studio-badge">{safe_section}<br><span style="font-size:7px;color:#bfa75f;">研究・仮説検証用</span></div>
</div>''', unsafe_allow_html=True)


def render_hero(title, subtitle, kicker="AI BASEBALL STUDIO", accent=None):
    safe_title = html.escape(str(title))
    safe_subtitle = html.escape(str(subtitle))
    safe_kicker = html.escape(str(kicker))
    st.markdown(f'''
<div class="studio-hero">
  <div class="studio-kicker">{safe_kicker}</div>
  <div class="studio-title">{safe_title}</div>
  <div class="studio-subtitle">{safe_subtitle}</div>
</div>''', unsafe_allow_html=True)


def render_section(label, title):
    st.markdown(f'<div class="studio-kicker">{html.escape(str(label))}</div><div class="dashboard-title">{html.escape(str(title))}</div>', unsafe_allow_html=True)


def render_nav_links():
    return None
