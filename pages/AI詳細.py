from datetime import date, datetime
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from ai_detail_summary import (
    find_team_prediction,
    hawks_history_summary,
    hawks_probability,
    simulate_hawks_win_probability,
)
from handicap_source import fetch_hawks_handicap
from prediction_metrics import build_prediction_metrics
from studio_theme import (
    apply_studio_theme,
    render_hero,
    render_nav_links,
    render_section,
    render_topbar,
)

JST = ZoneInfo("Asia/Tokyo")
TODAY_JST = datetime.now(JST).date()
REPO_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PROD_DATA_DIR = Path("/app/data")
DATA_DIR = PROD_DATA_DIR if PROD_DATA_DIR.exists() else REPO_DATA_DIR
SHARED_DATA_DIR = Path(
    os.getenv("AI_BASEBALL_SHARED_DATA_DIR", "/app/shared-data")
)

st.set_page_config(
    page_title="AI詳細 | MY AI BASEBALL",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="collapsed",
)
apply_studio_theme()
render_topbar("AI DETAIL")
render_hero(
    "AI詳細ダッシュボード",
    "試合情報・AI予測・公開ハンデ・検証成績を軽量な1画面に集約しました。",
    kicker="AI BASEBALL STUDIO / DEEP ANALYTICS",
    accent="AI詳細",
)
render_nav_links()


@st.cache_data(ttl=60, max_entries=12, show_spinner=False)
def load_json(path_text, fallback):
    try:
        return json.loads(Path(path_text).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


@st.cache_data(ttl=600, max_entries=4, show_spinner=False)
def load_live_handicap(date_value):
    return fetch_hawks_handicap(date_value, timeout=4)


schedule = load_json(str(DATA_DIR / "npb_today.json"), {"games": []})
predictions = load_json(
    str(DATA_DIR / "today_ai_predictions.json"), {"games": []}
)
shared_schedule = load_json(
    str(SHARED_DATA_DIR / "npb_today.json"), {"games": []}
)
shared_predictions = load_json(
    str(SHARED_DATA_DIR / "today_ai_predictions.json"), {"games": []}
)
game = find_team_prediction(schedule, predictions)
if game is None:
    game = find_team_prediction(shared_schedule, shared_predictions)

history = load_json(str(DATA_DIR / "game_history.json"), [])
history_summary = hawks_history_summary(
    history if isinstance(history, list) else []
)
metrics = build_prediction_metrics(
    DATA_DIR,
    SHARED_DATA_DIR if SHARED_DATA_DIR.exists() else None,
)
try:
    handicap_date = date.fromisoformat(str(game.get("date") or ""))
except (AttributeError, ValueError):
    handicap_date = TODAY_JST
handicap = load_live_handicap(handicap_date)
game_opponent = str(game.get("opponent") or "") if game else ""
handicap_matches_game = bool(
    handicap.get("published")
    and (
        not game_opponent
        or str(handicap.get("opponent") or "") == game_opponent
    )
)

game_date = str(game.get("date") or "") if game else ""
if game_date == TODAY_JST.isoformat():
    game_section_title = "本日のホークス試合分析"
elif game_date > TODAY_JST.isoformat():
    game_section_title = "次戦のホークス試合分析"
else:
    game_section_title = "直近保存されたホークス試合分析"
render_section("LATEST GAME DATA", game_section_title)
if game:
    opponent = str(game.get("opponent") or "未定")
    matchup = f"ソフトバンク vs {opponent}"
    schedule_label = (
        f"{game.get('date') or schedule.get('date') or '--'} "
        f"{game.get('time') or '--:--'}｜{game.get('venue') or '会場未定'}"
    )
    st.subheader(matchup)
    st.caption(schedule_label)
else:
    st.info("ホークスの次戦情報を同期中です。履歴と検証成績は確認できます。")

cards = st.container(horizontal=True)
pick = str(game.get("pick") or "生成待ち") if game else "生成待ち"
probability = game.get("win_probability") if game else None
probability_label = (
    f"{float(probability):.1f}%"
    if isinstance(probability, (int, float))
    else "--"
)
cards.metric("AI PICK", pick, probability_label, border=True)
cards.metric(
    "予想スコア",
    str(game.get("predicted_score") or "--") if game else "--",
    border=True,
)
cards.metric(
    "信頼度",
    str(game.get("confidence") or "--") if game else "--",
    border=True,
)
handicap_label = "対象カードなし" if handicap.get("published") else "未掲載"
if handicap_matches_game:
    handicap_label = (
        f"{handicap.get('favored_team') or ''} {handicap.get('token') or ''}"
    ).strip()
cards.metric("公開ハンデ", handicap_label, border=True)

render_section("MODEL PERFORMANCE", "HAWKS AI検証成績")
performance = st.container(horizontal=True)
performance.metric("検証済み", f"{metrics['verified_count']}試合", border=True)
performance.metric("的中", f"{metrics['hits']}試合", border=True)
performance.metric(
    "的中率",
    f"{metrics['hit_rate']:.1f}%" if metrics["hit_rate"] is not None else "--",
    border=True,
)
performance.metric(
    "Brier Score",
    f"{metrics['brier_score']:.4f}"
    if metrics["brier_score"] is not None
    else "--",
    border=True,
)
st.caption(
    "Brier Scoreは予測確率の誤差です。0に近いほど確率予測が正確です。"
)

render_section("RECENT RESULTS", "ホークス直近5試合")
recent_rows = []
for row in history_summary["recent"]:
    recent_rows.append(
        {
            "日付": row.get("date") or "--",
            "対戦相手": row.get("opponent") or "--",
            "球場": row.get("stadium") or "--",
            "スコア": (
                f"{row.get('hawks_score', '-')} - "
                f"{row.get('opponent_score', '-')}"
            ),
            "結果": row.get("result") or "--",
            "試合前AI勝率": row.get("pregame_probability"),
        }
    )
if recent_rows:
    st.dataframe(
        pd.DataFrame(recent_rows),
        hide_index=True,
        column_config={
            "試合前AI勝率": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )
    st.caption(
        f"保存済み {history_summary['played']}試合｜"
        f"{history_summary['wins']}勝 {history_summary['losses']}敗 "
        f"{history_summary['draws']}分"
    )
else:
    st.info("試合履歴を同期中です。")

render_section("LIVE SIMULATOR", "リアルタイム勝率シミュレーター")
st.caption(
    "V8の点差・イニング・アウト・走者補正を独立化した軽量版です。"
    "入力内容は保存されず、BET結果にも影響しません。"
)
simulator_mode = st.segmented_control(
    "分析モード",
    options=["試合前", "試合中"],
    default="試合中",
    key="ai_detail_simulator_mode",
)
base_probability = hawks_probability(game)
if simulator_mode == "試合前":
    published_handicap = (
        float(handicap.get("handicap_score") or 0.0)
        if handicap_matches_game
        else 0.0
    )
    simulator_handicap = st.number_input(
        "開始ハンデ（＋はホークス優位、－は相手優位）",
        min_value=-5.0,
        max_value=5.0,
        value=published_handicap,
        step=0.1,
        key="ai_detail_simulator_handicap",
    )
    simulation = simulate_hawks_win_probability(
        base_probability,
        mode="pregame",
        handicap_score=simulator_handicap,
    )
else:
    score_left, score_right, inning_col = st.columns(3)
    hawks_score = score_left.number_input(
        "ホークス得点",
        min_value=0,
        max_value=30,
        value=0,
        step=1,
        key="ai_detail_hawks_score",
    )
    opponent_score = score_right.number_input(
        "相手得点",
        min_value=0,
        max_value=30,
        value=0,
        step=1,
        key="ai_detail_opponent_score",
    )
    inning = inning_col.slider(
        "現在のイニング",
        min_value=1,
        max_value=9,
        value=1,
        key="ai_detail_inning",
    )
    attack_side = st.segmented_control(
        "現在の攻撃",
        options=["ホークス攻撃中", "相手攻撃中"],
        default="ホークス攻撃中",
        key="ai_detail_attack_side",
    )
    outs = st.segmented_control(
        "アウトカウント",
        options=[0, 1, 2],
        default=0,
        key="ai_detail_outs",
    )
    selected_runners = st.pills(
        "走者状況",
        options=["1塁", "2塁", "3塁"],
        selection_mode="multi",
        key="ai_detail_runners",
    )
    runner_bits = tuple(
        {"1塁": 1, "2塁": 2, "3塁": 4}[runner]
        for runner in (selected_runners or [])
    )
    simulation = simulate_hawks_win_probability(
        base_probability,
        mode="live",
        hawks_score=hawks_score,
        opponent_score=opponent_score,
        inning=inning,
        attack_side=attack_side,
        outs=outs,
        runners=runner_bits,
    )

sim_result, sim_score, sim_wpa = st.columns(3)
sim_result.metric(
    "ホークス勝利予測",
    f"{simulation['final_probability']:.1f}%",
    f"基礎勝率 {simulation['base_probability']:.1f}%",
)
sim_score.metric(
    "点差・ハンデ補正",
    f"{simulation['score_adjustment']:+.1f}%",
)
sim_wpa.metric(
    "走者・アウト補正",
    f"{simulation['wpa_adjustment']:+.1f}%",
)
st.progress(simulation["final_probability"] / 100.0)

render_section("LEGACY ANALYSIS", "従来版の高度分析")
st.caption(
    "移行確認用として従来の全機能も残しています。"
    "通常は上の軽量シミュレーターをご利用ください。"
)
show_legacy = st.toggle(
    "従来版の高度分析を開く",
    value=False,
    key="show_legacy_ai_detail",
)

if show_legacy:
    st.warning(
        "高度分析を読み込んでいます。外部データ取得により数秒かかる場合があります。"
    )
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app_source = app_path.read_text(encoding="utf-8")
    fixed_assignment = "handicap_score = -2.0"
    if fixed_assignment not in app_source:
        st.error("高度分析の読み込み設定を確認できません。")
        st.stop()
    live_handicap_score = (
        float(handicap["handicap_score"])
        if handicap_matches_game
        and handicap.get("handicap_score") is not None
        else 0.0
    )
    app_source = app_source.replace(
        fixed_assignment,
        "handicap_score = live_handicap_score",
        1,
    )
    original_set_page_config = st.set_page_config
    original_file = globals().get("__file__")
    st.set_page_config = lambda *args, **kwargs: None
    globals()["__file__"] = str(app_path)
    try:
        try:
            exec(compile(app_source, str(app_path), "exec"), globals(), globals())
        except Exception as exc:
            st.error(
                "高度分析の一部を読み込めませんでした。"
                "上部のAI分析サマリーは引き続き利用できます。"
            )
            with st.expander("エラー情報"):
                st.code(f"{type(exc).__name__}: {exc}")
    finally:
        st.set_page_config = original_set_page_config
        globals()["__file__"] = original_file
