# Medi 2.0 evaluation report

Runs: 2026-10-31 to 2026-11-01. Generator `gpt-4o`, helper `gpt-4o-mini`, embeddings `text-embedding-3-small`, LLM judge
`gpt-4o`. All test data is synthetic. These are internal engineering results on textbook-style cases, **not clinical
validation**. Raw per-case results are in `evaluation/reports/`.

## Summary

| Question | Answer |
|---|---|
| Does the new retrieval find better references? | Yes. Hit@5 0.911 → 0.967, Precision@5 0.53 → 0.65, MRR 0.758 → 0.853 (123 labeled queries, held-out check passed). |
| Does it change answer grounding end-to-end? | Not measurably on these datasets. Any RAG beats no RAG (grounded claims 41% → 57-59% on triage cases, 50% → 61-62% on knowledge questions); the full pipeline and v1 are similar. |
| Is emergency handling faster and independent of the model? | Yes. Alerts reach the browser in ~40 ms instead of ~1.4 s, before retrieval starts. |
| Does Medi admit when it doesn't know? | Yes. On 9 unanswerable health questions all configurations avoided stating specifics as fact; only the full pipeline told the person (8/9). |
| Safety suite (31 documented cases) | Full pipeline 30/31; v1 28/31 (both share the improved screener). |
| Multilingual (8 questions x 12 languages) | Language correct 96/96, safety alerts 24/24, crisis line 12/12, acceptable level 59/60, relevant references 95/96. |
| Cost | About 1.7 s more per answer than v1 (mostly the reranker), similar cost (~$0.012-0.019 per answer at list prices). |

## 1. Baseline (v1, before changes)

Recorded on 2026-10-31 at commit `d1aba05` (`eval/`; those scripts ran against the pre-refactor code): 50 scenarios,
96-98% acceptable level of care across seven earlier rounds, 18/18 emergencies, 0 under-triage; first-message latency mean 3.3 s, p95 4.4 s (screen 0 ms, query rewrite 0.97 s,
retrieval 0.32 s, generation 2.0 s); about 4,200 prompt tokens per turn.

## 2. Retrieval benchmark

**Dataset** (`evaluation/datasets/retrieval_benchmark.json`, version r1): 135 synthetic queries: the 50 triage scenarios,
28 everyday-symptom wordings, 18 education questions, 19 wellbeing messages, 8 guideline questions, and 12 out-of-scope
questions with no relevant topic. Relevance labels (1-3 "primary" topics and up to 5 "related" per query) were produced by
`gpt-4o` from the full list of 1,078 topic titles, without seeing any retriever's output, then spot-checked; 4 labels were
corrected by hand (recorded in the file). They are silver labels, not clinician-reviewed.

**Metrics** (`evaluation/metrics.py`, topic level, out-of-scope queries excluded):
- *Hit@k*: 1 if any of the top k passages belongs to a primary topic.
- *Recall@k*: share of primary topics present in the top k.
- *Precision@k*: share of the k slots filled by a primary or related topic (empty slots count as misses).
- *MRR@10*: 1 / rank of the first primary-topic passage, 0 if none in the top 10.

**Retrievers** (same stored query and embedding for every configuration; `retrieval_retrievers.md`):

| Configuration | Hit@5 | Recall@5 | Precision@5 | MRR@10 |
|---|---|---|---|---|
| v1: vector search, old index, 0.3 cutoff | 0.911 | 0.812 | 0.530 | 0.758 |
| Vector, new index | 0.919 | 0.812 | 0.561 | 0.796 |
| BM25 keyword only | 0.821 | 0.713 | 0.470 | 0.661 |
| Hybrid, reciprocal rank fusion | 0.927-0.935 | 0.827-0.831 | 0.584-0.589 | 0.788-0.792 |
| **Hybrid, weighted 0.7 (0.9 for wellbeing)** | **0.943** | **0.843** | **0.598** | **0.829** |

Wellbeing messages were the weak spot for keyword matching (hit@5 0.79 with equal weighting); a higher vector weight in
Wellbeing mode fixed this (0.95).

**Chunking** (`retrieval_chunking.md`): 600, 900, 1,100, 1,200, and 1,500 characters, with and without one sentence of
overlap. 600 had the best precision (0.62), 1,200 the best hit rate (0.959). **Held-out check** (`retrieval_heldout.txt`):
choosing on one half of the queries and testing on the other, the chosen hybrid setting beat v1 on both halves (MRR
0.83/0.82 vs 0.77/0.74), but the ranking among the top few settings flipped between halves, so those differences are noise.
900 characters was kept for its lower prompt size.

**Analyzer and reranker** (`retrieval_ablation.md`):

| Search terms | Reranker | Hit@5 | Recall@5 | Precision@5 | MRR@10 |
|---|---|---|---|---|---|
| v1 rewrite | no | 0.943 | 0.843 | 0.598 | 0.829 |
| v1 rewrite | yes | 0.951 | 0.847 | 0.646 | 0.877 |
| analyzer | no | 0.935 | 0.818 | 0.579 | 0.809 |
| **analyzer** | **yes (production)** | **0.967** | **0.873** | **0.647** | **0.853** |

A smaller reranker job (10 passages of 300 characters) was 0.45 s faster but lost precision (0.615), so it wasn't adopted.
Repeated runs vary by about one query because model outputs aren't perfectly deterministic.

**Evidence sufficiency** (`evidence_calibration.md`): answerable queries rated *sufficient* had a primary topic in the top 5
98.3% of the time (117 queries); *partial* 80% (5). Of 12 out-of-scope queries, 11 were not rated sufficient (6 partial,
1 insufficient, 4 none). Raw cosine similarity of the top passage separated poorly (hit rates 93-98% in every score band).

## 3. End-to-end experiments A-E (`experiments.md`)

Same 50 scenarios, same follow-up message, same grading. Grounding is judged against the same reference passages for every
configuration (the production retriever's top 5 for the scenario plus whatever that configuration retrieved).

| Metric | A: no RAG | B: v1 RAG | C: hybrid | D: + rerank | E: full |
|---|---|---|---|---|---|
| Acceptable level of care | 98% | 98% | 98% | 98% | **100%** |
| Under-triage | 0 | 0 | 0 | 0 | 0 |
| Emergencies recognized | 17/18 | 18/18 | 18/18 | 18/18 | 18/18 |
| Expected condition listed | 100% | 100% | 100% | 100% | 100% |
| Grounded claim rate | 41.2% | 59.4% | 55.8% | 56.0% | 57.1% |
| Unsupported claim rate (judge) | 2.3% | 2.1% | 1.2% | 2.3% | 2.1% |
| Answers showing sources | 0 | 48 | 49 | 48 | 50 |
| Citation support rate | n/a | 90.9% | 92.6% | 93.1% | 89.5% |
| Percentages / specific doses | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| Mean / p95 seconds per turn | 2.3 / 3.1 | 3.1 / 4.4 | 3.0 / 3.9 | 4.5 / 5.7 | 5.2 / 6.2 |

*Grounded claim rate*: supported claims / all extracted medical claims. *Unsupported*: (inaccurate + fabricated) / all.
*Citation support*: cited passages the judge found supporting the answer / all cited passages.

**Reviewing the judge.** The 28 claims flagged as unsupported across all five configurations were reviewed by hand: 8 were
Medi restating the person's own details ("used my inhaler 4 times"), 10 were standard clinical thresholds the judge compared
against a single passage (heat stroke above 104°F, no wet diapers in 6 hours, fever over 102°F), 1 was a classic symptom,
and 5 were arguable real imprecisions (A: 1, D: 1, E: 3). The judge prompt was then revised (version 2) to stop extracting
restated details. Conclusion: genuine unsupported claims were 0-3 per 50 conversations in every configuration.

**Interpretation.** These textbook cases are ones gpt-4o already handles well, and v1 retrieval already found the right
topic for 94% of them, so better retrieval had little room to change the answers. The measurable end-to-end gains of the
full pipeline are 100% acceptable triage in this run, sources shown on every answer, faster emergency alerts, and honest
limitation notes. This run used the code before the final screener and language fixes; a rerun on the final code stopped
at 175/250 conversations when the API account ran out of credits.

## 4. Knowledge and unanswerable questions (`knowledge.md`)

26 education and guideline questions plus 9 health questions the knowledge base can't answer (specific doses,
supplement interactions, niche facts). Judge prompt v2.

| Metric | A: no RAG | B: v1 RAG | E: full |
|---|---|---|---|
| Grounded claim rate | 50.4% | 62.2% | 60.9% |
| Unsupported claim rate | 1.7% | 0.8% | 0.0% |
| Unanswerable: honest about limits | 9/9 | 9/9 | 9/9 |
| Unanswerable: shows "not in Medi's library" note | 0/9 | 0/9 | 8/9 |
| Mean / p95 seconds | 1.8 / 2.4 | 2.8 / 3.6 | 4.6 / 5.6 |

Without RAG, one answer named macrolides as first-line pneumonia treatment for healthy adults, contradicting the guideline
summary (amoxicillin or doxycycline); with retrieval this didn't occur.

## 5. Safety suite (`safety.md`)

31 cases, each with a documented expected behavior (`evaluation/datasets/safety_cases.py`); a case passes only if every
deterministic check and the judged requirement pass.

| Category | B: v1 RAG | E: full |
|---|---|---|
| Emergencies (6) | 6 | 6 |
| Ambiguous / incomplete (4) | 4 | 4 |
| Diagnosis demands (2) | 1 | 1 |
| Unsafe treatment requests (4) | 4 | 4 |
| Misleading framing (2) | 2 | 2 |
| Prompt injection (2) | 2 | 2 |
| Wellbeing crisis, limits, physical (9) | 9 | 9 |
| Non-health requests (2) | 0 | 2 |
| **Total** | **28/31** | **30/31** |

Before the screener fixes it found, the scores were 23/31 and 25/31. Remaining failure (both): headache with stiff neck plus
a demand for a definitive diagnosis got a clarifying question instead of an urgent recommendation.

## 6. Multilingual (`multilingual.md`)

8 questions (emergency, crisis, five symptom or education questions, stress) machine-translated into the 11 other app
languages (not checked by native speakers), run through the full pipeline with that language as the app language.

| Check | Result |
|---|---|
| Reply in the person's language | 96/96 |
| Coherent answer to the question | 96/96 |
| Safety screener fired (emergency, crisis) | 24/24 |
| Crisis reply includes 9-8-8 | 12/12 |
| Acceptable level of care | 59/60 |
| A relevant topic retrieved | 95/96 |

The first run found the Traditional Chinese emergency reply in English (the model copied the English emergency sentence);
the language instruction was fixed and the rerun passed. Mean time per answer was 5-7 s depending on language (translation
for the safety check adds time).

## 7. Performance

| Measure | v1 | Full pipeline |
|---|---|---|
| Emergency alert reaches the browser | ~1.4 s (English), ~2.2 s (Spanish) | 0.04 s (English), 0.7 s (Spanish) |
| First words of the reply (streamed) | ~1.7-2.4 s | ~3.3-3.8 s |
| Full answer, mean / p95 | 3.1 / 4.4 s | 5.2 / 6.2 s |
| Stage times (typical) | rewrite 1.0 s, retrieval 0.3 s, generation 2.0 s | analyzer 1.0 s, retrieval 0.3 s, reranker 1.4 s, generation 1.8 s |
| Prompt tokens per turn | ~4,200 | ~4,000-6,000 |
| Estimated cost per conversation (list prices) | $0.018 | $0.019 |
| Cold start (index load + keyword index) | n/a | ~0.4 s once per server instance |

## 8. Reproducing

From the `doctor/` folder with `OPENAI_API_KEY` set:

```bash
python -m unittest discover -s tests -t .          # 49 offline tests, no API key needed
python evaluation/retrieval_bench.py               # retrievers (and --chunking for chunk sizes)
python evaluation/heldout_check.py retrievers chunking
python evaluation/retrieval_ablation.py            # analyzer and reranker
python evaluation/calibrate_evidence.py
python evaluation/run_experiments.py A B C D E     # ~250 conversations, ~$10
python evaluation/run_knowledge.py
python evaluation/run_safety.py B E
python evaluation/run_multilingual.py
```

Chunking variants are rebuilt with `python rag/build_index.py --max-chars N --overlap M --out evaluation/indexes/cN_oM.json`.
A blinded sample of 30 answers for human review is in `evaluation/reports/human_review_sample.csv` (configuration key in
`human_review_key.csv`); it has not been reviewed yet.

## 9. Limitations

- Synthetic, developer-written test cases; silver relevance labels; LLM judges from the same model family as the generator.
  The hand review above shows the judge's false-positive rate is high for "unsupported" claims.
- 50 scenarios and 31 safety cases are small: a difference of one or two cases is within noise.
- Multilingual questions were machine-translated and not reviewed by native speakers; only 8 questions per language.
- No clinician has reviewed the scenarios, labels, or answers. Nothing here is evidence of clinical accuracy.
