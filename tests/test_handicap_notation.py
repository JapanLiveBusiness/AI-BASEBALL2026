from bs4 import BeautifulSoup

from handicap_notation import adjusted_score, handicap_result, parse_japanese_handicap
from handicap_source import handicap_token_to_value
from handenomori_client import _normalize_handicap_cells


def test_parse_japanese_notation():
    assert parse_japanese_handicap("1半5") == 1.5
    assert parse_japanese_handicap("1半後") == 1.5
    assert parse_japanese_handicap("1半4") == 1.4
    assert parse_japanese_handicap("1半6") == 1.6
    assert parse_japanese_handicap("1半") == 1.5
    assert parse_japanese_handicap("1.5") == 1.5


def test_adjusted_score():
    assert adjusted_score(5, "1半後") == 3.5


def test_result():
    assert handicap_result(5, 3, "1半後") == "WIN"
    assert handicap_result(4, 3, "1半後") == "LOSE"


def test_handicap_source_uses_same_rule():
    assert handicap_token_to_value("1半5") == 1.5
    assert handicap_token_to_value("1半後") == 1.5
    assert handicap_token_to_value("1半4") == 1.4
    assert handicap_token_to_value("1半6") == 1.6


def test_handenomori_cells_are_normalized_for_existing_float_parser():
    html = b"""
    <table class='single-handi'>
      <tr>
        <td class='single-handi-handi'>1\xe5\x8d\x8a5</td>
        <td class='single-handi-handi'></td>
      </tr>
    </table>
    """
    normalized = _normalize_handicap_cells(html)
    soup = BeautifulSoup(normalized, "html.parser")
    values = [cell.get_text(strip=True) for cell in soup.select("td.single-handi-handi")]
    assert values == ["1.5", ""]
    assert float(values[0]) == 1.5
