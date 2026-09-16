import re
from typing import Optional


def parse_japanese_handicap(value: object) -> Optional[float]:
    """Convert Japanese baseball handicap notation to a numeric run value.

    Examples:
      1半5 / 1半後 -> 1.5
      1半4 -> 1.4
      1半6 -> 1.6
      1半 -> 1.5
      1.5 -> 1.5

    Returns None when no handicap is present / notation cannot be parsed.
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text or text in {"-", "－", "なし", "無し", "None", "null"}:
        return None

    # Normalize common full-width punctuation / spacing.
    text = (
        text.replace("　", "")
        .replace(" ", "")
        .replace("．", ".")
        .replace("−", "-")
        .replace("ー", "-")
    )

    # In common spoken/input notation, 後 is used for 5 (1半後 == 1半5).
    text = text.replace("半後", "半5")

    # 1半5 => 1.5, 2半4 => 2.4, etc.
    m = re.search(r"(-?\d+)半([0-9])", text)
    if m:
        return float(f"{m.group(1)}.{m.group(2)}")

    # Bare '1半' is treated as 1.5.
    m = re.search(r"(-?\d+)半", text)
    if m:
        return float(m.group(1)) + (0.5 if int(m.group(1)) >= 0 else -0.5)

    # Standard decimal/integer notation.
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    if m:
        return float(m.group(0))

    return None


def adjusted_score(team_score: float, handicap: object) -> float:
    """Return score after subtracting the team's handicap."""
    parsed = parse_japanese_handicap(handicap)
    return float(team_score) - (parsed or 0.0)


def handicap_result(team_score: float, opponent_score: float, handicap: object) -> str:
    """Return WIN/LOSE/DRAW after applying handicap to team_score."""
    adjusted = adjusted_score(team_score, handicap)
    opponent = float(opponent_score)
    if adjusted > opponent:
        return "WIN"
    if adjusted < opponent:
        return "LOSE"
    return "DRAW"
