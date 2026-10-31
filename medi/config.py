"""Every model name, threshold, and feature switch in one place. Values can be overridden with environment variables."""
import os
from dataclasses import dataclass, replace
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent


def load_env():
    for env_file in (APP_DIR / ".env", APP_DIR.parent / ".env"):
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())


load_env()


def env(name, default):
    return os.environ.get(name) or default


API_KEY = os.environ.get("OPENAI_API_KEY")
DEV_TOKEN = os.environ.get("MEDI_DEV_TOKEN", "")

MODEL = os.environ.get("DOCTOR_MODEL") or env("OPENAI_MODEL", "gpt-4o")
FAST_MODEL = env("RAG_REWRITE_MODEL", "gpt-4o-mini")
EMBED_MODEL = "text-embedding-3-small"
REALTIME_MODEL = env("REALTIME_MODEL", "gpt-realtime")
REALTIME_VOICE = env("REALTIME_VOICE", "marin")
TTS_MODEL = env("TTS_MODEL", "gpt-4o-mini-tts")
TRANSCRIBE_MODEL = "gpt-4o-mini-transcribe"

# Estimated US$ per million tokens (input, output), used only for cost reporting. Update if prices change.
PRICES = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "text-embedding-3-small": (0.02, 0.0),
}

MAX_BODY = 15 * 1024 * 1024
MAX_MESSAGES = 30
MAX_MESSAGE_CHARS = 8000

RAG_INDEX = APP_DIR / "rag" / "medi_index.json"
TRANSLATIONS_FILE = APP_DIR / "i18n" / "translations.json"


@dataclass(frozen=True)
class Pipeline:
    """One configuration of the answering pipeline. Experiments compare several of these on the same test data."""
    name: str = "medi-v1"
    rag: bool = os.environ.get("MEDI_RAG", "1") != "0"
    top_k: int = 5
    min_score: float = 0.3
    per_topic: int = 2

    def but(self, **changes):
        return replace(self, **changes)


DEFAULT = Pipeline()
