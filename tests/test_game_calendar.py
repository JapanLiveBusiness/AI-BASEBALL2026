from datetime import date

from game_calendar import (
    attach_handicaps,
    merge_game_sources,
    parse_handicap_html,
    parse_npb_schedule_html,
)


def test_parse_official_schedule_keeps_rowspan_date_and_schedule_details():
    markup = """
    <table>
      <tr><td rowspan="2">9/5（土）</td><td>ソフトバンク - 西武</td><td>みずほPayPay 14:00</td></tr>
      <tr><td>オリックス - ロッテ</td><td>京セラD大阪 14:00</td></tr>
      <tr><td>9/6（日）</td><td>楽天 5 - 2 日本ハム</td><td>楽天モバイル 13:00</td></tr>
    </table>
    """
    games = parse_npb_schedule_html(markup, 2026, 9)

    assert [(game["date"], game["home"], game["away"]) for game in games] == [
        ("2026-09-05", "ソフトバンク", "西武"),
        ("2026-09-05", "オリックス", "ロッテ"),
        ("2026-09-06", "楽天", "日本ハム"),
    ]
    assert games[0]["time"] == "14:00"
    assert games[0]["venue"] == "みずほPayPay"
    assert games[2]["status"] == "final"
    assert (games[2]["home_score"], games[2]["away_score"]) == (5, 2)


def test_parse_and_attach_daily_handicaps():
    markup = """
    <div class="game-detail2">
      <span class="detail-card-team">ヤクルト</span><span class="detail-card-team">阪神</span>
      <div>4-7</div>
      <div class="detail-single-studium-time"><span>18:00</span><span>神宮野球場</span></div>
      <table class="single-handi"><tr><td class="single-handi-handi"></td><td class="single-handi-handi">1.1</td></tr></table>
    </div>
    """
    handicaps = parse_handicap_html(markup, date(2026, 9, 3))
    games = [{"home": "ヤクルト", "away": "阪神", "home_score": 4, "away_score": 7}]
    result = attach_handicaps(games, handicaps)

    assert result[0]["home_handicap"] is None
    assert result[0]["away_handicap"] == "1.1"
    assert handicaps[0]["status"] == "final"


def test_merge_sources_enriches_history_without_losing_official_time():
    official = [{"home": "中日", "away": "広島", "time": "18:00", "venue": "バンテリンドーム"}]
    history = [{"home": "中日", "away": "広島", "home_score": 2, "away_score": 5, "status": "final"}]

    result = merge_game_sources(official, history)

    assert result == [{
        "home": "中日",
        "away": "広島",
        "time": "18:00",
        "venue": "バンテリンドーム",
        "home_score": 2,
        "away_score": 5,
        "status": "final",
    }]
