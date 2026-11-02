"""Loads a prebuilt knowledge base: passages with their metadata, unit-length embedding vectors, and a keyword index."""
import base64
import json
from array import array
from pathlib import Path

from .. import config
from .bm25 import BM25, passage_text

_cache = {}


class Index:
    def __init__(self, path):
        data = json.loads(path.read_text(encoding="utf-8"))
        self.path = path
        self.data = data
        self.chunks = data["chunks"]
        self.dims = data["dims"]
        self.vectors = array("f")
        self.vectors.frombytes(base64.b64decode(data["vectors"]))
        self._bm25 = None

    @property
    def bm25(self):
        if self._bm25 is None:
            self._bm25 = BM25([passage_text(c) for c in self.chunks])
        return self._bm25

    def cosine_all(self, q):
        d, v = self.dims, self.vectors
        return [sum(a * b for a, b in zip(q, v[i * d:(i + 1) * d])) for i in range(len(self.chunks))]


def get(path=None):
    """The index at `path` (relative to the app folder), loaded once per server instance."""
    path = Path(path) if path else config.RAG_INDEX
    if not path.is_absolute():
        path = config.APP_DIR / path
    key = str(path)
    if key not in _cache:
        _cache[key] = Index(path)
    return _cache[key]


def load(path=None):
    """(data, vectors) for code that works with the raw index."""
    idx = get(path)
    return idx.data, idx.vectors
