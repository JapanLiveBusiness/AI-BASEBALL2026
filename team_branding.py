import html

TEAM_MARKS = [
    (("読売ジャイアンツ", "巨人", "Yomiuri Giants"), "G", "#f36c21", "#111111"),
    (("阪神タイガース", "阪神", "Hanshin Tigers"), "T", "#f4c300", "#111111"),
    (("横浜DeNAベイスターズ", "DeNA", "横浜", "BayStars"), "DB", "#0876bd", "#ffffff"),
    (("広島東洋カープ", "広島", "カープ", "Carp"), "C", "#d71920", "#ffffff"),
    (("中日ドラゴンズ", "中日", "Dragons"), "D", "#1655a5", "#ffffff"),
    (("東京ヤクルトスワローズ", "ヤクルト", "Swallows"), "S", "#0a3765", "#ffffff"),
    (("福岡ソフトバンクホークス", "ソフトバンク", "ソフト", "ホークス", "Hawks"), "H", "#f3d321", "#111111"),
    (("北海道日本ハムファイターズ", "日本ハム", "日ハム", "Fighters"), "F", "#0b3158", "#ffffff"),
    (("千葉ロッテマリーンズ", "ロッテ", "Marines"), "M", "#111111", "#ffffff"),
    (("東北楽天ゴールデンイーグルス", "楽天", "Eagles"), "E", "#8c1531", "#ffffff"),
    (("オリックス・バファローズ", "オリックス", "Buffaloes"), "B", "#172a53", "#d7b65d"),
    (("埼玉西武ライオンズ", "西武", "Lions"), "L", "#1d4f91", "#ffffff"),
]

TEAM_BADGE_CSS = """
.team-badge{display:inline-flex;align-items:center;justify-content:center;flex:none;border-radius:50%;background:var(--team-bg);color:var(--team-fg);font-weight:950;letter-spacing:-.04em;border:1px solid rgba(255,255,255,.22);box-shadow:0 2px 8px rgba(0,0,0,.22)}
.team-badge-xs{width:18px;height:18px;font-size:7px}.team-badge-sm{width:24px;height:24px;font-size:8px}.team-badge-md{width:30px;height:30px;font-size:10px}.team-badge-lg{width:38px;height:38px;font-size:13px}
.team-with-badge{display:inline-flex;align-items:center;gap:8px;min-width:0}.team-with-badge .team-label{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
"""


def team_style(team):
    name = str(team or "-")
    mark, bg, fg = "⚾", "#30363d", "#ffffff"
    lowered = name.lower()
    for aliases, candidate_mark, candidate_bg, candidate_fg in TEAM_MARKS:
        if any(alias.lower() in lowered for alias in aliases):
            return candidate_mark, candidate_bg, candidate_fg
    return mark, bg, fg


def team_badge(team, size="md"):
    mark, bg, fg = team_style(team)
    return (
        f"<span class='team-badge team-badge-{html.escape(size)}' "
        f"style='--team-bg:{bg};--team-fg:{fg}'>{html.escape(mark)}</span>"
    )


def team_label(team, size="md", strong=True):
    name = html.escape(str(team or "-"))
    label = f"<strong class='team-label'>{name}</strong>" if strong else f"<span class='team-label'>{name}</span>"
    return f"<span class='team-with-badge'>{team_badge(team, size=size)}{label}</span>"
