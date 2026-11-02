"""Splits documents into passages that keep whole sentences, carry their heading, and overlap their neighbors slightly.

Chunk size and overlap are parameters so different settings can be compared on the same retrieval benchmark."""
import hashlib
import re

SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"(])")


def sentences(line):
    return [s for s in SENTENCE_END.split(line) if s.strip()]


def units(text):
    """(heading, piece) pairs: list items stay whole; paragraphs are split into sentences."""
    heading = ""
    for line in text.splitlines():
        if line.startswith("## "):
            heading = line[3:].strip()
        elif line.startswith("- "):
            yield heading, line
        else:
            for s in sentences(line):
                yield heading, s


def chunk_document(doc, max_chars=900, overlap=1):
    """Packs sentences into passages of at most ~max_chars, repeating the last `overlap` sentences of one passage at
    the start of the next. A passage never mixes two sections; each starts with "Title (section): "."""
    chunks, current, heading = [], [], None

    def emit():
        if current:
            label = doc["title"] + (f" ({heading})" if heading else "")
            chunks.append({"heading": heading or "", "text": f"{label}: " + " ".join(current)})

    for h, piece in units(doc["text"]):
        if current and (h != heading or sum(len(p) + 1 for p in current) + len(piece) > max_chars):
            emit()
            current = current[-overlap:] if overlap and h == heading else []
        heading = h
        current.append(piece)
    emit()
    return [{**c, "chunk_index": i} for i, c in enumerate(chunks)]


def body_hash(text):
    return hashlib.sha1(re.sub(r"\W+", " ", text.split(": ", 1)[-1].lower()).strip().encode()).hexdigest()


def build_chunks(documents, max_chars=900, overlap=1):
    """All passages for all documents, with exact duplicates (same body text) removed."""
    out, seen, dropped = [], set(), 0
    for doc in documents:
        for c in chunk_document(doc, max_chars, overlap):
            key = body_hash(c["text"])
            if key in seen:
                dropped += 1
                continue
            seen.add(key)
            out.append({
                "id": f"{doc['doc_id']}#{c['chunk_index']}",
                "doc_id": doc["doc_id"],
                "chunk_index": c["chunk_index"],
                "type": doc["type"],
                "t": doc["title"],
                "s": doc["source"],
                "u": doc["url"],
                "heading": c["heading"],
                "groups": doc["groups"],
                "also_called": doc["also_called"],
                "x": c["text"],
            })
    return out, dropped
