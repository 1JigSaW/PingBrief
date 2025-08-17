"""Language-to-flag utilities.

Keep UI-related formatting logic out of handlers.
"""

from __future__ import annotations


def get_flag_emoji(
    language_code: str,
) -> str:
    """Return a flag emoji for a given ISO 639-1 language code.

    Defaults to globe if mapping is unknown.
    """
    flag_map = {
        "en": "🇺🇸",
        "ru": "🇷🇺",
        "es": "🇪🇸",
        "fr": "🇫🇷",
        "de": "🇩🇪",
        "zh": "🇨🇳",
        "ja": "🇯🇵",
        "ko": "🇰🇷",
        "it": "🇮🇹",
        "pt": "🇵🇹",
        "ar": "🇸🇦",
        "hi": "🇮🇳",
        "tr": "🇹🇷",
        "nl": "🇳🇱",
        "sv": "🇸🇪",
    }
    return flag_map.get(language_code, "🌍")


