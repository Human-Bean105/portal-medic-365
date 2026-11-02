"""Builds Medi's retrieval index.

Sources:
- MedlinePlus health topics (U.S. National Library of Medicine), public domain. https://medlineplus.gov/xml.html
- 62 clinical guideline summaries from github.com/bshepp/clinical-decision-support-agent (Apache-2.0),
  each pointing to the original guideline publisher.

The downloaded documents are saved to rag/sources.json (the pinned dataset version), so every chunking setting is
built from exactly the same text. Use --refresh to download a new snapshot.

Usage (from the doctor/ folder):
  python rag/build_index.py                         # production index: rag/medi_index.json
  python rag/build_index.py --max-chars 600 --overlap 0 --out evaluation/indexes/c600_o0.json
"""
import argparse
import base64
import json
import math
import sys
import time
from array import array
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from medi import llm  # noqa: E402
from medi.rag import ingestion  # noqa: E402
from medi.rag.chunking import build_chunks  # noqa: E402

DIMS = 256
SOURCES = HERE / "sources.json"


def load_sources(refresh):
    if SOURCES.exists() and not refresh:
        return json.loads(SOURCES.read_text(encoding="utf-8"))
    mlp, mlp_info = ingestion.medlineplus_documents()
    gl, gl_info = ingestion.guideline_documents()
    data = {"downloaded": time.strftime("%Y-%m-%d"), **mlp_info, **gl_info, "documents": mlp + gl}
    SOURCES.write_text(json.dumps(data, ensure_ascii=False, indent=0), encoding="utf-8")
    return data


def embed_all(texts):
    vectors = []
    for start in range(0, len(texts), 200):
        vectors += llm.embed(texts[start:start + 200], DIMS, timeout=120, retries=6)
        print(f"  embedded {len(vectors)}/{len(texts)}")
    return vectors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-chars", type=int, default=900)
    ap.add_argument("--overlap", type=int, default=1)
    ap.add_argument("--out", default=str(HERE / "medi_index.json"))
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()

    sources = load_sources(args.refresh)
    docs = sources["documents"]
    chunks, dropped = build_chunks(docs, args.max_chars, args.overlap)
    print(f"{len(docs)} documents -> {len(chunks)} passages ({dropped} duplicates removed)")

    flat = array("f")
    for v in embed_all([c["x"] for c in chunks]):
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        flat.extend(x / norm for x in v)

    index = {
        "version": 2,
        "model": "text-embedding-3-small",
        "dims": DIMS,
        "built": time.strftime("%Y-%m-%d"),
        "chunking": {"max_chars": args.max_chars, "overlap_sentences": args.overlap},
        "sources": {k: v for k, v in sources.items() if k != "documents"},
        "attribution": [
            "Health topic summaries courtesy of MedlinePlus.gov, U.S. National Library of Medicine (public domain).",
            "Clinical guideline summaries from github.com/bshepp/clinical-decision-support-agent, "
            "licensed under the Apache License 2.0; each links to the original guideline publisher.",
        ],
        "documents": {d["doc_id"]: {k: d[k] for k in ("type", "source", "title", "url", "groups", "date_created", "snapshot_date")}
                      for d in docs},
        "chunks": chunks,
        "vectors": base64.b64encode(flat.tobytes()).decode(),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Saved {out} ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
