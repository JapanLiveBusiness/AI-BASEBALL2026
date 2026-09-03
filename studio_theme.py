import html
import streamlit as st

from auth import require_login

STUDIO_CSS = r'''
<style>
:root{--bg:#090b0e;--panel:#101419;--panel2:#151a20;--ink:#f4f6f8;--muted:#8d95a0;--gold:#f0b82f;--line:rgba(255,255,255,.10)}
html{background:var(--bg)}
[data-testid="stHeader"],[data-testid="stToolbar"],footer{display:none!important}
[data-testid="stAppViewContainer"]{background:linear-gradient(180deg,#090b0e,#0a0d11)!important;color:var(--ink)!important}
.block-container{max-width:1460px!important;padding:0 28px 46px!important}
[data-testid="stSidebar"]{background:#0d1014}
*{box-sizing:border-box}h1,h2,h3,h4,p,label,span,div{font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}h1,h2,h3,h4{color:#fff!important}p,label,.stCaption{color:#aab1bb!important}
.studio-topbar{margin:0 -28px 18px;min-height:76px;padding:0 28px;background:#07090b;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:22px}.studio-brand{display:flex;align-items:center;gap:12px;min-width:285px;text-decoration:none}.studio-mark{width:42px;height:42px;border:2px solid var(--gold);border-radius:50%;display:grid;place-items:center;color:var(--gold);font-weight:950}.studio-brand-title{font-size:17px;font-weight:950;letter-spacing:.05em;color:var(--gold)}.studio-brand-sub{font-size:8px;color:#a4abb4;margin-top:4px}.studio-nav{display:flex;align-items:stretch;justify-content:center;gap:14px;flex:1;min-width:0}.studio-nav a{display:flex;align-items:center;justify-content:center;min-height:76px;padding:0 4px;color:#c8cdd4;text-decoration:none;font-size:9px;font-weight:850;white-space:nowrap}.studio-nav a:hover{color:#fff}.studio-badge{min-width:148px;text-align:center;border:1px solid rgba(240,184,47,.72);border-radius:7px;padding:11px 14px;color:var(--gold);font-size:9px;font-weight:900;line-height:1.35}
.studio-hero{min-height:136px;background:linear-gradient(90deg,#0f1318,#0b0e12);border:1px solid var(--line);border-radius:10px;padding:24px 28px;margin-bottom:14px;display:flex;flex-direction:column;justify-content:center}.studio-kicker{font-size:8px;color:#a2a9b2;letter-spacing:.18em;font-weight:900}.studio-title{font-size:28px;line-height:1.1;font-weight:950;letter-spacing:-.025em;margin:7px 0 8px;color:#fff}.studio-subtitle{font-size:12px;line-height:1.75;color:#aeb5be;max-width:820px}.dashboard-title{display:flex;align-items:center;gap:9px;font-size:18px;font-weight:950;color:#fff;margin:0 0 12px}.studio-rank{width:38px;height:38px;border-radius:10px;background:var(--gold);color:#111;display:grid;place-items:center;font-weight:950}
[data-testid="stMetric"]{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px}.stButton>button,button[kind="primary"]{background:var(--gold)!important;color:#111!important;border:0!important;border-radius:10px!important;font-weight:900!important}[data-testid="stPageLink"] a{background:var(--panel)!important;border:1px solid var(--line)!important;border-radius:12px!important;color:#fff!important}
@media(max-width:900px){.studio-badge{display:none}.studio-nav{overflow-x:auto;justify-content:flex-start;gap:9px}.studio-brand{min-width:220px}}@media(max-width:760px){.block-container{padding:0 12px 36px!important}.studio-topbar{margin:0 -12px 14px;padding:0 12px;min-height:66px}.studio-brand{min-width:auto}.studio-brand-title{font-size:12px}.studio-brand-sub{display:none}.studio-nav a{min-height:66px;font-size:8px}.studio-hero{padding:20px;min-height:126px}.studio-title{font-size:23px}}
</style>
'''


def apply_studio_theme():
    require_login()
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
    <a href="/レポート" target="_self">REPORT</a>
    <a href="/設定" target="_self">SETTINGS</a>
  </nav>
  <div class="studio-badge">{safe_section}<br><span style="font-size:7px;color:#bfa75f">研究・仮説検証用</span></div>
</div>''', unsafe_allow_html=True)


def render_hero(title, subtitle, kicker="AI BASEBALL STUDIO", accent=None):
    st.markdown(
        f'<div class="studio-hero"><div class="studio-kicker">{html.escape(str(kicker))}</div><div class="studio-title">{html.escape(str(title))}</div><div class="studio-subtitle">{html.escape(str(subtitle))}</div></div>',
        unsafe_allow_html=True,
    )


def render_section(label, title):
    st.markdown(f'<div class="studio-kicker">{html.escape(str(label))}</div><div class="dashboard-title">{html.escape(str(title))}</div>', unsafe_allow_html=True)


def render_nav_links():
    return None

# Deployment refresh marker: 2026-09-03 JST
