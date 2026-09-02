import html
import streamlit as st


STUDIO_CSS = r'''
<style>
:root {
  --studio-bg: #0b0d10;
  --studio-panel: #12161c;
  --studio-panel-2: #171c23;
  --studio-paper: #f7f5ef;
  --studio-ink: #f5f7fa;
  --studio-ink-dark: #17191d;
  --studio-gold: #f2c94c;
  --studio-gold-2: #b98711;
  --studio-line: rgba(255,255,255,.10);
  --studio-muted: #9299a3;
  --studio-shadow: 0 18px 50px rgba(0,0,0,.22);
}

html {background:var(--studio-bg);}
[data-testid="stHeader"], [data-testid="stToolbar"], footer {display:none !important;}
[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(circle at 8% -10%, rgba(242,201,76,.10), transparent 26%),
    radial-gradient(circle at 95% 0%, rgba(59,130,246,.08), transparent 22%),
    var(--studio-bg) !important;
  color:var(--studio-ink) !important;
}
.block-container {max-width:1440px !important; padding:0 28px 64px !important;}
[data-testid="stSidebar"] {background:#101318;}

h1,h2,h3,h4,p,label,span,div {font-family:Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;}
h1,h2,h3,h4 {color:var(--studio-ink) !important;}
p, label, .stCaption {color:#b7bdc7 !important;}

.studio-topbar {
  position:sticky; top:0; z-index:999;
  margin:0 -28px 22px; min-height:72px; padding:0 28px;
  background:rgba(9,11,14,.90); backdrop-filter:blur(18px);
  border-bottom:1px solid rgba(242,201,76,.20);
  display:flex; align-items:center; justify-content:space-between; gap:22px;
}
.studio-brand {display:flex; align-items:center; gap:12px; min-width:260px;}
.studio-mark {
  width:40px;height:40px;border-radius:12px;
  background:linear-gradient(145deg,#ffe37c,#d6a51c);
  color:#111;display:flex;align-items:center;justify-content:center;
  font-size:19px;font-weight:1000;font-style:italic;
  box-shadow:0 8px 24px rgba(242,201,76,.22);
}
.studio-brand-title {font-weight:950;letter-spacing:.13em;font-size:13px;line-height:1.1;color:#fff;}
.studio-brand-sub {font-size:7px;color:#7f8792;letter-spacing:.34em;margin-top:5px;}
.studio-nav {display:flex;align-items:center;justify-content:center;gap:7px;flex:1;}
.studio-nav a {
  font-size:9px;color:#8f97a3;text-decoration:none;white-space:nowrap;font-weight:850;
  padding:9px 11px;border-radius:999px;transition:.18s ease;
}
.studio-nav a:hover {color:#111;background:var(--studio-gold);}
.studio-badge {
  font-size:8px;border:1px solid rgba(255,255,255,.12);border-radius:999px;
  padding:8px 11px;color:#d8dde5;white-space:nowrap;background:rgba(255,255,255,.04);
}

.studio-hero {
  min-height:220px;
  background:
    radial-gradient(circle at 82% 12%, rgba(242,201,76,.28), transparent 26%),
    linear-gradient(135deg,#11151a 0%,#17191d 50%,#241d0d 100%);
  color:#fff;border:1px solid rgba(255,255,255,.08);border-radius:24px;
  padding:34px 38px;margin-bottom:20px;position:relative;overflow:hidden;
  box-shadow:var(--studio-shadow);
  display:flex;flex-direction:column;justify-content:center;
}
.studio-hero:before {
  content:"";position:absolute;right:-30px;bottom:-100px;width:340px;height:340px;
  border:1px solid rgba(242,201,76,.10);border-radius:50%;
  box-shadow:0 0 0 34px rgba(242,201,76,.025),0 0 0 68px rgba(242,201,76,.018);
}
.studio-hero:after {
  content:"";position:absolute;inset:0;
  background-image:linear-gradient(rgba(255,255,255,.018) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.018) 1px,transparent 1px);
  background-size:34px 34px;pointer-events:none;
}
.studio-kicker {font-size:9px;letter-spacing:.28em;color:#e7c55f;font-weight:950;text-transform:uppercase;position:relative;z-index:1;}
.studio-title {font-size:42px;line-height:1.02;font-weight:950;margin:10px 0 12px;letter-spacing:-.045em;position:relative;z-index:1;max-width:900px;}
.studio-title span {color:var(--studio-gold);}
.studio-subtitle {font-size:13px;color:#aeb5c0;max-width:800px;line-height:1.8;position:relative;z-index:1;}

.studio-section-label {font-size:8px;letter-spacing:.28em;color:#d8b94c;font-weight:950;margin:28px 0 5px;}
.studio-section-title {font-size:24px;font-weight:950;letter-spacing:-.02em;margin:0 0 14px;color:#f7f7f8;}
.studio-card {background:var(--studio-panel);border:1px solid var(--studio-line);border-radius:18px;padding:18px;box-shadow:0 10px 30px rgba(0,0,0,.12);}
.studio-card-dark {background:#15191f;color:#fff;border:1px solid var(--studio-line);border-radius:18px;padding:18px;}
.studio-note {font-size:11px;color:var(--studio-muted);line-height:1.7;}
.studio-rank {width:38px;height:38px;border-radius:12px;background:var(--studio-gold);color:#111;display:inline-flex;align-items:center;justify-content:center;font-weight:950;}
.studio-pick {font-size:23px;font-weight:950;}

/* Metrics */
div[data-testid="stMetric"] {
  min-height:116px;
  background:linear-gradient(180deg,rgba(255,255,255,.045),rgba(255,255,255,.022));
  border:1px solid rgba(255,255,255,.09);
  padding:18px 18px 16px;border-radius:18px;
  box-shadow:0 10px 26px rgba(0,0,0,.10);
}
div[data-testid="stMetric"] label {color:#8e96a2 !important;font-size:11px !important;font-weight:800 !important;}
div[data-testid="stMetricValue"] {color:#fff !important;font-weight:950 !important;font-size:28px !important;letter-spacing:-.03em;}
div[data-testid="stMetricDelta"] {color:var(--studio-gold) !important;}

/* Forms and controls */
div[data-testid="stForm"], div[data-testid="stExpander"] {
  background:var(--studio-panel);border:1px solid var(--studio-line) !important;border-radius:18px !important;
}
[data-baseweb="input"] > div,
[data-baseweb="select"] > div,
textarea {
  background:#11151a !important;border-color:rgba(255,255,255,.10) !important;color:#fff !important;
}
.stButton>button, button[kind="primary"] {
  min-height:44px;background:linear-gradient(135deg,#f3d45d,#d5a31d) !important;
  color:#111 !important;border:0 !important;border-radius:12px !important;font-weight:950 !important;
  box-shadow:0 8px 20px rgba(242,201,76,.14) !important;
}
.stButton>button:hover, button[kind="primary"]:hover {transform:translateY(-1px);box-shadow:0 12px 24px rgba(242,201,76,.22) !important;}

/* Page links */
[data-testid="stPageLink"] a {
  min-height:58px;background:linear-gradient(180deg,#171b21,#12161b) !important;
  color:#f8f9fb !important;border:1px solid rgba(255,255,255,.09) !important;
  border-radius:16px !important;font-weight:900 !important;padding:14px 16px !important;
  box-shadow:0 8px 20px rgba(0,0,0,.10);
}
[data-testid="stPageLink"] a:hover {border-color:rgba(242,201,76,.55) !important;transform:translateY(-1px);}

/* Data */
[data-testid="stDataFrame"], [data-testid="stTable"] {
  background:var(--studio-panel);border:1px solid var(--studio-line);border-radius:16px;overflow:hidden;
}
[data-testid="stAlert"] {border-radius:16px !important;}
hr {border-color:rgba(255,255,255,.08) !important;}

/* Better column rhythm */
[data-testid="stHorizontalBlock"] {gap:12px !important;}
[data-testid="column"] {min-width:0;}

@media (max-width: 980px) {
  .studio-brand {min-width:auto;}
  .studio-nav {overflow-x:auto;justify-content:flex-start;gap:4px;padding-bottom:2px;}
  .studio-badge {display:none;}
  .studio-title {font-size:36px;}
}

@media (max-width: 760px) {
  .block-container {padding:0 12px 42px !important;}
  .studio-topbar {margin:0 -12px 16px;padding:0 12px;min-height:64px;gap:10px;}
  .studio-brand-title {font-size:11px;}
  .studio-brand-sub {display:none;}
  .studio-mark {width:36px;height:36px;}
  .studio-nav {max-width:54vw;}
  .studio-nav a {font-size:8px;padding:8px 9px;}
  .studio-hero {padding:26px 20px;min-height:205px;border-radius:20px;}
  .studio-title {font-size:31px;}
  .studio-subtitle {font-size:12px;line-height:1.65;}
  .studio-section-title {font-size:22px;}
  div[data-testid="stMetric"] {min-height:98px;padding:15px;}
  div[data-testid="stMetricValue"] {font-size:24px !important;}
}
</style>
'''


def apply_studio_theme():
    st.markdown(STUDIO_CSS, unsafe_allow_html=True)


def render_topbar(section="STUDIO"):
    safe_section = html.escape(str(section))
    st.markdown(
        f'''
<div class="studio-topbar">
  <div class="studio-brand">
    <div class="studio-mark">AI</div>
    <div>
      <div class="studio-brand-title">AI BASEBALL STUDIO</div>
      <div class="studio-brand-sub">GAME INTELLIGENCE</div>
    </div>
  </div>
  <nav class="studio-nav">
    <a href="/" target="_self">HOME</a>
    <a href="/試合" target="_self">GAMES</a>
    <a href="/本日のAI予想" target="_self">AI PREDICTION</a>
    <a href="/予想結果" target="_self">RESULTS</a>
    <a href="/BET入力" target="_self">SIMULATION</a>
    <a href="/収支マップ" target="_self">ANALYSIS</a>
  </nav>
  <div class="studio-badge">{safe_section}</div>
</div>
''',
        unsafe_allow_html=True,
    )


def render_hero(title, subtitle, kicker="AI BASEBALL STUDIO", accent=None):
    safe_title = html.escape(str(title))
    safe_subtitle = html.escape(str(subtitle))
    safe_kicker = html.escape(str(kicker))
    if accent and accent in safe_title:
        safe_title = safe_title.replace(accent, f"<span>{accent}</span>", 1)
    st.markdown(
        f'''
<div class="studio-hero">
  <div class="studio-kicker">{safe_kicker}</div>
  <div class="studio-title">{safe_title}</div>
  <div class="studio-subtitle">{safe_subtitle}</div>
</div>
''',
        unsafe_allow_html=True,
    )


def render_section(label, title):
    st.markdown(
        f'<div class="studio-section-label">{html.escape(str(label))}</div>'
        f'<div class="studio-section-title">{html.escape(str(title))}</div>',
        unsafe_allow_html=True,
    )


def render_nav_links():
    return None
