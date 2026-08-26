"""Deterministic win-probability calculations independent of Streamlit."""

def bradley_terry_probability(hawks_pct, opponent_pct):
    if hawks_pct is None or opponent_pct is None:
        return None
    denominator = hawks_pct + opponent_pct - (2 * hawks_pct * opponent_pct)
    if denominator <= 0:
        return float(hawks_pct) * 100.0
    return ((hawks_pct - hawks_pct * opponent_pct) / denominator) * 100.0

def clamp_probability(value):
    return max(0.5, min(99.5, float(value)))

def score_adjustment(score_mode, handicap_score, effective_score_diff, inning, outs):
    if score_mode == "handicap":
        value = float(handicap_score) * 8.0
    else:
        point_value = 8.0 + ((int(inning) - 1) * 1.25)
        out_pressure = 1.0 + (int(outs) * 0.10 if int(inning) >= 7 else 0.0)
        value = float(effective_score_diff) * point_value * out_pressure
    return max(-55.0, min(55.0, value))
