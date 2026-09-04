"""Archive and evaluate all daily NPB predictions."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from storage.json_store import load_json, save_json_atomic


def _score(value: Any) -> tuple[int, int] | None:
    try:
        left, right = str(value).split("-", 1)
        return int(left), int(right)
    except (AttributeError, TypeError, ValueError):
        return None


def _home_probability(prediction: dict[str, Any]) -> float | None:
    value = prediction.get("home_win_probability")
    if value is not None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    try:
        pick_probability = float(prediction.get("win_probability"))
    except (TypeError, ValueError):
        return None
    if prediction.get("pick") == prediction.get("home"):
        return pick_probability
    if prediction.get("pick") == prediction.get("away"):
        return 100.0 - pick_probability
    return None


def archive_predictions(
    archive: list[dict[str, Any]],
    predictions: dict[str, Any],
    schedule: dict[str, Any],
) -> tuple[list[dict[str, Any]], int]:
    """Add each pregame prediction once without modifying locked history."""
    result = deepcopy([row for row in archive if isinstance(row, dict)])
    target_date = str(predictions.get("date") or "")
    if not target_date or target_date != str(schedule.get("date") or ""):
        return result, 0

    schedule_index = {
        (str(game.get("home") or ""), str(game.get("away") or "")): game
        for game in schedule.get("games") or []
        if isinstance(game, dict)
    }
    existing = {str(row.get("game_id") or "") for row in result}
    now = datetime.now(timezone.utc).isoformat()
    added = 0
    for prediction in predictions.get("games") or []:
        if not isinstance(prediction, dict):
            continue
        home = str(prediction.get("home") or "")
        away = str(prediction.get("away") or "")
        if not home or not away:
            continue
        game_id = f"{target_date}_{home}_{away}"
        if game_id in existing:
            continue
        scheduled = schedule_index.get((home, away), {})
        result.append(
            {
                "game_id": game_id,
                "date": target_date,
                "time": scheduled.get("time"),
                "venue": scheduled.get("venue"),
                "home": home,
                "away": away,
                "pick": prediction.get("pick"),
                "win_probability": prediction.get("win_probability"),
                "home_win_probability": _home_probability(prediction),
                "predicted_score": prediction.get("predicted_score"),
                "confidence": prediction.get("confidence"),
                "model": prediction.get("model") or predictions.get("model"),
                "locked": True,
                "saved_at": now,
                "status": "pending",
                "actual_home_score": None,
                "actual_away_score": None,
                "actual_winner": None,
                "hit": None,
                "brier": None,
                "score_error": None,
                "settled_at": None,
            }
        )
        existing.add(game_id)
        added += 1
    result.sort(key=lambda row: (str(row.get("date") or ""), str(row.get("time") or ""), str(row.get("home") or "")))
    return result, added


def settle_predictions(
    archive: list[dict[str, Any]], schedule: dict[str, Any]
) -> tuple[list[dict[str, Any]], int]:
    """Settle archived predictions from final scores for the matching date."""
    result = deepcopy([row for row in archive if isinstance(row, dict)])
    schedule_date = str(schedule.get("date") or "")
    final_index = {}
    for game in schedule.get("games") or []:
        if not isinstance(game, dict) or str(game.get("status") or "") != "final":
            continue
        if game.get("home_score") is None or game.get("away_score") is None:
            continue
        final_index[(schedule_date, str(game.get("home") or ""), str(game.get("away") or ""))] = game

    settled = 0
    for row in result:
        if row.get("status") in {"final", "draw"}:
            continue
        game = final_index.get((str(row.get("date") or ""), str(row.get("home") or ""), str(row.get("away") or "")))
        if not game:
            continue
        home_score, away_score = int(game["home_score"]), int(game["away_score"])
        row["actual_home_score"] = home_score
        row["actual_away_score"] = away_score
        row["settled_at"] = datetime.now(timezone.utc).isoformat()
        settled += 1
        if home_score == away_score:
            row.update({"status": "draw", "actual_winner": None, "hit": None, "brier": None})
            continue
        winner = row["home"] if home_score > away_score else row["away"]
        row["status"] = "final"
        row["actual_winner"] = winner
        row["hit"] = str(row.get("pick") or "") == winner
        try:
            probability = float(row.get("home_win_probability")) / 100.0
            actual_home_win = 1.0 if home_score > away_score else 0.0
            row["brier"] = round((probability - actual_home_win) ** 2, 6)
        except (TypeError, ValueError):
            row["brier"] = None
        predicted = _score(row.get("predicted_score"))
        row["score_error"] = (
            round((abs(predicted[0] - home_score) + abs(predicted[1] - away_score)) / 2.0, 2)
            if predicted
            else None
        )
    return result, settled


def build_performance(archive: list[dict[str, Any]]) -> dict[str, Any]:
    finals = [row for row in archive if row.get("status") == "final"]
    draws = [row for row in archive if row.get("status") == "draw"]
    hits = sum(row.get("hit") is True for row in finals)
    briers = [float(row["brier"]) for row in finals if row.get("brier") is not None]
    errors = [float(row["score_error"]) for row in finals if row.get("score_error") is not None]
    confidence = {}
    for level in ("HIGH", "MEDIUM", "LOW", "A", "A-", "B", "C+"):
        rows = [row for row in finals if row.get("confidence") == level]
        level_hits = sum(row.get("hit") is True for row in rows)
        if rows:
            confidence[level] = {"games": len(rows), "hits": level_hits, "hit_rate": round(level_hits / len(rows) * 100, 1)}
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "settled_games": len(finals),
        "draws": len(draws),
        "hits": hits,
        "hit_rate": round(hits / len(finals) * 100, 1) if finals else None,
        "brier_score": round(sum(briers) / len(briers), 6) if briers else None,
        "score_mae": round(sum(errors) / len(errors), 2) if errors else None,
        "confidence": confidence,
        "games": finals,
    }


def merge_prediction_archives(*archives: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge local and shared locked predictions without losing final results."""
    merged: dict[str, dict[str, Any]] = {}
    status_rank = {"pending": 0, "draw": 1, "final": 2}
    for archive in archives:
        for row in archive or []:
            if not isinstance(row, dict):
                continue
            key = str(row.get("game_id") or "")
            if not key:
                key = "|".join(
                    str(row.get(field) or "")
                    for field in ("date", "home", "away")
                )
            if not key.strip("|"):
                continue
            current = merged.get(key)
            if current is None:
                merged[key] = deepcopy(row)
                continue
            current_rank = status_rank.get(str(current.get("status") or "pending"), 0)
            incoming_rank = status_rank.get(str(row.get("status") or "pending"), 0)
            if incoming_rank >= current_rank:
                combined = deepcopy(current)
                combined.update({field: value for field, value in row.items() if value is not None})
                merged[key] = combined
    return sorted(
        merged.values(),
        key=lambda row: (
            str(row.get("date") or ""),
            str(row.get("time") or ""),
            str(row.get("home") or ""),
        ),
    )


def sync_prediction_results(
    data_dir: Path,
    shared_data_dir: Path | None = Path("/app/shared-data"),
) -> dict[str, int]:
    predictions = load_json(data_dir / "today_ai_predictions.json", {})
    schedule = load_json(data_dir / "npb_today.json", {})
    archive_path = data_dir / "ai_prediction_history.json"
    archive = load_json(archive_path, [])
    if not isinstance(archive, list):
        archive = []
    shared_count = 0
    shared_added = 0
    shared_settled = 0
    if shared_data_dir is not None and shared_data_dir.exists():
        shared_archive = load_json(shared_data_dir / "ai_prediction_history.json", [])
        if isinstance(shared_archive, list):
            shared_count = len(shared_archive)
            archive = merge_prediction_archives(archive, shared_archive)
        shared_predictions = load_json(shared_data_dir / "today_ai_predictions.json", {})
        shared_schedule = load_json(shared_data_dir / "npb_today.json", {})
        archive, shared_added = archive_predictions(archive, shared_predictions, shared_schedule)
        archive, shared_settled = settle_predictions(archive, shared_schedule)
    archive, added = archive_predictions(archive, predictions, schedule)
    archive, settled = settle_predictions(archive, schedule)
    save_json_atomic(archive_path, archive)
    save_json_atomic(data_dir / "ai_prediction_performance.json", build_performance(archive))
    return {
        "added": added + shared_added,
        "settled": settled + shared_settled,
        "shared": shared_count + shared_added,
        "total": len(archive),
    }


if __name__ == "__main__":
    print(sync_prediction_results(Path("/app/data")))
