from pathlib import Path
import json

import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="収支マップ | HAWKS AI", page_icon="💰", layout="wide")

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
BETS_FILE = DATA_DIR / "bet_records.json"


def load_bets():
    try:
        data = json.loads(BETS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def yen(value):
    try:
        return f"¥{int(value):,}"
    except (TypeError, ValueError):
        return "-"


def result_label(value):
    return {
        "win": "WIN",
        "loss": "LOSE",
        "push": "PUSH",
    }.get(value, "未確定")


st.title("💰 収支マップ")
st.caption("各ポイントにカーソルを合わせると、BETした試合・ハンディ・BET額・スコア・損益を確認できます。")

bets = load_bets()

if not bets:
    st.info("BET記録がまだありません。")
    st.stop()

bets = sorted(
    bets,
    key=lambda b: (str(b.get("date", "")), str(b.get("time", ""))),
)

settled = [b for b in bets if b.get("status") == "final"]

if not settled:
    st.info("確定済みのBETがまだありません。")
    st.stop()

running = 0
x_values = []
y_values = []
hover_values = []

for bet in settled:
    profit = int(bet.get("profit", 0) or 0)
    running += profit

    date = str(bet.get("date", "-"))
    time = str(bet.get("time", "-"))
    team = str(bet.get("team", "-"))
    opponent = str(bet.get("opponent", "-"))
    handicap = bet.get("handicap", 0)
    units = float(bet.get("bet_units", 0) or 0)
    amount = abs(units) * 10000
    team_score = bet.get("team_score")
    opponent_score = bet.get("opponent_score")
    score = (
        f"{team_score} - {opponent_score}"
        if team_score is not None and opponent_score is not None
        else "未確定"
    )

    x_values.append(f"{date} {time}")
    y_values.append(running)
    hover_values.append(
        "<b>" + team + " vs " + opponent + "</b>"
        + "<br>日時: " + date + " " + time
        + "<br>BET先: " + team
        + "<br>ハンディ: " + str(handicap)
        + "<br>BET額: " + yen(amount)
        + "<br>スコア: " + score
        + "<br>結果: " + result_label(bet.get("result"))
        + "<br>この試合の損益: " + yen(profit)
        + "<br><b>累積収支: " + yen(running) + "</b>"
    )

fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=x_values,
        y=y_values,
        mode="lines+markers",
        customdata=hover_values,
        hovertemplate="%{customdata}<extra></extra>",
        name="累積収支",
    )
)
fig.add_hline(y=0, line_dash="dash", line_width=1)
fig.update_layout(
    xaxis_title="BETした試合",
    yaxis_title="累積収支（円）",
    hovermode="closest",
    height=500,
    margin=dict(l=20, r=20, t=30, b=30),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)
fig.update_yaxes(tickformat=",")

st.plotly_chart(fig, use_container_width=True)

st.markdown("### BETした試合の詳細")

for bet in reversed(settled):
    profit = int(bet.get("profit", 0) or 0)
    units = float(bet.get("bet_units", 0) or 0)
    amount = abs(units) * 10000
    team = str(bet.get("team", "-"))
    opponent = str(bet.get("opponent", "-"))
    team_score = bet.get("team_score")
    opponent_score = bet.get("opponent_score")
    score = (
        f"{team_score} - {opponent_score}"
        if team_score is not None and opponent_score is not None
        else "未確定"
    )
    icon = "🟢" if profit > 0 else ("🔴" if profit < 0 else "⚪")
    title = (
        f"{icon} {bet.get('date', '-')} {bet.get('time', '-')} | "
        f"{team} vs {opponent} | {yen(profit)}"
    )

    with st.expander(title):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("BET先", team)
        c2.metric("BET額", yen(amount))
        c3.metric("ハンディ", str(bet.get("handicap", 0)))
        c4.metric("損益", yen(profit))
        st.write(
            f"**試合スコア:** {score}　｜　"
            f"**結果:** {result_label(bet.get('result'))}"
        )

pending = [b for b in bets if b.get("status") != "final"]
if pending:
    st.markdown("### 未確定BET")
    for bet in reversed(pending):
        st.write(
            f"⏳ {bet.get('date', '-')} {bet.get('time', '-')} ｜ "
            f"{bet.get('team', '-')} vs {bet.get('opponent', '-')} ｜ "
            f"BET {yen(abs(float(bet.get('bet_units', 0) or 0)) * 10000)} ｜ "
            f"ハンディ {bet.get('handicap', 0)}"
        )
