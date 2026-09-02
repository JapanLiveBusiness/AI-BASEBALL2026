from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import re

import requests
import streamlit as st
from bs4 import BeautifulSoup

from bet_analytics import classify_result
from studio_theme import apply_studio_theme, render_topbar, render_hero, render_nav_links

JST = ZoneInfo("Asia/Tokyo")
REPO_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PROD_DATA_DIR = Path("/app/data")
DATA_DIR = PROD_DATA_DIR if PROD_DATA_DIR.exists() else REPO_DATA_DIR
SIM_FILE = DATA_DIR / "bet_records.json"
TEAM_NAMES = [
    "ソフトバンク", "日本ハム", "楽天", "西武", "ロッテ", "オリックス",
    "巨人", "阪神", "DeNA", "広島", "ヤクルト", "中日",
]

st.set_page_config(page_title="シミュレーション入力 | MY AI BASEBALL", page_icon="🧪", layout="wide")
apply_studio_theme()
render_topbar("SIMULATION LAB")
render_hero(
    "ハンデ仮説シミュレーション",
    "実際の試合カードに仮想ハンデと仮想ポイントを設定し、予測仮説の精度を検証します。実際の賭けや金銭取引には接続しません。",
    kicker="AI BASEBALL STUDIO / HYPOTHESIS TEST",
    accent="SIM",
)
render_nav_links()


def load_records():
    try:
        value = json.loads(SIM_FILE.read_text(encoding="utf-8"))
        return value if isinstance(value, list) else []
    except Exception:
        return []


def save_records(records):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SIM_FILE.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


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
    st.info("指定日の試合を自動取得できませんでした。対戦カードを手動入力できます。")
    team_options = []
    default_time = "18:00"

with st.form("simulation_form"):
    c1, c2 = st.columns(2)
    if team_options:
        subject_team = c1.selectbox("検証対象チーム", team_options)
        opponent = team_options[1] if subject_team == team_options[0] else team_options[0]
        c2.text_input("対戦相手", value=opponent, disabled=True)
    else:
        subject_team = c1.text_input("検証対象チーム")
        opponent = c2.text_input("対戦相手")

    try:
        time_value = datetime.strptime(default_time, "%H:%M").time()
    except ValueError:
        time_value = datetime.strptime("18:00", "%H:%M").time()

    c3, c4, c5 = st.columns(3)
    game_time = c3.time_input("開始時刻", value=time_value)
    simulation_points = c4.number_input("仮想投入ポイント", min_value=0, value=100, step=10)
    handicap = c5.number_input("仮想ハンデ", value=0.0, step=0.1)

    c6, c7 = st.columns(2)
    status_label = c6.selectbox("状態", ["未確定", "確定"])
    predicted_result = c7.selectbox("事前仮説", ["対象チーム側", "相手側", "引き分け相当"])

    c8, c9 = st.columns(2)
    team_score = c8.number_input("対象チーム得点", min_value=0, value=0, step=1)
    opponent_score = c9.number_input("対戦相手得点", min_value=0, value=0, step=1)
    memo = st.text_area("仮説メモ", placeholder="予測根拠、モデル条件、注目指標など")
    submitted = st.form_submit_button("シミュレーションを保存", type="primary", use_container_width=True)

if submitted:
    if not str(subject_team).strip() or not str(opponent).strip():
        st.error("検証対象チームと対戦相手を入力してください。")
    else:
        actual_result = None
        point_delta = 0.0
        if status_label == "確定":
            actual_result = classify_result(team_score, opponent_score, handicap)
            if actual_result == "win":
                point_delta = float(simulation_points)
            elif actual_result == "loss":
                point_delta = -float(simulation_points)

        records = load_records()
        created_at = datetime.now(JST)
        records.append({
            "id": f"sim-{created_at.strftime('%Y%m%d%H%M%S%f')}",
            "date": selected_date.isoformat(),
            "time": game_time.strftime("%H:%M"),
            "team": str(subject_team).strip(),
            "opponent": str(opponent).strip(),
            "handicap": float(handicap),
            "simulation_points": int(simulation_points),
            "status": "final" if status_label == "確定" else "pending",
            "predicted_result": predicted_result,
            "result": actual_result,
            "point_delta": point_delta,
            "team_score": int(team_score) if status_label == "確定" else None,
            "opponent_score": int(opponent_score) if status_label == "確定" else None,
            "memo": memo.strip(),
            "source": "simulation-page",
            "created_at": created_at.isoformat(timespec="seconds"),
        })
        save_records(records)
        st.success("仮説シミュレーションを保存しました。結果画面で命中率と累積ポイントを確認できます。")