"""The pipeline configurations compared in the end-to-end experiments (PRD section 8.2)."""
from medi.config import DEFAULT

_OFF = dict(analyzer=False, rerank=False, evidence=False, validate=False)

EXPERIMENTS = {
    "A": DEFAULT.but(name="A: LLM without RAG", rag=False, **_OFF),
    "B": DEFAULT.but(name="B: v1 basic RAG (old index, vector search)", index="rag/medi_index_v1.json",
                     retriever="vector", min_score=0.3, **_OFF),
    "C": DEFAULT.but(name="C: hybrid retrieval (new index)", **_OFF),
    "D": DEFAULT.but(name="D: hybrid retrieval + reranking", **{**_OFF, "rerank": True}),
    "E": DEFAULT.but(name="E: full pipeline (analyzer, hybrid, rerank, evidence check, output validation)"),
}
