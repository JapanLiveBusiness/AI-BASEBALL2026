from handicap_notation import adjusted_score, handicap_result, parse_japanese_handicap


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
