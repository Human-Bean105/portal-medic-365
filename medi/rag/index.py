"""Loads the prebuilt knowledge base: passages with their metadata plus unit-length embedding vectors."""
import base64
import json
from array import array

from .. import config

_cache = {}


def load(path=None):
    """Loads an index once per server instance. Returns (data, vectors)."""
    path = path or config.RAG_INDEX
    if path not in _cache:
        data = json.loads(path.read_text(encoding="utf-8"))
        vectors = array("f")
        vectors.frombytes(base64.b64decode(data["vectors"]))
        _cache[path] = (data, vectors)
    return _cache[path]
