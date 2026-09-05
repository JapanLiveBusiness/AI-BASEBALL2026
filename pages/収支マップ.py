from pathlib import Path
from datetime import date, datetime
from zoneinfo import ZoneInfo

import plotly.graph_objects as go
import streamlit as st

from auth_session import user_bets_path
from bet_analytics import (
    SORT_OPTIONS,
    calculate_hit_rate,
    profit_for_record,
    profit_for_result,
    settle_bet,
    sort_bets,
    weekly_bet_summary,
)
from bet_store import BetStoreError, append_bet, delete_bet, import_bets, load_bets, update_bet
from bet_transfer import BetSpreadsheetError, bets_to_xlsx, read_bet_spreadsheet
from game_calendar import load_npb_schedule_day
from studio_theme import apply_studio_theme, render_topbar, render_hero, render_nav_links, render_section

st.set_page_config(page_title="収支マップ | MY AI BASEBALL", page_icon="💰", layout="wide")
apply_studio_theme()
auth_user = render_topbar("PROFIT MAP")
render_hero(
    "収支マップ",
    "BET履歴・的中率・ROI・累積収支をまとめて可視化。登録済みのBET機能は維持したままStudioデザインへ統合しています。",
    kicker="AI BASEBALL STUDIO / PERFORMANCE",
    accent="収支",
)
render_nav_links()

REPO_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PROD_DATA_DIR = Path("/app/data")
DATA_DIR = PROD_DATA_DIR if PROD_DATA_DIR.exists() else REPO_DATA_DIR
BETS_FILE = user_bets_path(DATA_DIR, auth_user)
NPB_API = "https://npb.jp/bis/eng/2026/games/"
JST = ZoneInfo("Asia/Tokyo")
SCHEDULE_CACHE_PATHS = (
    Path("/app/shared-data/npb_today.json"),
    DATA_DIR / "npb_today.json",
    DATA_DIR / "npb_schedule_cache.json",
    REPO_DATA_DIR.parent / "npb_schedule_fallback.json",
)


def yen(value):
    try:
        return f"¥{int(value):,}"
    except (TypeError, ValueError):
        return "-"


def result_label(value):
    return {"win": "WIN", "loss": "LOSE", "push": "PUSH"}.get(value, "未確定")


def _record_date(value):
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return date.today()


def _record_time(value):
    try:
        return datetime.strptime(str(value), "%H:%M").time()
    except ValueError:
        return datetime.strptime("18:00", "%H:%M").time()


@st.dialog("BETを編集", width="large")
def edit_bet_dialog(bet):
    record_id = bet["id"]
    with st.form(f"edit_bet_{record_id}"):
        c1, c2 = st.columns(2)
        selected_date = c1.date_input("試合日", value=_record_date(bet.get("date")))
        game_time = c2.time_input("開始時刻", value=_record_time(bet.get("time")))
        c3, c4 = st.columns(2)
        team = c3.text_input("BET先", value=str(bet.get("team", "")))
        opponent = c4.text_input("対戦相手", value=str(bet.get("opponent", "")))
        c5, c6 = st.columns(2)
        amount = c5.number_input("BET金額（円）", min_value=0, step=1000, value=int(abs(float(bet.get("bet_amount", 0) or float(bet.get("bet_units", 0) or 0) * 10000))))
        handicap = c6.number_input("ハンディ", step=0.1, value=float(bet.get("handicap", 0) or 0))
        status_label = st.selectbox("状態", ["未確定", "確定"], index=1 if bet.get("status") == "final" else 0)
        c7, c8 = st.columns(2)
        team_score = c7.number_input("BET先チーム得点", min_value=0, step=1, value=int(bet.get("team_score") or 0))
        opponent_score = c8.number_input("対戦相手得点", min_value=0, step=1, value=int(bet.get("opponent_score") or 0))
        memo = st.text_area("メモ / その他情報", value=str(bet.get("memo", "")))
        submitted = st.form_submit_button("変更を保存", type="primary", width="stretch")

    if not submitted:
        return
    if not team.strip() or not opponent.strip():
        st.error("BET先と対戦相手を入力してください。")
        return

    is_final = status_label == "確定"
    adjusted_score, result = settle_bet(team_score, opponent_score, handicap) if is_final else (None, None)
    changes = {
        "date": selected_date.isoformat(),
        "time": game_time.strftime("%H:%M"),
        "team": team.strip(),
        "opponent": opponent.strip(),
        "handicap": float(handicap),
        "bet_units": float(amount) / 10000.0,
        "bet_amount": int(amount),
        "status": "final" if is_final else "pending",
        "settled": is_final,
        "result": result,
        "profit": profit_for_result(result, amount) if is_final else 0,
        "team_score": int(team_score) if is_final else None,
        "opponent_score": int(opponent_score) if is_final else None,
        "adjusted_score": adjusted_score,
        "memo": memo.strip(),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    try:
        update_bet(BETS_FILE, record_id, changes)
    except BetStoreError as exc:
        st.error(str(exc))
    else:
        st.session_state["bet_notice"] = "BETを更新しました。"
        st.rerun()


@st.dialog("BETを削除")
def delete_bet_dialog(bet):
    st.warning("この操作は元に戻せません。")
    st.write(f"{bet.get('date', '-')} {bet.get('time', '-')} ｜ {bet.get('team', '-')} vs {bet.get('opponent', '-')}")
    if st.button("このBETを削除", type="primary", width="stretch", key=f"confirm_delete_{bet['id']}"):
        try:
            delete_bet(BETS_FILE, bet["id"])
        except BetStoreError as exc:
            st.error(str(exc))
        else:
            st.session_state["bet_notice"] = "BETを削除しました。"
            st.rerun()


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_games(selected_date):
    return load_npb_schedule_day(
        selected_date,
        SCHEDULE_CACHE_PATHS,
        timeout=6,
    )


render_section("ENTRY", "当日のBET・収支を入力")
with st.expander("➕ 当日のBET・収支を手動入力", expanded=True):
    selected_date = st.date_input(
        "試合日",
        value=datetime.now(JST).date(),
        key="manual_bet_date",
    )
    games = fetch_games(selected_date)

    if games:
        game_labels = [f"{g['home']} vs {g['away']}" + (f" ({g['time']})" if g.get('time') else "") for g in games]
        game_choice = st.selectbox("開催試合", game_labels)
        selected_game = games[game_labels.index(game_choice)]
        default_team = selected_game["home"]
        default_opponent = selected_game["away"]
        default_time = selected_game.get("time") or "18:00"
        st.caption("選択した日付のNPB開催試合から選択できます。")
    else:
        st.info("この日付の開催試合を自動取得できませんでした。対戦カードを手動入力できます。")
        default_team = ""
        default_opponent = ""
        default_time = "18:00"

    try:
        default_game_time = datetime.strptime(default_time, "%H:%M").time()
    except ValueError:
        default_game_time = datetime.strptime("18:00", "%H:%M").time()

    with st.form("manual_bet_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        team = c1.text_input("BET先 / チーム", value=default_team)
        opponent = c2.text_input("対戦相手", value=default_opponent)

        c3, c4, c5 = st.columns(3)
        game_time = c3.time_input("試合開始時刻", value=default_game_time)
        bet_amount = c4.number_input("BET金額（円）", min_value=0, step=1000, value=10000)
        handicap = c5.number_input("ハンディ", step=0.1, value=0.0)

        status_label = st.selectbox("状態", ["未確定", "確定"])
        st.caption(
            "確定時は、BET先得点からハンディを差し引いて結果を判定します。"
            "損益は的中 +BET額の90%、外れ -BET額の100%、PUSH 0円です。"
        )

        c9, c10 = st.columns(2)
        team_score = c9.number_input("BET先チーム得点", min_value=0, step=1, value=0)
        opponent_score = c10.number_input("対戦相手得点", min_value=0, step=1, value=0)
        memo = st.text_area("メモ / その他情報", placeholder="オッズ、BET理由、ブックメーカー、補足など")

        submitted = st.form_submit_button("このBET・収支を保存", type="primary", width="stretch")

    if submitted:
        if not team.strip() or not opponent.strip():
            st.error("BET先と対戦相手を入力してください。")
        else:
            is_final = status_label == "確定"
            adjusted_score, result = (
                settle_bet(team_score, opponent_score, handicap)
                if is_final
                else (None, None)
            )
            calculated_profit = profit_for_result(result, bet_amount) if is_final else 0
            record = {
                "id": f"manual-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                "date": selected_date.isoformat(),
                "time": game_time.strftime("%H:%M"),
                "team": team.strip(),
                "opponent": opponent.strip(),
                "handicap": handicap,
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
                "source": "manual",
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
            try:
                append_bet(BETS_FILE, record)
            except BetStoreError as exc:
                st.error(str(exc))
            else:
                if is_final:
                    st.session_state["bet_notice"] = f"ハンデ込みで {result.upper()}、損益 {calculated_profit:+,}円として保存しました。"
                else:
                    st.session_state["bet_notice"] = f"{selected_date.isoformat()} {team} vs {opponent} の未確定BETを保存しました。"
                st.rerun()

if notice := st.session_state.pop("bet_notice", None):
    st.success(notice)

try:
    bets = load_bets(BETS_FILE)
except BetStoreError as exc:
    st.error(str(exc))
    st.stop()

render_section("SPREADSHEET", "BET履歴のエクスポート・インポート")
with st.container(border=True):
    st.caption(
        "現在ログイン中の利用者の履歴だけをExcelへ出力します。"
        "取込時は日付・金額・スコアを検証し、損益を90%ルールで再計算します。"
    )
    if bets:
        st.download_button(
            "Excelでエクスポート",
            data=bets_to_xlsx(bets),
            file_name=f"bet_history_{datetime.now(JST).strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            icon=":material/download:",
            width="stretch",
        )
    else:
        st.caption("エクスポートできるBET履歴はまだありません。")

    uploaded_history = st.file_uploader(
        "BET履歴ファイル",
        type=["xlsx", "csv"],
        key="bet_history_import",
        help="この画面から出力したExcel、または同じ列構成のCSVを選択できます。",
        max_upload_size=5,
    )
    if uploaded_history is not None:
        try:
            imported_records = read_bet_spreadsheet(
                uploaded_history.getvalue(),
                uploaded_history.name,
            )
        except BetSpreadsheetError as exc:
            st.error(str(exc))
        else:
            st.success(f"{len(imported_records):,}件を検証しました。")
            import_mode = st.segmented_control(
                "取込方法",
                ["重複を除いて追加", "現在の履歴を置換"],
                default="重複を除いて追加",
                key="bet_import_mode",
                width="stretch",
            )
            replacing = import_mode == "現在の履歴を置換"
            replacement_confirmed = True
            if replacing:
                replacement_confirmed = st.checkbox(
                    "現在の履歴をすべて置き換えることを確認しました",
                    key="bet_replace_confirm",
                )
                st.warning("置換すると、現在ログイン中の利用者の既存履歴が新しい内容に置き換わります。")
            if st.button(
                "検証済み履歴をインポート",
                type="primary",
                icon=":material/upload:",
                disabled=not replacement_confirmed,
                width="stretch",
            ):
                try:
                    _, imported_count = import_bets(
                        BETS_FILE,
                        imported_records,
                        replace=replacing,
                    )
                except BetStoreError as exc:
                    st.error(str(exc))
                else:
                    action = "置換" if replacing else "追加"
                    st.session_state["bet_notice"] = (
                        f"BET履歴を{action}しました（反映 {imported_count:,}件）。"
                    )
                    st.rerun()
if not bets:
    st.info("BET記録がまだありません。上のフォームから最初のBETを登録できます。")
    st.stop()

bets = sort_bets(bets, "古い日付順")
settled = [b for b in bets if b.get("status") == "final"]
pending = [b for b in bets if b.get("status") != "final"]

weekly = weekly_bet_summary(bets, datetime.now(JST).date())
render_section("WEEKLY P/L", "今週の収支")
st.caption(
    f"対象期間: {weekly['week_start'].strftime('%Y/%m/%d')}〜"
    f"{weekly['week_end'].strftime('%Y/%m/%d')}（日本時間・月曜始まり）"
)
w1, w2, w3, w4, w5 = st.columns(5)
w1.metric("週次確定損益", yen(weekly["profit"]))
w2.metric("確定BET", f"{weekly['final_count']}試合")
w3.metric(
    "勝敗",
    f"{weekly['wins']}勝 {weekly['losses']}敗"
    + (f" {weekly['pushes']}分" if weekly["pushes"] else ""),
)
w4.metric(
    "週次ROI",
    f"{weekly['roi']:+.1f}%" if weekly["roi"] is not None else "-",
)
w5.metric(
    "未確定BET",
    yen(weekly["pending_amount"]),
    f"{weekly['pending_count']}試合",
    delta_color="off",
)

sort_option = st.selectbox("履歴の並び順", SORT_OPTIONS, key="profit_map_sort")
sorted_settled = sort_bets(settled, sort_option)
sorted_pending = sort_bets(pending, sort_option)

if settled:
    wins = sum(1 for b in settled if b.get("result") == "win")
    losses = sum(1 for b in settled if b.get("result") == "loss")
    pushes = sum(1 for b in settled if b.get("result") == "push")
    total_profit = sum(profit_for_record(b) for b in settled)
    total_bet = sum(float(b.get("bet_amount", abs(float(b.get("bet_units", 0) or 0)) * 10000) or 0) for b in settled)
    _, decided, hit_rate = calculate_hit_rate(settled)
    roi = (total_profit / total_bet * 100.0) if total_bet else 0.0

    render_section("PERFORMANCE", "収支サマリー")
    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("総収支", yen(total_profit))
    s2.metric("確定BET", f"{len(settled)}試合")
    s3.metric("勝敗", f"{wins}勝 {losses}敗" + (f" {pushes}分" if pushes else ""))
    s4.metric("的中率", f"{hit_rate:.1f}%" if hit_rate is not None else "-")
    s5.metric("ROI", f"{roi:+.1f}%" if total_bet else "-")

    running = 0
    x_values, y_values, hover_values = [], [], []
    for bet in settled:
        profit_value = profit_for_record(bet)
        running += profit_value
        bet_date, bet_time = str(bet.get("date", "-")), str(bet.get("time", "-"))
        team_name, opponent_name = str(bet.get("team", "-")), str(bet.get("opponent", "-"))
        amount = float(bet.get("bet_amount", abs(float(bet.get("bet_units", 0) or 0)) * 10000) or 0)
        team_score_value, opponent_score_value = bet.get("team_score"), bet.get("opponent_score")
        score = f"{team_score_value} - {opponent_score_value}" if team_score_value is not None and opponent_score_value is not None else "未確定"
        x_values.append(f"{bet_date} {bet_time}")
        y_values.append(running)
        hover_values.append(
            f"<b>{team_name} vs {opponent_name}</b><br>日時: {bet_date} {bet_time}<br>BET先: {team_name}"
            f"<br>ハンディ: {bet.get('handicap', 0)}<br>BET額: {yen(amount)}<br>スコア: {score}"
            f"<br>結果: {result_label(bet.get('result'))}<br>この試合の損益: {yen(profit_value)}"
            f"<br><b>累積収支: {yen(running)}</b>"
        )

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x_values, y=y_values, mode="lines+markers", customdata=hover_values,
                             hovertemplate="%{customdata}<extra></extra>", name="累積収支"))
    fig.add_hline(y=0, line_dash="dash", line_width=1)
    fig.update_layout(xaxis_title="BETした試合", yaxis_title="累積収支（円）", hovermode="closest", height=500,
                      margin=dict(l=20, r=20, t=30, b=30), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    fig.update_yaxes(tickformat=",")
    st.plotly_chart(fig, width="stretch")

    render_section("HISTORY", "BETした試合の詳細")
    for bet in sorted_settled:
        profit_value = profit_for_record(bet)
        amount = float(bet.get("bet_amount", abs(float(bet.get("bet_units", 0) or 0)) * 10000) or 0)
        team_name, opponent_name = str(bet.get("team", "-")), str(bet.get("opponent", "-"))
        team_score_value, opponent_score_value = bet.get("team_score"), bet.get("opponent_score")
        score = f"{team_score_value} - {opponent_score_value}" if team_score_value is not None and opponent_score_value is not None else "未確定"
        icon = "🟢" if profit_value > 0 else ("🔴" if profit_value < 0 else "⚪")
        title = f"{icon} {bet.get('date', '-')} {bet.get('time', '-')} | {team_name} vs {opponent_name} | {yen(profit_value)}"
        with st.expander(title):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("BET先", team_name)
            c2.metric("BET額", yen(amount))
            c3.metric("ハンディ", str(bet.get("handicap", 0)))
            c4.metric("損益", yen(profit_value))
            st.write(f"**試合スコア:** {score}　｜　**結果:** {result_label(bet.get('result'))}")
            if bet.get("memo"):
                st.write(f"**メモ:** {bet['memo']}")
            actions = st.container(horizontal=True)
            if actions.button("編集", key=f"edit_final_{bet['id']}"):
                edit_bet_dialog(bet)
            if actions.button("削除", key=f"delete_final_{bet['id']}"):
                delete_bet_dialog(bet)
else:
    st.info("確定済みBETはまだありません。未確定BETは下に表示されます。")

if pending:
    render_section("PENDING", "未確定BET")
    for bet in sorted_pending:
        amount = float(bet.get("bet_amount", abs(float(bet.get("bet_units", 0) or 0)) * 10000) or 0)
        title = f"⏳ {bet.get('date', '-')} {bet.get('time', '-')} ｜ {bet.get('team', '-')} vs {bet.get('opponent', '-')} ｜ {yen(amount)}"
        with st.expander(title):
            st.write(f"**BET先:** {bet.get('team', '-')}　｜　**ハンディ:** {bet.get('handicap', 0)}")
            if bet.get("memo"):
                st.write(f"**メモ:** {bet['memo']}")
            with st.form(f"settle_bet_{bet['id']}"):
                c1, c2 = st.columns(2)
                team_score = c1.number_input("BET先チーム得点", min_value=0, step=1, value=0, key=f"settle_team_{bet['id']}")
                opponent_score = c2.number_input("対戦相手得点", min_value=0, step=1, value=0, key=f"settle_opponent_{bet['id']}")
                settle_submitted = st.form_submit_button("スコアを確定して精算", type="primary", width="stretch")
            if settle_submitted:
                adjusted_score, result = settle_bet(team_score, opponent_score, bet.get("handicap", 0))
                changes = {
                    "status": "final",
                    "result": result,
                    "profit": profit_for_result(result, amount),
                    "team_score": int(team_score),
                    "opponent_score": int(opponent_score),
                    "adjusted_score": adjusted_score,
                    "settled": True,
                    "updated_at": datetime.now().isoformat(timespec="seconds"),
                }
                try:
                    update_bet(BETS_FILE, bet["id"], changes)
                except BetStoreError as exc:
                    st.error(str(exc))
                else:
                    st.session_state["bet_notice"] = f"{result_label(result)}として精算しました。損益は {yen(changes['profit'])} です。"
                    st.rerun()
            actions = st.container(horizontal=True)
            if actions.button("編集", key=f"edit_pending_{bet['id']}"):
                edit_bet_dialog(bet)
            if actions.button("削除", key=f"delete_pending_{bet['id']}"):
                delete_bet_dialog(bet)
