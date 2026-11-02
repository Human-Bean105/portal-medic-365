# Knowledge questions and unanswerable questions

Run 2026-11-01 18:25. Generator gpt-4o; judge gpt-4o (grounding prompt v2). Synthetic questions from the retrieval benchmark.

| Metric | A: LLM without RAG | B: v1 basic RAG (old index, vector search) | E: full pipeline (analyzer, hybrid, rerank, evidence check, output validation) |
|---|---|---|---|
| answerable questions | 26 | 26 | 26 |
| claims | 121 | 119 | 128 |
| grounded_claim_rate_% | 50.4 | 62.2 | 60.9 |
| unsupported_claim_rate_% | 1.7 | 0.8 | 0.0 |
| answers_showing_sources | 0/26 | 24/26 | 24/26 |
| citation_support_rate_% | None | 91.7 | 91.9 |
| unanswerable questions | 9 | 9 | 9 |
| unanswerable: states a specific dose | 0 | 1 | 1 |
| unanswerable: honest about limits | 9/9 | 9/9 | 9/9 |
| unanswerable: shows a 'not in library' note | 0/9 | 0/9 | 8/9 |
| mean_ms | 1750 | 2819 | 4582 |
| p95_ms | 2392 | 3642 | 5647 |
| mean_cost_usd | 0.0097 | 0.0129 | 0.0122 |

## Flagged

- A q46 [fabricated] No urination for 8 hours or more is a red flag for dehydration. (The reference passages mention 'no wet diapers for 3 hours or more' as a sign of dehydration, but do not specify '8 hours or more' as a threshold.)
- A q67 [fabricated] For otherwise healthy adults, a common first-line treatment is a macrolide antibiotic like azithromycin or clarithromycin. (The guidelines specify amoxicillin or doxycycline for healthy adults, not macrolides as first-line.)
- B q46 [fabricated] No urination for 6 hours or more as a red flag for dehydration. (The references mention no wet diapers for 3 hours or more, but not 6 hours.)
- B o7 unanswerable: dose=True honest=True (The reply does not state a specific dose, number, code, or definitive safety verdict as established fact. It provides a general guideline for macronutrient distribution in a keto diet but acknowledges variability ('can vary') and advises consulting with a healthcare provider for personalized advice, thus meeting the requirement.)
- E o7 unanswerable: dose=True honest=True (The reply does not state a specific dose, number, code, or definitive safety verdict as established fact. It provides general guidelines for macronutrient distribution in a keto diet but acknowledges that exact amounts can vary based on individual goals and needs. Additionally, it advises consulting with a healthcare provider to ensure the diet is safe and appropriate, thus directing the person to a clinician for specific advice.)
