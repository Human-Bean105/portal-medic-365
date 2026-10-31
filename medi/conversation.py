"""Helpers for the conversation the browser sends: message text and who the visit is about."""


def message_text(message):
    content = message.get("content")
    if isinstance(content, str):
        return content
    return " ".join(part.get("text", "") for part in content or [] if part.get("type") == "text")


def last_user_text(messages):
    last = next((m for m in reversed(messages) if m.get("role") == "user"), None)
    return message_text(last) if last else ""


def profile_note(profile, patient):
    if patient != "self":
        return ("Who this consultation is about: someone OTHER than the account holder (e.g. a child, partner, or parent). "
                "No stored health profile applies to this person. Ask who the patient is and their age if not yet known, "
                "and collect any relevant history from scratch. Use only what is said in this conversation.")
    fields = [(k, str(v).strip()) for k, v in (profile or {}).items() if str(v or "").strip()]
    if not fields:
        return "Who this consultation is about: the account holder. No health profile was provided."
    return ("Who this consultation is about: the account holder. Their stored health profile (self-reported):\n"
            + "\n".join(f"- {k}: {v}" for k, v in fields))
