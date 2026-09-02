from pathlib import Path
import json

import plotly.graph_objects as go
import streamlit as st

from bet_analytics import SORT_OPTIONS, calculate_hit_rate, point_delta, simulation_points, sort_bets
from studio_theme import apply_studio_theme, render_topbar, render_hero, render_nav_links, render_section

st.set_page_config(page_title="感度分析結果 | AI BASEBALL RESEARCH", page_icon="📊", layout="wide")
apply_studio_theme()
render_topbar("SENSITIVITY RESULTS")
render_hero(
    "得点補正・感度分析結果",
    "得点補正値ごとの成立率、評価スコア差、累積推移を可視化する研究用ダッシュボードです。",
    kicker="AI BASEBALL STUDIO / SENSITIVITY",
    accent="分析",
)
render_nav_links()

REPO_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PROD_DATA_DIR = Path("/app/data")
DATA_DIR = PROD_DATA_DIR if PROD_DATA_DIR.exists() else REPO_DATA_DIR
SIM_FILE = DATA_DIR / "simulation_records.json"
LEGACY_FILE = DATA_DIR / "bet_records.json"


def _read_list(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _legacy_to_analysis(record):
    try:
        weight = abs(float(record.get("bet_units") or 0))
    except (TypeError, ValueError):
        weight = 0.0
    result = record.get("result")
    delta = weight if result == "win" else (-weight if result == "loss" else 0.0)
    return {
        "id": f"legacy-{record.get('date','')}-{record.get('time','')}-{record.get('team','')}-{record.get('opponent','')}",
        "date": record.get("date"),
        "time": record.get("time"),
        "team": record.get("team"),
        "opponent": record.get("opponent"),
        "handicap": record.get("handicap", 0),
        "simulation_points": weight,
        "status": record.get("status", "pending"),
        "result": result,
        "point_delta": delta,
        "team_score": record.get("team_score"),
        "opponent_score": record.get("opponent_score"),
        "predicted_result": record.get("predicted_result"),
        "memo": record.get("memo", ""),
        "source": "legacy-research-history",
    }


def load_records():
    current = _read_list(SIM_FILE)
    legacy = [_legacy_to_analysis(r) for r in _read_list(LEGACY_FILE)]

    merged = []
    seen = set()
    for record in legacy + current:
        key = (
            str(record.get("date", "")),
            str(record.get("time", "")),
            str(record.get("team", "")),
            str(record.get("opponent", "")),
            str(record.get("handicap", "")),
        )
        if key in seen:
            continue
        seen.add(key)
        merged.append(record)
    return merged


def result_label(value):
    return {"win": "仮説成立", "loss": "仮説不成立", "push": "境界"}.get(value, "未確定")


records = load_records()
if not records:
    st.info("分析シナリオがまだありません。入力画面から最初の仮説を登録できます。")
    st.stop()

records = sort_bets(records, "古い日付順")
settled = [r for r in records if r.get("status") == "final"]
pending = [r for r in records if r.get("status") != "final"]

sort_option = st.selectbox("履歴の並び順", SORT_OPTIONS, key="simulation_sort")
sorted_settled = sort_bets(settled, sort_option)
sorted_pending = sort_bets(pending, sort_option)

if settled:
    successes = sum(1 for r in settled if r.get("result") == "win")
    failures = sum(1 for r in settled if r.get("result") == "loss")
    boundaries = sum(1 for r in settled if r.get("result") == "push")
    total_delta = sum(point_delta(r) for r in settled)
    total_weight = sum(simulation_points(r) for r in settled)
    _, decided, hit_rate = calculate_hit_rate(settled)
    efficiency = (total_delta / total_weight * 100.0) if total_weight else 0.0

    render_section("PERFORMANCE", "分析サマリー")
    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("累積評価スコア差", f"{total_delta:+.0f}")
    s2.metric("確定シナリオ", f"{len(settled)}試合")
    s3.metric("成立 / 不成立", f"{successes} / {failures}" + (f" / {boundaries}" if boundaries else ""))
    s4.metric("成立率", f"{hit_rate:.1f}%" if hit_rate is not None else "-")
    s5.metric("評価効率", f"{efficiency:+.1f}%" if total_weight else "-")

    running = 0.0
    x_values, y_values, hover_values = [], [], []
    for record in settled:
        delta = point_delta(record)
        running += delta
        date_value = str(record.get("date", "-"))
        time_value = str(record.get("time", "-"))
        team_name = str(record.get("team", "-"))
        opponent_name = str(record.get("opponent", "-"))
        weight = simulation_points(record)
        team_score = record.get("team_score")
        opponent_score = record.get("opponent_score")
        score = f"{team_score} - {opponent_score}" if team_score is not None and opponent_score is not None else "未確定"
        x_values.append(f"{date_value} {time_value}")
        y_values.append(running)
        hover_values.append(
            f"<b>{team_name} vs {opponent_name}</b><br>日時: {date_value} {time_value}"
            f"<br>得点補正値: {record.get('handicap', 0)}<br>評価ウェイト: {weight:.0f}"
            f"<br>スコア: {score}<br>判定: {result_label(record.get('result'))}"
            f"<br>評価スコア差: {delta:+.0f}<br><b>累積: {running:+.0f}</b>"
        )

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_values,
        y=y_values,
        mode="lines+markers",
        customdata=hover_values,
        hovertemplate="%{customdata}<extra></extra>",
        name="累積評価スコア差",
    ))
    fig.add_hline(y=0, line_dash="dash", line_width=1)
    fig.update_layout(
        xaxis_title="検証した試合",
        yaxis_title="累積評価スコア差",
        hovermode="closest",
        height=500,
        margin=dict(l=20, r=20, t=30, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#c7ccd4"),
    )
    st.plotly_chart(fig, use_container_width=True)

    render_section("ADJUSTMENT", "得点補正値別の検証")
    buckets = {}
    for record in settled:
        adjustment = float(record.get("handicap", 0) or 0)
        key = f"{adjustment:+.1f}"
        buckets.setdefault(key, []).append(record)

    rows = []
    for adjustment_key, items in sorted(buckets.items(), key=lambda x: float(x[0])):
        _, decided_count, rate = calculate_hit_rate(items)
        rows.append({
            "得点補正値": adjustment_key,
            "試合数": len(items),
            "判定対象": decided_count,
            "成立率": round(rate, 1) if rate is not None else None,
            "評価スコア差": round(sum(point_delta(i) for i in items), 1),
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)

    render_section("HISTORY", "検証履歴")
    for record in sorted_settled:
        delta = point_delta(record)
        weight = simulation_points(record)
        team_name = str(record.get("team", "-"))
        opponent_name = str(record.get("opponent", "-"))
        title = f"{record.get('date', '-')} {record.get('time', '-')} | {team_name} vs {opponent_name} | {delta:+.0f}"
        with st.expander(title):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("検証対象", team_name)
            c2.metric("評価ウェイト", f"{weight:.0f}")
            c3.metric("得点補正値", str(record.get("handicap", 0)))
            c4.metric("評価スコア差", f"{delta:+.0f}")
            st.write(f"**判定:** {result_label(record.get('result'))}")
            if record.get("predicted_result"):
                st.write(f"**事前仮説:** {record.get('predicted_result')}")
            if record.get("memo"):
                st.write(f"**メモ:** {record['memo']}")
else:
    st.info("確定済み分析シナリオはまだありません。")

if pending:
    render_section("PENDING", "未確定シナリオ")
    for record in sorted_pending:
        weight = simulation_points(record)
        st.write(
            f"⏳ {record.get('date', '-')} {record.get('time', '-')} ｜ "
            f"{record.get('team', '-')} vs {record.get('opponent', '-')} ｜ "
            f"評価ウェイト {weight:.0f} ｜ 得点補正値 {record.get('handicap', 0)}"
        )
