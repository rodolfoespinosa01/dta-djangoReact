ALLOWED_THEMES = {"dark", "light"}
DEFAULT_THEME = "light"


def normalize_theme(value):
    theme = str(value or "").strip().lower()
    if theme not in ALLOWED_THEMES:
        return DEFAULT_THEME
    return theme


def is_allowed_theme(value):
    return str(value or "").strip().lower() in ALLOWED_THEMES
