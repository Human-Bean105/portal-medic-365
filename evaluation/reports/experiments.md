# End-to-end experiments A-E

Run 2026-11-01 18:22. Generator gpt-4o, helper gpt-4o-mini, judge gpt-4o. Dataset: scenarios-v1 (50 textbook vignettes, unchanged since the v1 evaluation). LLM-judge results assist grading but are not ground truth.

- **A**: A: LLM without RAG
- **B**: B: v1 basic RAG (old index, vector search)
- **C**: C: hybrid retrieval (new index)
- **D**: D: hybrid retrieval + reranking
- **E**: E: full pipeline (analyzer, hybrid, rerank, evidence check, output validation)

| Metric | A | B | C | D | E |
|---|---|---|---|---|---|
| conversations | 50 | 50 | 50 | 50 | 50 |
| failures | 0 | 0 | 0 | 0 | 0 |
| triage_acceptable_% | 98.0 | 98.0 | 98.0 | 98.0 | 100.0 |
| under_triage | 0 | 0 | 0 | 0 | 0 |
| over_triage | 1 | 1 | 1 | 1 | 0 |
| emergencies_detected | 17/18 | 18/18 | 18/18 | 18/18 | 18/18 |
| emergency_on_first_message | 17/18 | 18/18 | 18/18 | 18/18 | 18/18 |
| diagnosis_top1_% | 100.0 | 98.0 | 98.0 | 98.0 | 100.0 |
| diagnosis_listed_% | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| claims | 257 | 239 | 249 | 218 | 240 |
| grounded_claim_rate_% | 41.2 | 59.4 | 55.8 | 56.0 | 57.1 |
| standard_knowledge_% | 56.4 | 38.5 | 43.0 | 41.7 | 40.8 |
| unsupported_claim_rate_% | 2.3 | 2.1 | 1.2 | 2.3 | 2.1 |
| answers_with_unsupported_claim | 5 | 3 | 2 | 4 | 4 |
| answers_showing_sources | 0 | 48 | 49 | 48 | 50 |
| citation_support_rate_% | None | 90.9 | 92.6 | 93.1 | 89.5 |
| percentage_violations | 0 | 0 | 0 | 0 | 0 |
| specific_dose_mentions | 0 | 0 | 0 | 0 | 0 |
| turn_latency_ms_mean | 2282 | 3127 | 3015 | 4548 | 5224 |
| turn_latency_ms_p95 | 3095 | 4391 | 3945 | 5722 | 6201 |
| cost_usd_per_conversation | 0.0151 | 0.018 | 0.0173 | 0.0167 | 0.0192 |

## Cases to review

- A #3 Stroke: level emergency (correct, accepted emergency); fabricated: "Symptoms started 20 minutes ago." (The specific timing of 20 minutes is not mentioned in the reference passages.)
- A #7 Pulmonary embolism: level emergency (correct, accepted emergency); inaccurate: "Swollen and sore calf is a symptom of pulmonary embolism." (Swollen and sore calf is more directly associated with deep vein thrombosis (DVT), which can lead to pulmonary embolism if the clot travels to the lungs.)
- A #10 Ectopic pregnancy: level emergency (correct, accepted emergency); fabricated: "Sharp pain on the left side" (The reference mentions abdominal pain but does not specify 'sharp pain on the left side.')
- A #15 Heat stroke: level emergency (correct, accepted emergency); fabricated: "High body temperature (104F) is a symptom of heatstroke." (The reference states that body temperature may rise above 106 °F (41 °C) in heat stroke, not 104 °F.); fabricated: "Stopped sweating is a symptom of heatstroke." (The reference does not mention stopped sweating as a symptom of heat stroke.)
- A #16 Sepsis: level emergency (correct, accepted emergency); fabricated: "High fever of 102°F is a symptom of sepsis." (The passage mentions fever as a symptom of sepsis but does not specify a temperature of 102°F.)
- A #23 Possible ankle fracture: level emergency (over, accepted urgent_care)
- B #15 Heat stroke: level emergency (correct, accepted emergency); inaccurate: "Heat stroke is a life-threatening condition where the body temperature rises above 104°F, and symptoms include confusion, hot and dry skin, and lack of sweating." (The reference states that heat stroke is life-threatening with body temperature rising above 106°F, not 104°F. Symptoms include dry skin, a rapid, strong pulse, dizziness, nausea, and confusion, but it does not mention 'lack of sweating' as a symptom.)
- B #22 Cellulitis: level emergency (over, accepted urgent_care)
- B #24 Pneumonia: level emergency (correct, accepted urgent_care/emergency); fabricated: "Fever of 101.5F" (The specific fever temperature of 101.5F is not mentioned in the reference passage.); fabricated: "Cough with green phlegm" (The reference mentions cough with phlegm but does not specify the color green.); fabricated: "Shortness of breath walking around the house" (The reference mentions shortness of breath but does not specify it occurring while walking around the house.)
- B #29 Dehydration in a toddler: level urgent_care (correct, accepted urgent_care); fabricated: "No urination for 6 hours" (The passages mention no wet diapers for 3 hours as a sign of dehydration, but not 6 hours.)
- C #12 Severe asthma attack: level emergency (correct, accepted emergency); fabricated: "Used rescue inhaler 4 times without relief." (The specific detail of using a rescue inhaler 4 times without relief is not mentioned in the reference passages.); fabricated: "Can only say a few words at a time." (This specific symptom is not mentioned in the reference passages.)
- C #23 Possible ankle fracture: level emergency (over, accepted urgent_care)
- C #29 Dehydration in a toddler: level urgent_care (correct, accepted urgent_care); fabricated: "No wet diapers for 6 hours" (The reference mentions 3 hours as a threshold, not 6 hours.)
- D #4 Anaphylaxis: level emergency (correct, accepted emergency); fabricated: "Try to stay calm and avoid lying down flat." (This specific advice is not found in the reference passages.)
- D #15 Heat stroke: level emergency (correct, accepted emergency); fabricated: "Heat stroke is a life-threatening condition where the body temperature rises above 104°F, often with confusion and dry skin." (The reference states that heat stroke is life-threatening and body temperature may rise above 106°F, not 104°F.); fabricated: "Symptoms of heat stroke include confusion, hot and dry skin, stopped sweating, and a temperature of 104°F." (The reference mentions confusion and dry skin as symptoms, but it specifies a temperature above 106°F, not 104°F, and does not mention 'stopped sweating' explicitly.)
- D #23 Possible ankle fracture: level emergency (over, accepted urgent_care)
- D #29 Dehydration in a toddler: level urgent_care (correct, accepted urgent_care); fabricated: "No wet diapers for 6 hours is a red flag to watch for." (The passages mention 3 hours as a threshold for concern, not 6 hours.)
- D #45 Common cold: level home_care (correct, accepted home_care); fabricated: "High fever over 102°F" (The specific threshold of 102°F is not mentioned in the reference passages.)
- E #1 Concussion with red flags: level emergency (correct, accepted emergency); fabricated: "Avoid eating or drinking until evaluated after a head injury." (This specific advice is not found in the reference passages or standard medical guidelines.)
- E #15 Heat stroke: level emergency (correct, accepted emergency); inaccurate: "Heat stroke is a life-threatening condition where the body temperature rises above 104°F, often with confusion, hot and dry skin, and lack of sweating." (The reference states that heat stroke can cause body temperature to rise above 106°F, not 104°F. It also mentions dry skin and confusion as symptoms, but does not specify 'lack of sweating' as a symptom.)
- E #29 Dehydration in a toddler: level urgent_care (correct, accepted urgent_care); fabricated: "No wet diapers for 6 hours is a red flag to watch for." (The reference mentions no wet diapers for 3 hours as a sign of dehydration, not 6 hours.)
- E #41 Carpal tunnel syndrome: level clinic (correct, accepted clinic/home_care); fabricated: "Severe pain or swelling in the wrist is a red flag for carpal tunnel syndrome." (The passages do not mention severe pain or swelling as specific red flags for carpal tunnel syndrome.); fabricated: "Symptoms spreading to other fingers is a red flag for carpal tunnel syndrome." (The passages do not mention symptoms spreading to other fingers as a red flag for carpal tunnel syndrome.)
