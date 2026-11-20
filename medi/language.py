"""Language handling: the app's chosen language, the person's actual language, and translations for safety checks."""
import json
import re

from . import config, llm

# ChatGPT's official UI language list (OpenAI Help Center), plus English.
# Chinese is split into Simplified and Traditional for clearer patient UI.
# Kept in alphabetical order by English name.
LANG_NAMES = {
    "sq": "Albanian",
    "am": "Amharic",
    "ar": "Arabic",
    "hy": "Armenian",
    "bn": "Bengali",
    "bs": "Bosnian",
    "bg": "Bulgarian",
    "my": "Burmese",
    "ca": "Catalan",
    "hr": "Croatian",
    "cs": "Czech",
    "da": "Danish",
    "nl": "Dutch",
    "en": "English",
    "et": "Estonian",
    "fi": "Finnish",
    "fr": "French",
    "ka": "Georgian",
    "de": "German",
    "el": "Greek",
    "gu": "Gujarati",
    "hi": "Hindi",
    "hu": "Hungarian",
    "is": "Icelandic",
    "id": "Indonesian",
    "it": "Italian",
    "ja": "Japanese",
    "kn": "Kannada",
    "kk": "Kazakh",
    "ko": "Korean",
    "lv": "Latvian",
    "lt": "Lithuanian",
    "mk": "Macedonian",
    "ms": "Malay",
    "ml": "Malayalam",
    "mr": "Marathi",
    "mn": "Mongolian",
    "no": "Norwegian",
    "fa": "Persian (Farsi)",
    "pl": "Polish",
    "pt": "Portuguese",
    "pa": "Punjabi",
    "ro": "Romanian",
    "ru": "Russian",
    "sr": "Serbian",
    "zh-Hans": "Simplified Chinese",
    "sk": "Slovak",
    "sl": "Slovenian",
    "so": "Somali",
    "es": "Spanish",
    "sw": "Swahili",
    "sv": "Swedish",
    "tl": "Tagalog",
    "ta": "Tamil",
    "te": "Telugu",
    "th": "Thai",
    "zh-Hant": "Traditional Chinese",
    "tr": "Turkish",
    "uk": "Ukrainian",
    "ur": "Urdu",
    "vi": "Vietnamese",
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
    return (f"LANGUAGE: The app language is {name}. ALWAYS write in {name}, even if the person writes or speaks in a "
            f"different language. Understand their message in whatever language they use, but every text field you return "
            f"(reply, headlines, lists, condition names, quick replies) and any required emergency instruction must be in "
            f"{name} (e.g. translate \"Call 911 ...\" into {name} when needed). Keep JSON keys and enum values exactly as "
            f"specified, in English.")


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
