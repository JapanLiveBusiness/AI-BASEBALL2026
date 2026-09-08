import html

import streamlit as st

from daily_data import load_current_daily_json
from daily_board import coverage, merge_daily_board
from studio_theme import apply_studio_theme, render_topbar, render_hero, render_section, render_nav_links

st.set_page_config(page_title="AI予測 | MY AI BASEBALL", page_icon="⚾", layout="wide")
apply_studio_theme()
render_topbar("AI PREDICTION")
render_hero(
    "本日のAI予測",
    "勝率・予想スコア・信頼度を1画面で比較。AI Baseball Studioのメインデザインに統一しています。",
    kicker="TODAY / NPB / AI PREDICTION",
    accent="AI予測",
)
render_nav_links()

@st.cache_data(ttl="1m", max_entries=4)
def load_json(name, fallback):
    return load_current_daily_json(name, fallback)


payload = load_json("today_ai_predictions.json", {"games": []})
schedule = load_json("npb_today.json", {"games": []})
games = merge_daily_board(schedule, payload)
status = coverage(games)
display_date = schedule.get("date") or payload.get("date") or ""
render_section("WIN / LOSS RANKING", f"{display_date} NPB 勝敗予測ランキング")

st.info(
    "予測強度は補正後勝率で分類します（高：65%以上、中：58%以上、標準：58%未満）。"
    "精度検証は同じ10ポイント確率帯の過去確定試合を使い、20試合以上で勝率補正へ反映します。",
    icon=":material/info:",
)

st.markdown(
    """
<style>
.prediction-list{display:grid;gap:14px;margin:16px 0 24px}
.prediction-card{background:#fffdf8;border:1px solid #ddd5c8;border-radius:16px;padding:18px;box-shadow:0 7px 20px rgba(35,29,18,.05)}
.prediction-head{display:grid;grid-template-columns:48px minmax(0,1fr) auto;gap:14px;align-items:center}
.prediction-rank{width:44px;height:44px;border-radius:50%;display:grid;place-items:center;background:#171717;color:#f1c40f;font-size:18px;font-weight:950}
.prediction-match b{display:block;font-size:18px;color:#111827}.prediction-match span{display:block;margin-top:4px;color:#6b7280;font-size:13px}
.prediction-prob{text-align:right}.prediction-prob small{display:block;color:#6b7280;font-size:12px}.prediction-prob strong{display:block;color:#9a7200;font-size:28px;line-height:1.1}
.prediction-bar{height:9px;margin:14px 0;background:#e8e3d9;border-radius:999px;overflow:hidden}.prediction-bar i{display:block;height:100%;background:linear-gradient(90deg,#d9a900,#f1c40f);border-radius:999px}
.prediction-detail{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px}.prediction-item{background:#f7f4ed;border-radius:10px;padding:10px}.prediction-item small{display:block;color:#6b7280;font-size:11px}.prediction-item b{display:block;margin-top:4px;font-size:14px;color:#1f2937}.prediction-item b.ok{color:#217043}.prediction-item b.wait{color:#9a6700}
.prediction-result{margin-top:12px;padding-top:11px;border-top:1px solid #e5dfd4;color:#4b5563;font-size:13px}
@media(max-width:700px){.prediction-card{padding:14px}.prediction-head{grid-template-columns:40px minmax(0,1fr)}.prediction-rank{width:38px;height:38px}.prediction-prob{grid-column:1/-1;display:flex;justify-content:space-between;align-items:end;text-align:left}.prediction-prob strong{font-size:25px}.prediction-detail{grid-template-columns:1fr 1fr}.prediction-item:last-child{grid-column:1/-1}}
</style>
""",
    unsafe_allow_html=True,
)

source_url = next((row.get("source_url") for row in schedule.get("games") or [] if row.get("source_url")), "https://handenomori.com/jpb/")
st.markdown(f"ハンデ情報: [ハンデの森]({source_url})（各試合の開始100分前までに一度取得し、取得値を固定）")

if not games:
    st.info("本日の試合データを同期中です。")
    st.stop()

if not status["complete"]:
    st.warning(f"全{status['games']}試合中、予想済みは{status['predicted']}試合です。未生成の試合は同期後に表示されます。")

cards = []
for game in sorted(games, key=lambda row: row.get("rank") or 999):
    rank = game.get("rank")
    home = game.get("home", "-")
    away = game.get("away", "-")
    pick = game.get("pick", "-")
    prob = game.get("win_probability", 0)
    score = game.get("predicted_score", "-")
    confidence = game.get("confidence", "-")
    home_score = game.get("home_score")
    away_score = game.get("away_score")
    result = game.get("actual_result", "未確定")
    verified = game.get("verified")

    raw_home = game.get("raw_home_win_probability")
    raw_pick = None
    if isinstance(raw_home, (int, float)):
        raw_pick = float(raw_home) if pick == home else 100.0 - float(raw_home)
    adjustment = game.get("calibration_adjustment")
    if isinstance(adjustment, (int, float)) and pick == away:
        adjustment = -float(adjustment)
    validation_count = int(game.get("validation_sample_size") or 0)
    validation_rate = game.get("validation_home_win_rate")
    if isinstance(validation_rate, (int, float)) and pick == away:
        validation_rate = 100.0 - float(validation_rate)
    validation_ready = validation_count >= 20 and isinstance(validation_rate, (int, float))
    validation_status = "検証反映済み" if validation_ready else f"データ不足 {validation_count}/20"
    confidence_labels = {"HIGH":"高", "MEDIUM":"中", "LOW":"標準", "A":"高", "A-":"やや高", "B":"標準", "C+":"参考"}
    result_text = "試合結果は未確定です。"
    if result != "未確定":
        verdict = "的中" if verified is True else "外れ" if verified is False else "判定対象外"
        result_text = f"結果：{away} {away_score} - {home_score} {home} ／ 勝者 {result} ／ {verdict}"
    prob_value = float(prob) if isinstance(prob, (int, float)) else 0.0
    cards.append(f'''<article class="prediction-card">
<div class="prediction-head"><div class="prediction-rank">{rank if rank is not None else "—"}</div>
<div class="prediction-match"><b>{html.escape(str(away))} @ {html.escape(str(home))}</b><span>AIの勝利予想：{html.escape(str(pick))}</span></div>
<div class="prediction-prob"><small>予測勝率</small><strong>{prob_value:.1f}%</strong></div></div>
<div class="prediction-bar"><i style="width:{max(0,min(100,prob_value)):.1f}%"></i></div>
<div class="prediction-detail">
<div class="prediction-item"><small>予想スコア</small><b>{html.escape(str(score))}</b></div>
<div class="prediction-item"><small>予測強度</small><b>{confidence_labels.get(str(confidence), html.escape(str(confidence)))}</b></div>
<div class="prediction-item"><small>補正前勝率</small><b>{f"{raw_pick:.1f}%" if raw_pick is not None else "--"}</b></div>
<div class="prediction-item"><small>検証補正</small><b>{f"{adjustment:+.1f}%" if isinstance(adjustment,(int,float)) else "--"}</b></div>
<div class="prediction-item"><small>同確率帯の実勝率</small><b>{f"{validation_rate:.1f}%" if isinstance(validation_rate,(int,float)) else "--"}</b></div>
<div class="prediction-item"><small>精度検証</small><b class="{'ok' if validation_ready else 'wait'}">{validation_status}</b></div></div>
<div class="prediction-result">{html.escape(result_text)}</div></article>''')

st.markdown(f'<div class="prediction-list">{"".join(cards)}</div>', unsafe_allow_html=True)

ranked = [game for game in games if game.get("pick")]
best = max(ranked, key=lambda row: float(row.get("win_probability") or 0)) if ranked else None
render_section("TOP RECOMMENDATION", "最も勝率が高い予想")
if best:
    left, mid, right = st.columns([1.6, 1, 1])
    left.markdown(f"## {best.get('pick', '-')}")
    left.caption(f"{best.get('home', '-')} vs {best.get('away', '-')} / 予想スコア {best.get('predicted_score', '-')}")
    mid.metric("推定勝率", f"{best.get('win_probability', '-')}%")
    right.metric("信頼度", best.get("confidence", "-"))
else:
    st.info("予想生成後に最上位予想を表示します。")

st.caption("※勝率・予想スコアはAI予測値であり、試合結果を保証するものではありません。")
