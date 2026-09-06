"""Read-only aggregation and calendar for non-redeemable virtual points."""
import calendar
from datetime import date
from html import escape
from decimal import Decimal, InvalidOperation


def bet_amount_label(row):
    """Show stakes, not profit; unknown amounts must not look like zero."""
    try:
        amount = row.get("bet_amount")
        if amount is None:
            amount = abs(Decimal(str(row["bet_units"]))) * 10000
        amount = Decimal(str(amount))
        if not amount.is_finite() or amount <= 0:
            return "金額要確認"
        if amount % 10000 == 0:
            return f"{amount / 10000:,.0f}万 pt"
        return f"{amount:,.0f} pt" if amount == amount.to_integral_value() else f"{amount:,f} pt"
    except (InvalidOperation, ValueError, TypeError, KeyError):
        return "金額要確認"


def summarize(rows):
    calculated = [r for r in rows if r.get("status") == "calculated" and isinstance(r.get("points_delta"), int)]
    daily = {}
    for row in calculated:
        try:
            day = date.fromisoformat(str(row.get("date"))).isoformat()
        except ValueError:
            continue
        daily[day] = daily.get(day, 0) + row["points_delta"]
    cumulative = 0
    series = []
    for day, delta in sorted(daily.items()):
        cumulative += delta
        series.append({"日付": day, "日別ポイント": delta, "累積ポイント": cumulative})
    return {"points": cumulative, "calculated": len(calculated),
            "review": sum(r.get("status") == "review" for r in rows),
            "pending": sum(r.get("status") == "pending" for r in rows),
            "cancelled": sum(r.get("status") == "cancelled" for r in rows),
            "daily": daily, "series": series}


def month_options(rows):
    months = set()
    for row in rows:
        try:
            months.add(date.fromisoformat(str(row.get("date"))).strftime("%Y-%m"))
        except ValueError:
            pass
    return sorted(months, reverse=True)


def calendar_html(rows, month):
    rows = [r for r in rows if not r.get("virtual_deleted")]
    first = date.fromisoformat(month + "-01")
    summary = summarize(rows)
    states = {}
    bets = {}
    for row in rows:
        states.setdefault(str(row.get("date")), []).append(row.get("status"))
        bets.setdefault(str(row.get("date")), []).append(row)
    cells = []
    for week in calendar.Calendar(firstweekday=0).monthdayscalendar(first.year, first.month):
        for day in week[1:]:
            if day == 0:
                cells.append('<div class="vp-cell vp-empty"></div>')
                continue
            key = f"{month}-{day:02d}"
            delta = summary["daily"].get(key)
            status = states.get(key, [])
            color = "vp-positive" if delta is not None and delta > 0 else "vp-negative" if delta is not None and delta < 0 else ""
            value = f"{delta:+,} pt" if delta is not None else "—"
            notes = []
            for state, label in [("review", "要確認"), ("pending", "未確定"), ("cancelled", "中止")]:
                if state in status:
                    notes.append(f"{label} {status.count(state)}")
            details = ''.join(f'<span class="vp-bet"><span>{escape(str(r.get("team") or "チーム未確認"))}</span><span class="vp-stake">{escape(bet_amount_label(r))}</span></span>' for r in bets.get(key, []))
            cells.append(f'<a class="vp-cell {color}" href="?edit_date={key}#day-editor" target="_self" aria-label="{key} の内容を編集"><b>{day}</b><strong>{value}</strong><span class="vp-bets">{details}</span><small>{escape(" / ".join(notes))}</small></a>')
    style = '<style>.vp-calendar{grid-template-columns:repeat(6,minmax(0,1fr))!important}.vp-calendar .vp-cell{min-height:150px}.vp-bets{display:block;margin-top:8px}.vp-bet{display:block;color:#253044;font-size:12px;line-height:1.5;overflow-wrap:anywhere;margin-top:6px}.vp-bet>span{display:block}.vp-stake{font-weight:600}@media(max-width:600px){.vp-calendar .vp-cell{min-height:130px}.vp-bet{font-size:10px;line-height:1.4}}</style>'
    return style + '<div class="vp-calendar">' + ''.join(f'<div class="vp-weekday">{day}</div>' for day in "火水木金土日") + ''.join(cells) + '</div>'


def history_rows(rows):
    labels = {"calculated": "計算済み", "review": "要確認", "pending": "未確定", "cancelled": "中止"}
    return [{"日付": r.get("date"), "チーム": r.get("team"), "相手": r.get("opponent"),
             "状態": labels.get(r.get("status"), "要確認"), "適用ハンデ": r.get("handicap_raw"),
             "元履歴ハンデ": r.get("stored_handicap"),
             "再取得適用": "あり" if r.get("handicap_refetched") else "なし",
             "手動編集": "あり" if r.get("virtual_edited") else "なし",
             "9回時点": f"{r['team_score_9']}–{r['opponent_score_9']}" if "team_score_9" in r else None,
             "ポイント増減": r.get("points_delta"), "確認事項": r.get("reason", ""),
             "公式記録": r.get("score_source", ""),
             "ハンデ出典": r.get("handicap_source", "")} for r in sorted(rows, key=lambda r: str(r.get("date") or ""), reverse=True)]
