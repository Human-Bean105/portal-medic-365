"""Language handling: the app's chosen language, the person's actual language, and translations for safety checks."""
import json
import re

from . import config, llm

LANG_NAMES = {
    "en": "English", "fr": "French", "es": "Spanish", "zh-Hans": "Simplified Chinese", "zh-Hant": "Traditional Chinese",
    "pa": "Punjabi", "hi": "Hindi", "tl": "Tagalog", "ko": "Korean", "vi": "Vietnamese", "fa": "Persian (Farsi)", "ar": "Arabic",
}
_translations = None


def ui_text(english, lang):
    """The app's own translation of a fixed English string (built by i18n/build_translations.py)."""
    global _translations
    if lang == "en":
        return english
    if _translations is None:
        try:
            _translations = json.loads(config.TRANSLATIONS_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _translations = {}
    return _translations.get(lang, {}).get("text", {}).get(english, english)


def language_note(lang):
    name = LANG_NAMES.get(lang, "English")
    return (f"LANGUAGE: The person chose {name} as the app language, so write in {name} by default. If they write or "
            "speak in a different language, reply in the language they're using instead. Use that same language for every "
            "text field you return (reply, headlines, lists, condition names, quick replies). Keep JSON keys and enum values "
            "exactly as specified, in English.")


def needs_english(text, lang):
    """Non-English messages are translated before the English-only keyword check and source search."""
    return lang != "en" or bool(re.search(r"[^\x00-\x7F\u00C0-\u024F\u2018-\u201D]", text))


def to_english(text, usage=None):
    return llm.chat_text({
        "model": config.FAST_MODEL,
        "temperature": 0,
        "max_tokens": 300,
        "messages": [{"role": "system", "content": "Translate the user's message into English. Output only the translation."},
                     {"role": "user", "content": text}],
    }, timeout=15, usage=usage).strip()
