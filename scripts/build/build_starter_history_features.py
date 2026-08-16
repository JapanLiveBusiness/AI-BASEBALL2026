import json
import unicodedata
from pathlib import Path
from collections import defaultdict

SRC = Path(
    "/opt/hawks-ai/data/hawks_games_with_starters.json"
)

OUT = Path(
    "/opt/hawks-ai/data/hawks_games_starter_history.json"
)

ALIASES = {
    "スチュワート": "スチュワートジュニア",
    "石川": "石川雅規",
    "田嶋大": "田嶋大樹",
    "深沢": "深沢鳳介",
}

def norm(name):
    if not name:
        return ""

    s = unicodedata.normalize("NFKC", name)

    s = s.replace("*", "")
    s = s.replace(" ", "")
    s = s.replace("　", "")
    s = s.replace("・", "")
    s = s.strip()

    return ALIASES.get(s, s)


with SRC.open(encoding="utf-8") as f:
    games = json.load(f)

games = sorted(
    games,
    key=lambda x: x["date"]
)


# 過去の先発履歴
hawks_history = defaultdict(list)
opp_history = defaultdict(list)

output = []


def calc(items):

    if not items:
        return {
            "starts": 0,
            "win_pct": 0.5,
            "recent3_win_pct": 0.5,
            "avg_run_diff": 0.0
        }

    decided = [
        x for x in items
        if x["result"] != "draw"
    ]

    if decided:
        wins = sum(
            x["result"] == "win"
            for x in decided
        )

        pct = wins / len(decided)

    else:
        pct = 0.5


    recent = items[-3:]

    recent_decided = [
        x for x in recent
        if x["result"] != "draw"
    ]

    if recent_decided:
        rw = sum(
            x["result"] == "win"
            for x in recent_decided
        )

        recent_pct = (
            rw / len(recent_decided)
        )

    else:
        recent_pct = 0.5


    avg_diff = sum(
        x["run_diff"]
        for x in items
    ) / len(items)


    return {
        "starts": len(items),
        "win_pct": round(pct, 4),
        "recent3_win_pct": round(
            recent_pct,
            4
        ),
        "avg_run_diff": round(
            avg_diff,
            3
        )
    }


for g in games:

    hs = norm(
        g.get("hawks_starter")
    )

    os = norm(
        g.get("opponent_starter")
    )

    # 相手投手は球団もキーにする
    opp_key = (
        g["opponent"],
        os
    )

    hstat = calc(
        hawks_history[hs]
    )

    ostat = calc(
        opp_history[opp_key]
    )

    x = dict(g)

    x["starter_history"] = {
        "hawks": hstat,
        "opponent": ostat,

        "win_pct_diff": round(
            hstat["win_pct"]
            - ostat["win_pct"],
            4
        ),

        "recent3_diff": round(
            hstat["recent3_win_pct"]
            - ostat["recent3_win_pct"],
            4
        ),

        "run_diff_advantage": round(
            hstat["avg_run_diff"]
            - ostat["avg_run_diff"],
            3
        )
    }

    output.append(x)


    # この試合終了後に履歴へ追加
    # ＝未来情報を絶対に使用しない

    record = {
        "date": g["date"],
        "result": g["result"],
        "run_diff": g["run_diff"]
    }

    hawks_history[hs].append(
        record
    )

    opp_history[opp_key].append(
        record
    )


with OUT.open(
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        output,
        f,
        ensure_ascii=False,
        indent=2
    )


print(
    "===== STARTER HISTORY FEATURES ====="
)

print("TOTAL :", len(output))
print("OUTPUT:", OUT)


print("\n===== LAST 10 =====")

for g in output[-10:]:

    h = g["starter_history"]["hawks"]
    o = g["starter_history"]["opponent"]

    print(
        g["date"],
        g["hawks_starter"],
        "vs",
        g["opponent_starter"],
        "| H",
        h["starts"],
        f"{h['win_pct']:.1%}",
        "| O",
        o["starts"],
        f"{o['win_pct']:.1%}",
        "| ADV",
        f"{g['starter_history']['win_pct_diff']:+.1%}"
    )
