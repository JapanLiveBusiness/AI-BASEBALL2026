import re
import unicodedata
from typing import Optional


# Uploaded workbook: プロ野球ハンデ判定表.xlsx
# The table is intentionally kept explicit so fractional outcomes are not
# approximated by subtracting a decimal handicap from the score.
HANDICAP_JUDGEMENT_TABLE = {
    "05": {1: "5分勝ち", 2: "丸勝ち", 3: "丸勝ち", 4: "丸勝ち"},
    "07": {1: "7分勝ち", 2: "丸勝ち", 3: "丸勝ち", 4: "丸勝ち"},
    "1": {1: "引き分け", 2: "丸勝ち", 3: "丸勝ち", 4: "丸勝ち"},
    "1ア3": {1: "3分負け", 2: "丸勝ち", 3: "丸勝ち", 4: "丸勝ち"},
    "1ア5": {1: "5分負け", 2: "丸勝ち", 3: "丸勝ち", 4: "丸勝ち"},
    "1ア7": {1: "7分負け", 2: "丸勝ち", 3: "丸勝ち", 4: "丸勝ち"},
    "1半": {1: "丸負け", 2: "丸勝ち", 3: "丸勝ち", 4: "丸勝ち"},
    "1半3": {1: "丸負け", 2: "3分勝ち", 3: "丸勝ち", 4: "丸勝ち"},
    "1半4": {1: "丸負け", 2: "4分勝ち", 3: "丸勝ち", 4: "丸勝ち"},
    "1半5": {1: "丸負け", 2: "5分勝ち", 3: "丸勝ち", 4: "丸勝ち"},
    "1半7": {1: "丸負け", 2: "7分勝ち", 3: "丸勝ち", 4: "丸勝ち"},
    "1半8": {1: "丸負け", 2: "8分勝ち", 3: "丸勝ち", 4: "丸勝ち"},
    "2": {1: "丸負け", 2: "引き分け", 3: "丸勝ち", 4: "丸勝ち"},
    "2半": {1: "丸負け", 2: "丸負け", 3: "丸勝ち", 4: "丸勝ち"},
    "2半3": {1: "丸負け", 2: "丸負け", 3: "3分勝ち", 4: "丸勝ち"},
    "2半5": {1: "丸負け", 2: "丸負け", 3: "5分勝ち", 4: "丸勝ち"},
    "2半7": {1: "丸負け", 2: "丸負け", 3: "7分勝ち", 4: "丸勝ち"},
    "3": {1: "丸負け", 2: "丸負け", 3: "引き分け", 4: "丸勝ち"},
    "3半": {1: "丸負け", 2: "丸負け", 3: "丸負け", 4: "丸勝ち"},
    "3半3": {1: "丸負け", 2: "丸負け", 3: "丸負け", 4: "3分勝ち"},
    "3半5": {1: "丸負け", 2: "丸負け", 3: "丸負け", 4: "5分勝ち"},
    "3半7": {1: "丸負け", 2: "丸負け", 3: "丸負け", 4: "7分勝ち"},
}


def normalize_handicap_token(value: object) -> Optional[str]:
    """Normalize source notation to a key used by HANDICAP_JUDGEMENT_TABLE."""
    if value is None:
        return None

    text = unicodedata.normalize("NFKC", str(value)).strip()
    if not text or text in {"-", "－", "なし", "無し", "None", "null"}:
        return None

    text = text.replace(" ", "").replace("　", "")
    text = text.replace("半後", "半5")

    aliases = {
        "0.5": "05",
        ".5": "05",
        "0.7": "07",
        ".7": "07",
        "1.0": "1",
        "2.0": "2",
        "3.0": "3",
    }
    return aliases.get(text, text)


def handicap_table_result(team_score: float, opponent_score: float, handicap: object) -> str:
    """Judge a projected score using the uploaded handicap table.

    The result is from the perspective of the team carrying the handicap.
    Scores are expected to be whole-run baseball scores. Unknown notation is
    returned as 判定対象外 rather than guessed.
    """
    token = normalize_handicap_token(handicap)
    if token is None:
        return "ハンデなし"
    if token not in HANDICAP_JUDGEMENT_TABLE:
        return "判定対象外"

    try:
        margin_value = float(team_score) - float(opponent_score)
    except (TypeError, ValueError):
        return "判定対象外"

    rounded = round(margin_value)
    if abs(margin_value - rounded) > 1e-9:
        return "判定対象外"

    margin = int(rounded)
    if margin <= 0:
        return "丸負け"
    if margin >= 5:
        return "丸勝ち"
    return HANDICAP_JUDGEMENT_TABLE[token][margin]


def parse_japanese_handicap(value: object) -> Optional[float]:
    """Convert Japanese notation to a numeric approximation for legacy code.

    This numeric value is NOT used for fractional win/loss judgement. Use
    handicap_table_result() when the uploaded settlement table is required.
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text or text in {"-", "－", "なし", "無し", "None", "null"}:
        return None

    text = (
        text.replace("　", "")
        .replace(" ", "")
        .replace("．", ".")
        .replace("−", "-")
        .replace("ー", "-")
        .replace("半後", "半5")
    )

    if text == "05":
        return 0.5
    if text == "07":
        return 0.7

    m = re.search(r"(-?\d+)半([0-9])", text)
    if m:
        return float(f"{m.group(1)}.{m.group(2)}")

    m = re.search(r"(-?\d+)半", text)
    if m:
        return float(m.group(1)) + (0.5 if int(m.group(1)) >= 0 else -0.5)

    m = re.search(r"-?\d+(?:\.\d+)?", text)
    if m:
        return float(m.group(0))

    return None


def adjusted_score(team_score: float, handicap: object) -> float:
    """Legacy numeric adjustment retained for probability-model compatibility."""
    parsed = parse_japanese_handicap(handicap)
    return float(team_score) - (parsed or 0.0)


def handicap_result(team_score: float, opponent_score: float, handicap: object) -> str:
    """Legacy WIN/LOSE/DRAW result based on numeric approximation."""
    adjusted = adjusted_score(team_score, handicap)
    opponent = float(opponent_score)
    if adjusted > opponent:
        return "WIN"
    if adjusted < opponent:
        return "LOSE"
    return "DRAW"
