"""What happens when a safety check fires: instructions to the model and guaranteed crisis-line wording."""
import re

from .. import language

MENTAL_HEALTH_FLAGS = {"Thoughts of suicide or self-harm", "Thoughts of harming someone else", "Possible abuse or an unsafe home"}
CRISIS_LINE = ("\n\nIf you're not safe or you're thinking about hurting yourself or someone else, you can call or text "
               "**9-8-8** any time (Canada and US). If you're in immediate danger, call **911**.")
CRISIS_NUMBER = re.compile(r"[9۹٩]\s*-?\s*[8۸٨]\s*-?\s*[8۸٨]")


def alert_note(flags, wellbeing):
    """The system message that tells the model a safety check fired on the latest message."""
    return ("SAFETY SCREENER ALERT for the latest message: " + "; ".join(f["label"] for f in flags) +
            (". Follow the SAFETY rules now, and include 9-8-8 and 911 in your reply." if wellbeing else
             ". Treat this as an emergency unless the patient clearly says it is not happening now, "
             "and begin your reply with the emergency instruction."))


def is_crisis(result, flags):
    return result.get("risk", {}).get("level") == "crisis" or any(f["label"] in MENTAL_HEALTH_FLAGS for f in flags)


def ensure_crisis_line(result, flags, lang="en"):
    """Guarantees every mental-health crisis reply contains 9-8-8 and 911, whatever the model wrote."""
    if is_crisis(result, flags) and not CRISIS_NUMBER.search(result["reply"]):
        result["reply"] += "\n\n" + language.ui_text(CRISIS_LINE.strip(), lang)
    return result
