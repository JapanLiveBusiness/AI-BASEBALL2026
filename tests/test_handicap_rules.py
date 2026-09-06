import json
from copy import deepcopy
from pathlib import Path
import pytest

from bet_analytics import profit_for_record
from bet_store import recalculate_handicap_history, load_bets, BetStoreError
from handicap_rules import fractional_settlement, normalize_handicap, RULE
from bet_transfer import bets_to_xlsx, read_bet_spreadsheet


# Every cell of the user-supplied table: draw / win by one / two / three.
TABLE = {
    "0.3": [-0.3, 0.7, 1, 1], "0.5": [-0.5, 0.5, 1, 1],
    "0.7": [-0.7, 0.3, 1, 1], "1": [-1, 0, 1, 1],
    "1.3": [-1, -0.3, 1, 1], "1.5": [-1, -0.5, 1, 1],
    "1.7": [-1, -0.7, 1, 1], "1半": [-1, -1, 1, 1],
    "1半3": [-1, -1, 0.7, 1], "1半5": [-1, -1, 0.5, 1],
    "1半7": [-1, -1, 0.3, 1], "2": [-1, -1, 0, 1],
}


@pytest.mark.parametrize("token,ratios", TABLE.items())
@pytest.mark.parametrize("margin", range(4))
def test_every_supplied_table_cell_and_receiving_side(token, ratios, margin):
    ratio = ratios[margin]
    result = fractional_settlement(3 + margin, 3, token, 10000)
    expected = round(10000 * ratio * (0.9 if ratio > 0 else 1))
    assert result["profit"] == expected
    assert result["settlement_fraction"] == abs(ratio)
    opposite = fractional_settlement(3, 3 + margin, "-" + token, 10000)
    assert opposite["profit"] == round(-10000 * ratio * (0.9 if ratio < 0 else 1))


def test_half_token_is_not_decimal_and_rejects_approximations():
    assert normalize_handicap("1.5") != normalize_handicap("1半")
    assert fractional_settlement(4, 3, "1.5", 10000)["profit"] == -5000
    assert fractional_settlement(4, 3, "1半", 10000)["profit"] == -10000
    with pytest.raises(ValueError):
        normalize_handicap("1.65")


def sample_record():
    return {"id": "sample", "date": "2026-01-01", "time": "18:00", "team": "A", "opponent": "B", "handicap": 0.7,
            "bet_amount": 10000, "team_score": 5, "opponent_score": 4, "status": "final", "result": "win", "profit": 9000}


def test_explicit_recalculation_backups_and_preserves_ids_and_other_users(tmp_path):
    record = sample_record()
    path = tmp_path / "bets.json"
    path.write_text(json.dumps([record]), encoding="utf-8")
    other = tmp_path / "other.json"
    other.write_bytes(path.read_bytes())
    untouched = other.read_bytes()
    report = recalculate_handicap_history(path)
    assert report["count"] == report["changed"] == 1
    assert report["before"] == 9000 and report["after"] == 2700
    assert json.loads(Path(report["backup"]).read_text(encoding="utf-8")) == [record]
    assert load_bets(path)[0]["id"] == "sample"
    assert other.read_bytes() == untouched
    assert recalculate_handicap_history(path)["changed"] == 0


def test_invalid_history_leaves_original_bytes_untouched(tmp_path):
    path = tmp_path / "bets.json"
    records = [sample_record(), dict(sample_record(), id="bad", team_score=None)]
    path.write_text(json.dumps(records), encoding="utf-8")
    before = path.read_bytes()
    with pytest.raises(BetStoreError):
        recalculate_handicap_history(path)
    assert path.read_bytes() == before


def test_spreadsheet_round_trip_preserves_half_and_partial_profit():
    record = dict(sample_record(), handicap="-1半3", team_score=3, opponent_score=5)
    record.update(fractional_settlement(3, 5, record["handicap"], 10000))
    restored = read_bet_spreadsheet(bets_to_xlsx([record]), "bets.xlsx")[0]
    assert restored["handicap"] == "-1半3"
    assert restored["settlement_rule"] == RULE
    assert restored["profit"] == -7000
    assert profit_for_record(restored) == -7000


def test_unmodified_legacy_history_keeps_old_calculation():
    assert profit_for_record(sample_record()) == 9000
