"""Features around the consultation: the printable visit summary, read-aloud speech, and live voice calls."""
import json
import os
import re

from . import config, language, llm, prompts
from .conversation import message_text, profile_note


def summarize(messages, profile, patient, lang="en"):
    transcript = "\n".join(
        f"{'Patient' if m.get('role') == 'user' else 'Medi (AI)'}: {message_text(m)}" for m in messages
    )
    text = llm.chat_text({
        "model": config.MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": prompts.SUMMARY_PROMPT + f"\nWrite the summary, including section headings, in {language.LANG_NAMES.get(lang, 'English')}."},
            {"role": "user", "content": profile_note(profile, patient) + "\n\nTranscript:\n" + transcript},
        ],
    })
    return {"summary": text.strip()}


def speak(text):
    """Turns a typed reply into natural speech with OpenAI's text-to-speech model. Returns MP3 bytes."""
    plain = re.sub(r"\*\*|__|`|^#+\s*", "", text, flags=re.M)
    plain = re.sub(r"^\s*[-*•]\s+", "", plain, flags=re.M)
    return llm.speech(plain[:4000], config.REALTIME_VOICE, prompts.TTS_STYLE)


def voice_session(sdp, profile, patient, history, mode="health", lang="en"):
    """Starts a Realtime voice call through OpenAI's unified WebRTC interface and returns the SDP answer."""
    base = (prompts.WELLBEING_PROMPT + prompts.WELLBEING_VOICE_PROMPT if mode == "wellbeing"
            else prompts.SYSTEM_PROMPT + prompts.VOICE_PROMPT)
    instructions = base + "\n\n" + profile_note(profile, patient) + "\n\n" + language.language_note(lang)
    earlier = [f"{'Patient' if m.get('role') == 'user' else 'Medi'}: {message_text(m)}" for m in history[-20:]]
    if any(m.get("role") == "user" for m in history):
        instructions += ("\n\nEarlier in this same visit, by text chat (continue from here instead of greeting from scratch):\n"
                         + "\n".join(earlier))
    session = {
        "type": "realtime",
        "model": config.REALTIME_MODEL,
        "instructions": instructions,
        "audio": {
            "input": {
                "transcription": {"model": config.TRANSCRIBE_MODEL},
                # The app triggers each reply itself, after looking up reference passages for what was just said.
                "turn_detection": {"type": "semantic_vad", "create_response": False, "interrupt_response": True},
                "noise_reduction": {"type": "far_field"},
            },
            "output": {"voice": config.REALTIME_VOICE},
        },
    }
    boundary = "----medi" + os.urandom(12).hex()
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"sdp\"\r\nContent-Type: application/sdp\r\n\r\n{sdp}\r\n"
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"session\"\r\nContent-Type: application/json\r\n\r\n"
        f"{json.dumps(session)}\r\n--{boundary}--\r\n"
    ).encode()
    return {"sdp": llm.realtime_call(body, boundary)}
