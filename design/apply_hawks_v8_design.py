#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime

APP = Path("/opt/hawks-ai/app.py")
CSS_FILE = Path(__file__).with_name("hawks_v8_final.css")

if not APP.exists():
    raise SystemExit(f"APP_NOT_FOUND: {APP}")
if not CSS_FILE.exists():
    raise SystemExit(f"CSS_NOT_FOUND: {CSS_FILE}")

s = APP.read_text(encoding="utf-8")
backup = Path("/home/user/hawks-backup") / f"app.py.before-v8-final-{datetime.now():%Y%m%d-%H%M%S}"
backup.parent.mkdir(parents=True, exist_ok=True)
backup.write_text(s, encoding="utf-8")

css = CSS_FILE.read_text(encoding="utf-8")
style = '<style id="hawks-v8-web-final">\n' + css + '\n</style>'
marker = '<style id="hawks-v8-web-final">'

if marker in s:
    a = s.find(marker)
    b = s.find("</style>", a)
    if b == -1:
        raise SystemExit("FINAL_STYLE_END_NOT_FOUND")
    b += len("</style>")
    s = s[:a] + style + s[b:]
else:
    pos = s.rfind("</style>")
    if pos == -1:
        raise SystemExit("NO_STYLE_BLOCK_FOUND")
    pos += len("</style>")
    s = s[:pos] + "\n" + style + "\n" + s[pos:]

a = s.find("# HAWKS AI PREMIUM LIVE STATUS")
b = s.find("# HAWKS AI v2.4 LIVE自動反映", a)
if a == -1 or b == -1:
    raise SystemExit("LIVE_STATUS_MARKERS_NOT_FOUND")

live_block = """# HAWKS AI PREMIUM LIVE STATUS
_live_status = str(live.get("status", "取得中"))
if _live_status == "試合中":
    _live_badge, _live_class = "● LIVE", "is-live"
elif _live_status == "試合終了":
    _live_badge, _live_class = "試合終了", "is-finished"
else:
    _live_badge, _live_class = "試合開始前", "is-waiting"

st.markdown(
    f\"\"\"
    <div class="hawks-live-strip">
      <div class="hawks-live-left">
        <span class="hawks-live-dot"></span>
        <span class="hawks-live-title">⚾ NPB公式速報：{_live_status}</span>
      </div>
      <div class="hawks-live-right">
        <span class="hawks-live-badge {_live_class}">{_live_badge}</span>
        <span class="hawks-live-refresh">自動確認 15秒キャッシュ</span>
      </div>
    </div>
    \"\"\",
    unsafe_allow_html=True
)

"""
s = s[:a] + live_block + s[b:]

a = s.find("# HAWKS AI PREMIUM SCOREBOARD")
b = s.find("# AI計算へ渡す点差", a)
if a == -1 or b == -1:
    raise SystemExit("SCOREBOARD_MARKERS_NOT_FOUND")

score_block = """# HAWKS AI PREMIUM SCOREBOARD
if live_score_ready:
    hawks_score = int(live["hawks_score"])
    opponent_score = int(live["opp_score"])
else:
    score_c1, score_c2 = st.columns(2)
    with score_c1:
        hawks_score = st.number_input("🦅 ホークス得点", min_value=0, max_value=99, value=0, step=1, key="hawks_score")
    with score_c2:
        opponent_score = st.number_input("⚾ 相手得点", min_value=0, max_value=99, value=0, step=1, key="opponent_score")

score_diff = hawks_score - opponent_score
if score_diff > 0:
    score_status, score_status_class, score_icon = f"{score_diff}点リード", "hawks-leading", "🦅"
elif score_diff < 0:
    score_status, score_status_class, score_icon = f"{abs(score_diff)}点ビハインド", "hawks-behind", "🔥"
else:
    score_status, score_status_class, score_icon = "同点", "hawks-tied", "⚾"

if live_score_ready:
    opponent_name = str(npb.get("opponent", "OPPONENT"))
    game_status = str(live.get("status", "-"))
    if game_status == "試合終了":
        status_text = "FINAL"
    elif game_status == "試合中":
        i = live.get("inning")
        h = live.get("half", "")
        status_text = f"{i}回{h}" if i else "LIVE"
    else:
        status_text = game_status

    st.markdown(
        f\"\"\"
        <div class="hawks-game-card">
          <div class="hawks-game-card-head">
            <div class="hawks-game-card-title"><span class="hawks-red-dot"></span>試合状況（NPB LIVE自動反映）</div>
            <div class="hawks-game-card-source">NPB LIVE</div>
          </div>
          <div class="hawks-score-area">
            <div class="hawks-team hawks-home">
              <div class="hawks-team-icon">🦅</div>
              <div class="hawks-team-name">HAWKS</div>
              <div class="hawks-team-sub">ソフトバンク</div>
              <div class="hawks-score-number hawks-score-main">{hawks_score}</div>
            </div>
            <div class="hawks-vs-area">
              <div class="hawks-final-badge">{status_text}</div>
              <div class="hawks-vs">VS</div>
              <div class="hawks-score-diff {score_status_class}">{score_icon} {score_status}</div>
            </div>
            <div class="hawks-team hawks-away">
              <div class="hawks-team-icon">⚾</div>
              <div class="hawks-team-name">{opponent_name}</div>
              <div class="hawks-team-sub">OPPONENT</div>
              <div class="hawks-score-number">{opponent_score}</div>
            </div>
          </div>
          <div class="hawks-score-footer">
            <span class="hawks-sync-dot"></span>
            NPB公式速報のスコアを自動使用中
            <span class="hawks-auto-badge">AUTO</span>
          </div>
        </div>
        \"\"\",
        unsafe_allow_html=True
    )

"""
s = s[:a] + score_block + s[b:]

APP.write_text(s, encoding="utf-8")
print("PATCH_OK")
print("APP:", APP)
print("BACKUP:", backup)
print("NEXT:")
print("python3 -m py_compile /opt/hawks-ai/app.py && echo 'PYTHON OK'")
print("docker cp /opt/hawks-ai/app.py hawks-app:/app/app.py")
print("docker restart hawks-app")
