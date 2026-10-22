"""Builds Medi's retrieval index (run once, then commit rag/medi_index.json).

Sources:
- MedlinePlus health topics (U.S. National Library of Medicine), plain-language summaries. https://medlineplus.gov/xml.html
- 62 clinical guideline summaries from github.com/bshepp/clinical-decision-support-agent (Apache-2.0),
  each pointing to the original guideline publisher.

Usage (from the doctor/ folder):  python rag/build_index.py
"""
import base64
import html
import io
import json
import math
import re
import sys
import urllib.request
import zipfile
from array import array
from pathlib import Path
from xml.etree import ElementTree

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from api._medi import API_KEY  # noqa: E402

EMBED_MODEL = "text-embedding-3-small"
DIMS = 256
CHUNK_CHARS = 1100
GUIDELINES_URL = ("https://api.github.com/repos/bshepp/clinical-decision-support-agent/contents/"
                  "src/backend/app/data/clinical_guidelines.json")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Medi-RAG-builder (Portal Medic 365 student project)"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def html_to_text(fragment):
    text = re.sub(r"<li[^>]*>", "\n- ", fragment)
    text = re.sub(r"</(p|ul|ol|h\d)>|<br\s*/?>", "\n", text)
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def chunk(title, body):
    """Splits text into ~CHUNK_CHARS passages on line boundaries, each labeled with its topic."""
    parts, current = [], ""
    for line in body.splitlines():
        if current and len(current) + len(line) > CHUNK_CHARS:
            parts.append(current)
            current = ""
        current += ("\n" if current else "") + line
    if current:
        parts.append(current)
    return [f"{title}: {p}" for p in parts]


def medlineplus_chunks():
    page = fetch("https://medlineplus.gov/xml.html").decode("utf-8", "replace")
    links = sorted(set(re.findall(r'href="([^"]*mplus_topics_compressed_[\d-]+\.zip)"', page)), reverse=True)
    if not links:
        raise SystemExit("Couldn't find the MedlinePlus download link.")
    url = links[0] if links[0].startswith("http") else "https://medlineplus.gov/" + links[0].lstrip("/")
    print("Downloading", url)
    archive = zipfile.ZipFile(io.BytesIO(fetch(url)))
    root = ElementTree.fromstring(archive.read(archive.namelist()[0]))
    chunks = []
    for topic in root.iter("health-topic"):
        if topic.get("language") != "English":
            continue
        summary = topic.findtext("full-summary") or ""
        if not summary.strip():
            continue
        title = topic.get("title")
        aliases = [a.text for a in topic.findall("also-called") if a.text]
        body = html_to_text(summary)
        if aliases:
            body = f"Also called: {', '.join(aliases)}\n{body}"
        for text in chunk(title, body):
            chunks.append({"t": title, "s": "MedlinePlus (U.S. National Library of Medicine)", "u": topic.get("url"), "x": text})
    return chunks


def guideline_chunks():
    chunks = []
    for g in json.loads(base64.b64decode(json.loads(fetch(GUIDELINES_URL))["content"])):
        for text in chunk(g["title"], g["text"]):
            chunks.append({"t": g["title"], "s": f"{g['source']} (summary)", "u": g.get("url", ""), "x": text})
    return chunks


def embed(texts):
    vectors = []
    for start in range(0, len(texts), 200):
        batch = texts[start:start + 200]
        req = urllib.request.Request(
            "https://api.openai.com/v1/embeddings",
            data=json.dumps({"model": EMBED_MODEL, "input": batch, "dimensions": DIMS}).encode(),
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            vectors += [d["embedding"] for d in sorted(json.load(r)["data"], key=lambda d: d["index"])]
        print(f"  embedded {len(vectors)}/{len(texts)}")
    return vectors


def main():
    chunks = medlineplus_chunks()
    print(f"MedlinePlus: {len(chunks)} passages")
    guidelines = guideline_chunks()
    print(f"Guideline summaries: {len(guidelines)} passages")
    chunks += guidelines

    flat = array("f")
    for v in embed([c["x"] for c in chunks]):
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        flat.extend(x / norm for x in v)

    index = {
        "model": EMBED_MODEL,
        "dims": DIMS,
        "attribution": [
            "Health topic summaries courtesy of MedlinePlus.gov, U.S. National Library of Medicine (public domain).",
            "Clinical guideline summaries from github.com/bshepp/clinical-decision-support-agent, "
            "licensed under the Apache License 2.0; each links to the original guideline publisher.",
        ],
        "chunks": chunks,
        "vectors": base64.b64encode(flat.tobytes()).decode(),
    }
    out = HERE / "medi_index.json"
    out.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Saved {len(chunks)} passages to {out} ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
