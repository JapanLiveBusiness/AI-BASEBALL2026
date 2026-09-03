from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

JST = ZoneInfo("Asia/Tokyo")

STANDINGS_URLS = {
    "セ・リーグ": "https://npb.jp/bis/2026/stats/std_c.html",
    "パ・リーグ": "https://npb.jp/bis/2026/stats/std_p.html",
}

TEAM_ALIASES = {
    "阪神タイガース": "阪神",
    "阪神": "阪神",
    "読売ジャイアンツ": "巨人",
    "読売": "巨人",
    "巨人": "巨人",
    "横浜DeNAベイスターズ": "DeNA",
    "横浜DeNA": "DeNA",
    "DeNA": "DeNA",
    "東京ヤクルトスワローズ": "ヤクルト",
    "東京ヤクルト": "ヤクルト",
    "ヤクルト": "ヤクルト",
    "広島東洋カープ": "広島",
    "広島東洋": "広島",
    "広島": "広島",
    "中日ドラゴンズ": "中日",
    "中日": "中日",
    "福岡ソフトバンクホークス": "ソフトバンク",
    "福岡ソフトバンク": "ソフトバンク",
    "ソフトバンク": "ソフトバンク",
    "埼玉西武ライオンズ": "西武",
    "埼玉西武": "西武",
    "西武": "西武",
    "北海道日本ハムファイターズ": "日本ハム",
    "北海道日本ハム": "日本ハム",
    "日本ハム": "日本ハム",
    "千葉ロッテマリーンズ": "ロッテ",
    "千葉ロッテ": "ロッテ",
    "ロッテ": "ロッテ",
    "オリックス・バファローズ": "オリックス",
    "オリックス": "オリックス",
    "東北楽天ゴールデンイーグルス": "楽天",
    "東北楽天": "楽天",
    "楽天": "楽天",
}


def normalize_team(value: Any) -> str:
    text = re.sub(r"\s+", "", str(value or ""))
    for alias, canonical in sorted(TEAM_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if re.sub(r"\s+", "", alias) in text:
            return canonical
    return str(value or "").strip()


def record_rate(value: str) -> float | None:
    match = re.search(r"(\d+)\s*-\s*(\d+)", value or "")
    if not match:
        return None
    wins, losses = int(match.group(1)), int(match.group(2))
    decided = wins + losses
    return wins / decided if decided else None


def parse_pct(value: str) -> float | None:
    match = re.search(r"(?:0)?\.\d{3}", value or "")
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def fetch_standings(url: str, league: str) -> dict[str, dict[str, Any]]:
    response = requests.get(
        url,
        timeout=20,
        headers={"User-Agent": "AI-BASEBALL-STUDIO research schedule sync"},
    )
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")

    result: dict[str, dict[str, Any]] = {}
    for row in soup.select("tr"):
        cells = [re.sub(r"\s+", " ", cell.get_text(" ", strip=True)).strip() for cell in row.select("th,td")]
        if len(cells) < 9:
            continue
        team = normalize_team(cells[0])
        if team not in set(TEAM_ALIASES.values()):
            continue

        pct = parse_pct(cells[5])
        home_rate = record_rate(cells[7])
        road_rate = record_rate(cells[8])
        if pct is None:
            continue

        try:
            games = int(re.search(r"\d+", cells[1]).group(0))
            wins = int(re.search(r"\d+", cells[2]).group(0))
            losses = int(re.search(r"\d+", cells[3]).group(0))
            draws = int(re.search(r"\d+", cells[4]).group(0))
        except (AttributeError, ValueError):
            games = wins = losses = draws = None

        result[team] = {
            "team": team,
            "league": league,
            "games": games,
            "wins": wins,
            "losses": losses,
            "draws": draws,
            "pct": pct,
            "home_rate": home_rate,
            "road_rate": road_rate,
            "source_url": url,
        }

    if len(result) < 6:
        raise RuntimeError(f"standings parser returned only {len(result)} teams for {league}")
    return result


def adjusted_strength(row: dict[str, Any], split: str) -> float:
    overall = float(row["pct"])
    venue_rate = row.get(split)
    if venue_rate is None:
        value = overall
    else:
        value = overall * 0.70 + float(venue_rate) * 0.30
    return min(0.78, max(0.22, value))


def log5_probability(home_strength: float, away_strength: float) -> float:
    numerator = home_strength * (1.0 - away_strength)
    denominator = numerator + (1.0 - home_strength) * away_strength
    raw = numerator / denominator if denominator else 0.5
    # Standings-only models can become overconfident late in the season.
    # Shrink the raw Log5 estimate toward 50% for a more conservative baseline.
    shrunk = 0.5 + 0.72 * (raw - 0.5)
    return min(0.72, max(0.28, shrunk))


def confidence(probability: float) -> str:
    edge = max(probability, 1.0 - probability)
    if edge >= 0.64:
        return "A"
    if edge >= 0.60:
        return "A-"
    if edge >= 0.57:
        return "B+"
    if edge >= 0.54:
        return "B"
    return "C+"


def score_scenario(probability: float) -> str:
    edge = max(probability, 1.0 - probability)
    if edge >= 0.65:
        return "5-2"
    if edge >= 0.60:
        return "4-2"
    if edge >= 0.56:
        return "4-3"
    return "3-2"


def build_prediction(game: dict[str, Any], standings: dict[str, dict[str, Any]]) -> dict[str, Any]:
    home = normalize_team(game.get("home"))
    away = normalize_team(game.get("away"))
    base = {
        "home": home,
        "away": away,
        "league": game.get("league") or "NPB",
    }

    home_row = standings.get(home)
    away_row = standings.get(away)
    if not home_row or not away_row:
        return {
            **base,
            "pick": None,
            "win_probability": None,
            "confidence": "-",
            "status": "insufficient_data",
            "reason": "公式順位表で両チームの成績を確認できませんでした",
        }

    home_strength = adjusted_strength(home_row, "home_rate")
    away_strength = adjusted_strength(away_row, "road_rate")
    home_probability = log5_probability(home_strength, away_strength)

    if home_probability >= 0.5:
        pick = home
        pick_probability = home_probability
    else:
        pick = away
        pick_probability = 1.0 - home_probability

    return {
        **base,
        "pick": pick,
        "win_probability": round(pick_probability * 100.0, 1),
        "home_win_probability": round(home_probability * 100.0, 1),
        "predicted_score": score_scenario(home_probability),
        "predicted_score_order": "winner-loser illustrative scenario",
        "confidence": confidence(home_probability),
        "status": "ready",
        "inputs": {
            "home_overall_pct": round(float(home_row["pct"]), 3),
            "home_home_pct": round(float(home_row.get("home_rate") or home_row["pct"]), 3),
            "away_overall_pct": round(float(away_row["pct"]), 3),
            "away_road_pct": round(float(away_row.get("road_rate") or away_row["pct"]), 3),
        },
    }


def generate(schedule_path: Path, output_path: Path) -> dict[str, Any]:
    schedule = json.loads(schedule_path.read_text(encoding="utf-8"))
    games = [row for row in schedule.get("games") or [] if isinstance(row, dict)]
    slate_date = str(schedule.get("date") or "")
    if not slate_date or not games:
        raise RuntimeError("schedule payload has no date or games")

    standings: dict[str, dict[str, Any]] = {}
    source_urls: list[str] = []
    errors: list[str] = []
    for league, url in STANDINGS_URLS.items():
        try:
            standings.update(fetch_standings(url, league))
            source_urls.append(url)
        except Exception as exc:
            errors.append(f"{league}: {exc}")

    if not standings:
        raise RuntimeError("could not load any official NPB standings: " + "; ".join(errors))

    predictions = [build_prediction(game, standings) for game in games]
    ready = [row for row in predictions if row.get("pick") and row.get("win_probability") is not None]
    ready.sort(key=lambda row: float(row["win_probability"]), reverse=True)
    rank_lookup = {(row["home"], row["away"]): rank for rank, row in enumerate(ready, 1)}
    for row in predictions:
        row["rank"] = rank_lookup.get((row["home"], row["away"]))

    now = datetime.now(JST).isoformat(timespec="seconds")
    payload = {
        "date": slate_date,
        "updated_at": now,
        "model": "NPB Official Standings Baseline v1",
        "model_type": "transparent standings baseline",
        "method": "70% overall win rate + 30% home/road split, Log5 matchup, 28-72% clamp",
        "games": predictions,
        "count": len(predictions),
        "ready_count": len(ready),
        "source": "NPB公式",
        "source_urls": source_urls,
        "warnings": errors,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp = output_path.with_suffix(output_path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(output_path)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate research daily NPB prediction baseline")
    parser.add_argument("--schedule", default="data/npb_today.json")
    parser.add_argument("--output", default="data/today_ai_predictions.json")
    args = parser.parse_args()

    payload = generate(Path(args.schedule), Path(args.output))
    print(json.dumps({
        "date": payload["date"],
        "count": payload["count"],
        "ready_count": payload["ready_count"],
        "model": payload["model"],
        "output": args.output,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
