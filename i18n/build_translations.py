"""Translates Medi's interface into the supported languages (run after changing interface text, then commit).

Collects every fixed English string the app shows:
- text and placeholder/title/alt/aria-label attributes in index.html, except inside #chat, [data-dynamic]
  (filled in by code), and [data-i18n-html] (translated as whole HTML snippets, by key),
- strings in the page's script wrapped in t("...") or N_("..."),
- the backend's safety advice and crisis line,
then translates them with gpt-4o and writes i18n/translations.json.

Usage (from the doctor/ folder):  python i18n/build_translations.py
"""
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).parent
APP = HERE.parent
sys.path.insert(0, str(APP))
from medi import config, llm  # noqa: E402
from medi.language import LANG_NAMES  # noqa: E402
from medi.safety.escalation import CRISIS_LINE  # noqa: E402
from medi.safety.input_checks import RED_FLAGS  # noqa: E402
from medi.rag.evidence import LIMITATION  # noqa: E402
from medi.safety.output_checks import EMERGENCY_ACTION  # noqa: E402

LANGUAGES = {code: name for code, name in LANG_NAMES.items() if code != "en"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
ATTRS = ("placeholder", "title", "alt", "aria-label")
BATCH = 30  # smaller batches = fewer truncated/invalid JSON replies from the model


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def has_letters(s):
    return any(ch.isalpha() for ch in s)


class Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.texts = set()

    def skipping(self):
        return any(self.stack)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        skip = (tag in ("script", "style") or a.get("id") == "chat" or "data-dynamic" in a or "data-i18n-html" in a)
        if not self.skipping() and not skip:
            for name in ATTRS:
                if a.get(name) and has_letters(a[name]):
                    self.texts.add(norm(a[name]))
        if tag not in VOID:
            self.stack.append(skip)

    def handle_endtag(self, tag):
        if tag not in VOID and self.stack:
            self.stack.pop()

    def handle_data(self, data):
        if not self.skipping() and has_letters(data):
            self.texts.add(norm(data))


def collect():
    page = (APP / "index.html").read_text(encoding="utf-8")
    body = page[page.index("<body"):]
    parser = Collector()
    parser.feed(body[:body.index("<script>")] + body[body.index("</script>") + 9:])
    texts = set(parser.texts)

    script = page[page.index("<script>"):page.index("</script>")]
    for raw in re.findall(r'\b(?:t|N_)\(\s*"((?:[^"\\]|\\.)*)"', script):
        texts.add(json.loads(f'"{raw}"'))

    texts.update(advice for _, _, advice in RED_FLAGS)
    texts.add(CRISIS_LINE.strip())
    texts.add(EMERGENCY_ACTION)
    texts.update(LIMITATION.values())

    html = {key: norm(inner) for _, key, inner in
            re.findall(r'<(\w+)\b[^>]*\bdata-i18n-html="([\w-]+)"[^>]*>(.*?)</\1>', page, flags=re.S)}
    return sorted(texts), html


PROMPT = """You translate the user interface of "Medi", an AI family health and wellbeing assistant web app (Portal Medic 365) used in Canada and the US, into {language}.
Rules:
- Translate naturally, warmly, and plainly, the way a caring clinic would write for patients. Use the polite/neutral register.
- Keep exactly as they are: emojis, numbers, phone numbers and short codes (9-8-8, 911, 112, 999, 000, 1-800-668-6868, 686868), "{{placeholders}}" in curly braces, markdown markers (** and *), line breaks (\\n), and HTML tags and attributes.
- Keep these names unchanged: Medi, Portal Medic 365, MedlinePlus.gov, OpenAI, Google Maps, bshepp/clinical-decision-support-agent, Apache License 2.0. Keep the text keyword CONNECT unchanged.
- For "Kids Help Phone", use its official name in the language if one exists (French: Jeunesse, J'écoute), otherwise keep it.
- Strings that start with an emoji should keep that emoji first.
- Glossary: the app has two modes. "Health check" (and "health assistant") is the physical symptom checker. "Wellbeing" is the separate mental and emotional wellbeing mode; translate it with a term that clearly means emotional/mental wellbeing and can't be confused with the health check (e.g. Chinese 身心健康, Vietnamese Sức khỏe tinh thần, Persian سلامت روان).
Return a JSON object with exactly the same keys as the input and the translated strings as values."""


def translate_batch(language, items):
    out = json.loads(llm.chat_text({
        "model": config.FAST_MODEL,  # UI chrome translation; mini is enough and much cheaper at this scale
        "temperature": 0,
        "messages": [{"role": "system", "content": PROMPT.format(language=language)},
                     {"role": "user", "content": json.dumps(items, ensure_ascii=False)}],
        "response_format": {"type": "json_object"},
    }, timeout=180))
    missing = [k for k in items if not isinstance(out.get(k), str)]
    if missing:
        raise ValueError(f"{language}: missing {len(missing)} translations")
    return out


def translate_batch_safe(language, items):
    """Translate a batch; on persistent JSON failures, fall back to one string at a time."""
    try:
        return translate_batch(language, items)
    except Exception as e:
        if len(items) == 1:
            raise
        print(f"  splitting {language} batch ({len(items)}): {e}", flush=True)
        out = {}
        for key, value in items.items():
            for attempt in range(3):
                try:
                    out |= translate_batch(language, {key: value})
                    break
                except Exception as inner:
                    if attempt == 2:
                        raise
                    print(f"  retrying {language} single: {inner}", flush=True)
        return out


def translate_language(code, texts, html):
    language = LANGUAGES[code]
    entries = {f"t{i}": s for i, s in enumerate(texts)} | {f"h_{k}": v for k, v in html.items()}
    keys = list(entries)
    out = {}
    for start in range(0, len(keys), BATCH):
        batch = {k: entries[k] for k in keys[start:start + BATCH]}
        for attempt in range(3):
            try:
                out |= translate_batch_safe(language, batch)
                break
            except Exception as e:
                if attempt == 2:
                    raise
                print(f"  retrying {language} batch: {e}", flush=True)
    result = {"text": {s: out[f"t{i}"] for i, s in enumerate(texts)}, "html": {k: out[f"h_{k}"] for k in html}}
    print(f"  {language}: {len(result['text'])} strings, {len(result['html'])} HTML snippets", flush=True)
    return code, result


def save(translations):
    out = HERE / "translations.json"
    out.write_text(json.dumps(translations, ensure_ascii=False, indent=0), encoding="utf-8")
    return out


def main():
    from concurrent.futures import as_completed

    texts, html = collect()
    print(f"Collected {len(texts)} strings and {len(html)} HTML snippets; translating into {len(LANGUAGES)} languages...",
          flush=True)
    translations = {}
    # Keep any already-finished languages if this run is resumed after a crash.
    existing = {}
    out_path = HERE / "translations.json"
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
        except ValueError:
            existing = {}
    todo = []
    for code in LANGUAGES:
        prev = existing.get(code) or {}
        if prev.get("text") and set(prev["text"]) >= set(texts) and set(prev.get("html", {})) >= set(html):
            translations[code] = {"text": {s: prev["text"][s] for s in texts},
                                  "html": {k: prev["html"][k] for k in html}}
            print(f"  keep {LANGUAGES[code]}", flush=True)
        else:
            todo.append(code)
    print(f"Translating {len(todo)} languages ({len(translations)} already complete)...", flush=True)
    failed = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(translate_language, code, texts, html): code for code in todo}
        for fut in as_completed(futures):
            code = futures[fut]
            try:
                code, result = fut.result()
            except Exception as e:
                failed.append(code)
                print(f"  FAILED {LANGUAGES.get(code, code)}: {e}", flush=True)
                continue
            translations[code] = result
            path = save(translations)
            print(f"  saved {len(translations)}/{len(LANGUAGES)} → {path.name}", flush=True)
    path = save(translations)
    print(f"Done. Saved {path} ({path.stat().st_size / 1e3:.0f} KB)", flush=True)
    if failed:
        print(f"Failed languages ({len(failed)}): {', '.join(failed)}", flush=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
