from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import re

import requests
import streamlit as st
from bs4 import BeautifulSoup

from bet_analytics import profit_for_result, settle_bet
from bet_store import BetStoreError, append_bet
from studio_theme import apply_studio_theme, render_topbar, render_hero, render_nav_links

JST = ZoneInfo("Asia/Tokyo")
REPO_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PROD_DATA_DIR = Path("/app/data")
DATA_DIR = PROD_DATA_DIR if PROD_DATA_DIR.exists() else REPO_DATA_DIR
BETS_FILE = DATA_DIR / "bet_records.json"
TEAM_NAMES = [
    "ソフトバンク", "日本ハム", "楽天", "西武", "ロッテ", "オリックス",
    "巨人", "阪神", "DeNA", "広島", "ヤクルト", "中日",
]

st.set_page_config(page_title="BET入力 | MY AI BASEBALL", page_icon="✍️", layout="wide")
apply_studio_theme()
render_topbar("BET MANAGEMENT")
render_hero(
    "BET・収支入力",
    "当日のNPBカードからBET先・ハンデ・金額・結果を登録し、収支マップへ即時反映します。",
    kicker="AI BASEBALL STUDIO / BET INPUT",
    accent="BET",
)
render_nav_links()


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_npb_games(selected_date):
    year, month = selected_date.year, selected_date.month
    target_md = f"{selected_date.month}/{selected_date.day}"
    url = f"https://npb.jp/games/{year}/schedule_{month:02d}_detail.html"
    games = []
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser")
        current_date = None
        for tr in soup.find_all("tr"):
            text = " ".join(tr.get_text(" ", strip=True).split())
            dm = re.search(r"(\d{1,2})/(\d{1,2})", text)
            if dm:
                current_date = f"{int(dm.group(1))}/{int(dm.group(2))}"
            if current_date != target_md:
                continue
            found = []
            for team in TEAM_NAMES:
                if team in text and team not in found:
                    found.append(team)
            if len(found) < 2:
                continue
            tm = re.search(r"(\d{1,2}:\d{2})", text)
            pair = {"team1": found[0], "team2": found[1], "time": tm.group(1) if tm else "18:00"}
            if pair not in games:
                games.append(pair)
    except Exception:
        pass
    return games


selected_date = st.date_input("試合日", value=datetime.now(JST).date())
games = fetch_npb_games(selected_date)

if games:
    labels = [f"{g['team1']} vs {g['team2']}（{g['time']}）" for g in games]
    selected_label = st.selectbox("当日の開催試合", labels)
    game = games[labels.index(selected_label)]
    team_options = [game["team1"], game["team2"]]
    default_time = game["time"]
else:
    st.info("指定日の試合を自動取得できませんでした。チーム名を手動入力できます。")
    team_options = []
    default_time = "18:00"

with st.form("manual_bet_form"):
    c1, c2 = st.columns(2)
    if team_options:
        bet_team = c1.selectbox("BET先", team_options)
        opponent = team_options[1] if bet_team == team_options[0] else team_options[0]
        c2.text_input("対戦相手", value=opponent, disabled=True)
    else:
        bet_team = c1.text_input("BET先 / チーム")
        opponent = c2.text_input("対戦相手")

    try:
        time_value = datetime.strptime(default_time, "%H:%M").time()
    except ValueError:
        time_value = datetime.strptime("18:00", "%H:%M").time()

    c3, c4, c5 = st.columns(3)
    game_time = c3.time_input("開始時刻", value=time_value)
    bet_amount = c4.number_input("BET金額（円）", min_value=0, value=10000, step=1000)
    handicap = c5.number_input("ハンディ", value=0.0, step=0.1)

    status_label = st.selectbox("状態", ["未確定", "確定"])
    st.caption("確定時は、BET先得点からハンディを差し引いて結果と損益を自動計算します。")

    c9, c10 = st.columns(2)
    team_score = c9.number_input("BET先チーム得点", min_value=0, value=0, step=1)
    opponent_score = c10.number_input("対戦相手得点", min_value=0, value=0, step=1)
    memo = st.text_area("その他情報", placeholder="オッズ、BET理由、ブックメーカー、補足など")
    submitted = st.form_submit_button("BET・収支を保存", type="primary", width="stretch")

if submitted:
    if not str(bet_team).strip() or not str(opponent).strip():
        st.error("BET先と対戦相手を入力してください。")
    else:
        is_final = status_label == "確定"
        adjusted_score, result = (
            settle_bet(team_score, opponent_score, handicap)
            if is_final
            else (None, None)
        )
        calculated_profit = profit_for_result(result, bet_amount) if is_final else 0
        created_at = datetime.now(JST)
        record = {
            "id": f"manual-{created_at.strftime('%Y%m%d%H%M%S%f')}",
            "date": selected_date.isoformat(),
            "time": game_time.strftime("%H:%M"),
            "team": str(bet_team).strip(),
            "opponent": str(opponent).strip(),
            "handicap": float(handicap),
            "bet_units": float(bet_amount) / 10000.0,
            "bet_amount": int(bet_amount),
            "status": "final" if is_final else "pending",
            "settled": is_final,
            "result": result,
            "profit": calculated_profit,
            "team_score": int(team_score) if is_final else None,
            "opponent_score": int(opponent_score) if is_final else None,
            "adjusted_score": adjusted_score,
            "memo": memo.strip(),
            "source": "manual-page",
            "created_at": created_at.isoformat(timespec="seconds"),
        }
        try:
            append_bet(BETS_FILE, record)
        except BetStoreError as exc:
            st.error(str(exc))
        else:
            if is_final:
                st.success(f"ハンデ込みで {result.upper()}、損益 {calculated_profit:+,}円として保存しました。")
            else:
                st.success("未確定BETを保存しました。収支マップにも反映されます。")
