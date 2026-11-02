"""Optional reranking: a small model reads the top candidate passages and grades how well each one answers the
question. It's kept in the pipeline only because the retrieval benchmark shows it helps (see evaluation/reports)."""
import json

from .. import config, llm

SCHEMA = {
    "name": "passage_grades",
    "strict": True,
    "schema": {
        "type": "object", "additionalProperties": False, "required": ["grades"],
        "properties": {"grades": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["n", "grade"],
            "properties": {"n": {"type": "integer"}, "grade": {"type": "integer", "enum": [0, 1, 2, 3]}},
        }}},
    },
}
PROMPT = """Grade how useful each numbered reference passage is for answering the person's health question.
3 = directly about their main concern and answers it; 2 = about their concern or a likely cause, partly useful;
1 = loosely related; 0 = not relevant. Grade every passage. Judge relevance only, not writing quality."""


def rerank(question, passages, usage=None, chars=450):
    """Returns the passages sorted by grade (ties keep retrieval order), each with a "grade" field."""
    if not passages:
        return []
    listing = "\n\n".join(f"[{n}] {p['t']}: {p['x'].split(': ', 1)[-1][:chars]}" for n, p in enumerate(passages, 1))
    out = json.loads(llm.chat_text({
        "model": config.FAST_MODEL,
        "temperature": 0,
        "messages": [{"role": "system", "content": PROMPT},
                     {"role": "user", "content": f"QUESTION:\n{question}\n\nPASSAGES:\n{listing}"}],
        "response_format": {"type": "json_schema", "json_schema": SCHEMA},
    }, timeout=15, usage=usage))
    grades = {g["n"]: g["grade"] for g in out["grades"]}
    graded = [{**p, "grade": grades.get(n, 0)} for n, p in enumerate(passages, 1)]
    return sorted(graded, key=lambda p: -p["grade"])
