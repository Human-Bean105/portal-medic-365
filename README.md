# Medi (Portal Medic 365)

Medi is an AI health-information and wellbeing assistant built for the World AI Competition for Youth (WAICY) 2026.
People describe how they feel, by text or voice, in any of 12 languages. Medi checks for emergencies first, asks focused
questions, suggests one of four levels of care (emergency, urgent care, clinic, home care), explains possibilities without
diagnosing, and shows the trusted sources its answer is based on. A separate Wellbeing mode supports stress, mood, and
sleep, with immediate crisis-line support.

Medi is not a doctor and not a diagnostic system. Its results come from internal testing on synthetic cases, not clinical
validation.

Live: https://portal-medic-365.vercel.app

## How it works

```text
message -> validation -> safety screener (alerts sent immediately) -> analyzer (intent, facts, search terms)
        -> hybrid retrieval (embeddings + BM25) -> reranker -> evidence check -> GPT-4o (strict JSON, streamed)
        -> output safety checks -> answer with sources (or an honest "not in Medi's library" note)
```

- Knowledge base: 3,881 passages from 1,016 MedlinePlus health topics and 62 clinical guideline summaries, with source
  metadata (`rag/`).
- Safety: a deterministic screener that doesn't depend on any language model, emergency alerts before any other stage, and
  deterministic output checks (`medi/safety/`).
- Observability: a content-free trace of every stage, redacted server logs, and a developer dashboard (`/dev`).

Details: [Architecture](docs/ARCHITECTURE.md) · [Safety](docs/SAFETY.md) · [Security and privacy](docs/SECURITY_PRIVACY.md) ·
[API](docs/API.md) · [Evaluation report](docs/EVALUATION.md) · [Phase 0 audit](docs/AUDIT.md)

## Key results (internal, synthetic test sets)

| | v1 | Medi 2.0 |
|---|---|---|
| Retrieval Hit@5 / MRR (123 labeled queries) | 0.911 / 0.758 | 0.967 / 0.853 |
| Acceptable level of care (50 scenarios) | 98% | 100% |
| Emergencies recognized | 18/18 | 18/18 |
| Safety suite (31 documented cases) | 28/31 | 30/31 |
| Emergency alert reaches the screen | ~1.4 s | ~0.04 s |
| Unanswerable questions flagged as "not in library" | 0/9 | 8/9 |
| Time per answer (mean) | 3.1 s | 5.2 s |

End-to-end answer grounding was similar for v1 and 2.0 on these datasets (both clearly better than no retrieval). See the
evaluation report for the full picture, including limitations.

## Run locally

Requirements: Python 3.10+ (standard library only) and an OpenAI API key.

```bash
cd doctor
echo OPENAI_API_KEY=sk-... > .env          # never commit this file
python server.py                            # http://localhost:8785
```

Optional: `MEDI_DEV_TOKEN=...` in `.env` enables the developer dashboard at `/dev`.

## Tests and evaluation

```bash
python -m unittest discover -s tests -t .   # offline, no API key or cost
python evaluation/run_safety.py B E         # see docs/EVALUATION.md for all experiments
```

## Project layout

```text
medi/          backend pipeline (config, llm, intake, analyzer, orchestrator, safety/, rag/, web)
api/           Vercel function entry points
rag/           knowledge-base sources, index, and build script
evaluation/    datasets, experiment runners, metrics, judges, reports
tests/         offline unit tests
docs/          architecture, safety, privacy, API, evaluation
index.html     the app; dev.html the developer dashboard
eval/          v1 evaluation scripts and results (baseline record)
```

## Credits

Health information from [MedlinePlus.gov](https://medlineplus.gov) (U.S. National Library of Medicine). Clinical guideline
summaries adapted from [bshepp/clinical-decision-support-agent](https://github.com/bshepp/clinical-decision-support-agent)
(Apache License 2.0). Models by OpenAI.
