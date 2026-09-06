"""Fractional settlement from the supplied Japanese baseball handicap table.

Positive tokens are giving; negative tokens are receiving. 1.5 and 1半
are intentionally distinct. Legacy numeric settlement remains versioned separately.
"""
from decimal import Decimal, ROUND_HALF_UP
import re
import unicodedata

RULE = "jpb_fractional_v1"


def normalize_handicap(value):
    text = unicodedata.normalize("NFKC", str(value or "0")).strip().strip("<>").replace(" ", "")
    if not re.fullmatch(r"[+-]?(?:\d+(?:\.[0-9])?|\d*半[357]?)", text):
        raise ValueError("ハンデは0.3、1、1.5、1半、1半3などで入力してください。受け側は先頭に-を付けます。")
    sign = "-" if text.startswith("-") else ""
    token = text.lstrip("+-")
    if "半" not in token:
        token = format(Decimal(token).normalize(), "f")
    elif token.startswith("半"):
        token = "0" + token
    if Decimal(token.split("半")[0]) > 100:
        raise ValueError("ハンデは100以下で入力してください。")
    return sign + token if token != "0" else "0"


def _giving_fraction(margin, token):
    if "半" in token:
        whole, suffix = token.split("半")
        boundary = int(whole) + 1
        if margin < boundary:
            return Decimal(-1)
        if margin == boundary and suffix:
            return Decimal(1) - Decimal(suffix) / 10
        return Decimal(1)
    number = Decimal(token)
    whole = int(number)
    fraction = number - whole
    if not fraction:
        return Decimal(1 if margin > whole else -1 if margin < whole else 0)
    if margin < whole:
        return Decimal(-1)
    if margin == whole:
        return -fraction
    if whole == 0 and margin == 1:
        return Decimal(1) - fraction
    return Decimal(1)


def fractional_settlement(team_score, opponent_score, handicap, amount):
    token = normalize_handicap(handicap)
    scores = [Decimal(str(value)) for value in (team_score, opponent_score)]
    if any(not value.is_finite() or value < 0 or value != value.to_integral_value() for value in scores):
        raise ValueError("得点は0以上の整数で入力してください。")
    margin = int(scores[0] - scores[1])
    receiving = token.startswith("-")
    ratio = _giving_fraction(-margin if receiving else margin, token.lstrip("-"))
    if receiving:
        ratio = -ratio
    result = "win" if ratio > 0 else "loss" if ratio < 0 else "push"
    fraction = abs(ratio)
    stake = Decimal(str(amount))
    if not stake.is_finite() or stake < 0:
        raise ValueError("BET金額は0以上で入力してください。")
    profit = stake * ratio * (Decimal("0.9") if ratio > 0 else Decimal(1))
    label = "勝負無し" if not ratio else ("丸勝ち" if ratio == 1 else "丸負け" if ratio == -1 else f"{int(fraction * 10)}分{'勝ち' if ratio > 0 else '負け'}")
    return {
        "settlement_rule": RULE, "settlement_fraction": float(fraction),
        "settlement_label": label, "result": result,
        "profit": int(profit.quantize(Decimal(1), rounding=ROUND_HALF_UP)),
        "adjusted_score": None,
    }
