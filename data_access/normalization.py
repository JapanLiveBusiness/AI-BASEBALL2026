"""Data normalization helpers."""

def npb_logo_slug(team_name):
    name = str(team_name)
    logo_names = (
        (("阪神", "タイガース"), "hanshin"), (("巨人", "読売", "ジャイアンツ"), "giants"),
        (("中日", "ドラゴンズ"), "dragons"), (("広島", "カープ"), "carp"),
        (("DeNA", "ＤｅＮＡ", "横浜", "ベイスターズ"), "baystars"), (("ヤクルト", "スワローズ"), "swallows"),
        (("ソフトバンク", "ホークス"), "hawks"), (("ロッテ", "マリーンズ"), "marines"),
        (("楽天", "イーグルス"), "eagles"), (("日本ハム", "ファイターズ"), "fighters"),
        (("西武", "ライオンズ"), "lions"), (("オリックス", "バファローズ"), "buffaloes"),
    )
    for aliases, slug in logo_names:
        if any(alias in name for alias in aliases):
            return slug
    return "generic"
