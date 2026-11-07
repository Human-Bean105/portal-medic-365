# Medi (Portal Medic 365)

**WAICY 2026 — AI Showcase Track · Developer: Ethan Yiu-Sing Pan**
Live demo: https://portal-medic-365.vercel.app · Code: https://github.com/Human-Bean105/portal-medic-365

> Draft for the final submission. Every number below is traceable to a file in `evaluation/reports/` (see
> `docs/EVALUATION.md`). Check the official word limits before submitting and shorten sections 4 and 7 first if needed.

## 1. Project overview

Medi is an AI health-guidance and wellbeing assistant that makes health information more accessible, understandable, and
responsible. Instead of acting as an online doctor, it helps people organize their concerns, understand trustworthy health
information, and choose a sensible next step: an emergency, urgent care today, a regular clinic visit, or home care.

Medi combines a conversational AI, a retrieval system over a curated medical library, voice and multilingual interaction,
and a safety layer that does not depend on the AI model. Its central principle: **AI should help people navigate health
information, not replace professional medical judgment.**

## 2. Problem statement

People often struggle to know which symptoms matter, where to find trustworthy information, and whether they need care
now, later, or not at all. Emergency departments are crowded and primary care is hard to access (see references), so
people turn to search engines and general chatbots. General AI systems can give confident answers that are incomplete or
unsupported; in health, an answer that sounds convincing is not necessarily safe.

Medi addresses three connected problems:

| Problem | Who it affects | Medi features that address it |
|---|---|---|
| Health information is hard to understand or access, especially across languages | Patients and families, newcomers, people with limited English | Plain-language answers, 12 languages, voice, read-aloud, cited sources |
| People don't know what level of care to seek or how to prepare | Anyone deciding whether to go to the ER, urgent care, or a clinic | Focused symptom intake, four-level care guidance, nearby-care map, printable visit summary |
| AI answers need grounding, safety limits, and honest uncertainty | Every user of health AI | Retrieval from MedlinePlus and guideline summaries, emergency screener, output checks, "not in library" notes |

Intended users: teens and adults looking for health or wellbeing information for themselves or a family member, mainly in
Canada and the US (crisis lines and emergency numbers are set for these countries).

## 3. The solution

| Feature | What it does | User need |
|---|---|---|
| Health check | Conversational symptom intake, one or two focused questions at a time, possible explanations (never a diagnosis, never percentages), and a level of care with warning signs to watch | "Is this serious, and what should I do?" |
| Wellbeing mode | Supportive conversation about stress, mood, sleep, and loneliness; guided breathing and grounding; immediate 9-8-8 crisis support | Emotional support and a safe path to help |
| Voice calls | Hands-free spoken conversation with an animated avatar | Accessibility, people who prefer talking |
| Photo input | A photo of a rash, wound, or swelling is described and considered cautiously | Showing what's hard to describe |
| Nearby care map | Emergency rooms, urgent care, clinics, and pharmacies near a chosen location | Finding where to go |
| Visit summary | A printable doctor-style summary with questions to ask | Preparing for a real appointment |
| 12 languages | Interface and answers in English, French, Spanish, Simplified and Traditional Chinese, Punjabi, Hindi, Tagalog, Korean, Vietnamese, Farsi, Arabic | Language barriers |
| Family visits | Separate visits for "me" and "someone else"; the stored profile is never applied to another person | Caring for children or parents |

## 4. How the AI works

### 4.1 Architecture

```text
User message (text, voice, or photo)
  -> 1. Input validation            (only user/assistant messages, size limits)
  -> 2. Safety screener             (deterministic rules; alerts sent to the screen immediately, ~0.04 s)
  -> 3. Analyzer                    (intent, reported facts, what's missing, English search terms)
  -> 4. Hybrid retrieval            (meaning-based search + keyword search over 3,881 passages)
  -> 5. Reranker + evidence check   (grades passages; sufficient / partial / insufficient / none)
  -> 6. Answer generation           (GPT-4o, strict JSON format, streamed word by word)
  -> 7. Output safety checks        (citations, crisis line, emergency wording, doses, certainty)
  -> Answer with sources, level of care, and a limitation note when evidence is weak
```

If the screener finds an emergency, steps 3 and 5 are skipped so the emergency answer isn't delayed. If any AI step fails,
Medi still answers with less (and the safety screener still works, even when the AI service is down).

### 4.2 Models and why each was chosen

| Model | Role | Why |
|---|---|---|
| GPT-4o | Writes the answer, in a fixed JSON format (reply, level of care, possibilities, next steps, citations); reads photos | Strong reasoning and multilingual writing, supports strict structured output and images |
| GPT-4o-mini | Analyzer, reranker, and translating non-English messages for the safety check | Fast and inexpensive for small, well-defined tasks |
| text-embedding-3-small (256 dimensions) | Turns passages and questions into vectors for meaning-based search | Good retrieval quality at low cost; small vectors keep the index in plain Python |
| gpt-realtime | Live voice conversation | Natural, low-latency speech in and out |
| gpt-4o-mini-transcribe | Transcribes the person's speech during calls | Needed to screen and search what was said |
| gpt-4o-mini-tts | Reads typed answers aloud | Natural voice with a calm, clinical speaking style |

**Pretrained vs. custom.** All models are pretrained by OpenAI; Medi does not train a model. Custom-developed parts: the
pipeline and orchestration, the safety screener and output checks, the knowledge-base ingestion and chunking, BM25 keyword
search and score fusion, the evidence-sufficiency logic, prompts and output schemas, the frontend, and the evaluation framework.

### 4.3 Retrieval, with a real example

The knowledge base holds 3,881 passages from **1,016 MedlinePlus health topics** (U.S. National Library of Medicine,
public domain) and **62 clinical guideline summaries** (Apache-2.0), each with its source, URL, section, and topic groups.

For "what is an A1C test", the analyzer adds search terms and topic names; the system then scores every passage two ways
and combines them (70% meaning, 30% keywords). Actual scores from the developer dashboard:

| Passage | Meaning (cosine) | Keyword (BM25) | Combined | Reranker grade |
|---|---|---|---|---|
| A1C | 0.74 | 25.6 | 1.00 | 3 (answers it) |
| Blood Glucose (section "When and how should I check my blood glucose?") | 0.55 | 17.6 | 0.71 | 3 |

The best five passages (at most two per topic) are inserted into GPT-4o's instructions as numbered reference material. The
model must list the numbers it relied on; Medi maps them back to the real passages and shows them as "📚 Sources", so a
citation can never point to a source that wasn't retrieved.

**When retrieval fails.** For "how many milligrams of melatonin can a 4 year old take", the library only partly covers the
question. The evidence check rates it *partial*, the model is told not to present specifics as sourced, and the person sees
"Medi's reference library only partly covers this question." For "what are the side effects of metformin", the passages found were
only loosely related (grade 1), so the evidence was rated *insufficient*: the answer cited nothing and the note said it is
general guidance. Passages graded 0 (not relevant) are withheld from the model entirely. On 9 unanswerable questions, Medi showed this note 8 times; the original version never did.

## 5. AI concepts demonstrated

Natural language processing (intent detection and information extraction); semantic search with embeddings; keyword
retrieval (BM25) and score fusion; retrieval-augmented generation with grounded citations; reranking; generative AI with
structured output; multimodal interaction (voice and images); AI-assisted decision support without diagnosis; and
evaluation methods (retrieval metrics, controlled experiments, LLM-as-judge with human review of the judge).

## 6. Safety, ethics, and responsible AI

### 6.1 Emergency awareness, and where it can fail

A rule-based screener checks every message, in every language, for signs such as chest pain, trouble breathing, stroke signs,
severe allergic reactions, overdose, and suicidal thoughts. It doesn't use an AI model, so it can't be talked out of a warning
and works even if the AI service is down. Alerts open a "Call 911" or "9-8-8" screen before Medi finishes thinking.

Limits: the rules alone catch 12 of the 18 emergency test scenarios (up from 6 after widening them from Medi's clinical
red-flag list); GPT-4o catches the rest, so emergency detection relies on both layers and is not perfect. On all labeled test
messages the rules catch 79% of emergencies with a 2% false-alarm rate. General questions ("how is a stroke treated?") no
longer trigger the emergency screen, but crisis and self-harm rules always apply.

### 6.2 Not a diagnostic tool

Medi never confirms a diagnosis, never gives probabilities, never invents doses, and always says a text conversation can't
replace an examination. It presents possibilities labeled "possibility", "probable explanation", or "important to rule out".

### 6.3 Communicating uncertainty

Each possibility lists what supports and what weakens it, and what's still unknown. When the library doesn't cover a
question, the person is told. Automatic checks flag percentages, specific doses, and overconfident wording.

### 6.4 Wellbeing safeguards

Wellbeing mode listens first, never diagnoses or gives medication advice, and redirects physical symptoms to care. Any sign of
suicide, self-harm, harm to others, or abuse brings up 9-8-8 and 911 (and Kids Help Phone for youth); a code-level backstop
adds the crisis line if the model ever leaves it out.

### 6.5 Privacy (actual behavior, verified in the code)

| Question | Answer |
|---|---|
| What is collected? | The conversation (text and any photo), an optional self-entered health profile, the chosen language, and a typed map location. No account, name, or contact details. |
| Are conversations or images stored? | Not by Medi. The server has no database. The conversation lives in the browser for the current visit; the profile and language are saved in the browser's local storage on the device. |
| Which external services receive information? | **OpenAI** receives the conversation, photos, and (for "me" visits) the profile to generate answers, and voice audio during calls. **Google Maps** receives the location typed into the map. **Vercel** hosts the app. |
| How long is information kept? | Medi keeps nothing after the request. Server logs record only timings, counts, and scores, never message text or health details (enforced in code and by a test). OpenAI's and Vercel's retention follows their own policies and account settings; check the current OpenAI API data-retention settings for this account before stating a number. |
| What controls do users have? | "New visit" clears the conversation; the profile can be cleared in its form or by clearing browser data. The profile is optional and only used for "me" visits. |

Medi doesn't promise confidentiality and makes no regulatory compliance claims.

### 6.6 Bias and language limitations

The library is U.S.-based and English-only; non-English questions are searched in English. Crisis numbers are for Canada
and the US. Multilingual tests used machine translations, not native speakers. Test cases were written by the developer and
may not represent all ages, cultures, or ways of describing symptoms.

### 6.7 Risk register

| Risk | Safeguard | Remaining gap |
|---|---|---|
| Missed emergency | Rule-based screener + model instructions + output check | Rules alone miss 21% of test emergencies; tested only on synthetic cases |
| Unnecessary emergency alert | General-question exception, negation and exertion rules | 2% false alarms on test messages |
| Unsupported medical claim | Retrieval, citations limited to retrieved passages, evidence check, judged tests | Judge is an AI model; some imprecisions remain |
| Over-triage (unneeded ER visit) | Four defined care levels with examples | 1 over-triage per 50 cases in some runs |
| Crisis handled badly | Screener, crisis screen, guaranteed 9-8-8 | Synthetic tests only |
| Wrong language in an emergency | Explicit instruction, multilingual test | Machine-translated tests |
| Prompt injection | Server rejects client system messages; refusal tested | Not exhaustively tested |
| Privacy leak via logs | Redacted logs, test | Third-party retention outside Medi's control |

## 7. Testing and evaluation

All test data is synthetic. Methodology, definitions, and per-case results are in `docs/EVALUATION.md`.

**Retrieval** (135 labeled questions; same input for every method):

| | Original (v1) | Medi 2.0 |
|---|---|---|
| Hit@5 (a right topic in the top 5) | 0.911 | 0.967 |
| Precision@5 | 0.53 | 0.65 |
| MRR (how high the first right topic ranks) | 0.758 | 0.853 |

A held-out check confirmed the improvement wasn't tuned to the test set.

**Controlled experiment** (same 50 symptom scenarios and grading for five configurations):

| | No RAG | v1 RAG | Medi 2.0 |
|---|---|---|---|
| Acceptable level of care | 98% | 98% | 100% |
| Under-triage | 0 | 0 | 0 |
| Emergencies recognized | 17/18 | 18/18 | 18/18 |
| Medical claims backed by a reference | 41% | 59% | 57% |
| Answers showing sources | 0/50 | 48/50 | 50/50 |

**Unsupported claims.** This replaces the earlier 0/228 vs 5/224 comparison, which used different question sets. Now every
configuration answers the same questions. An AI judge first flagged 28 claims; on hand review, 23 of them were judge errors,
such as Medi repeating the person's own details or using standard clinical thresholds. That left 0-3 genuinely questionable
claims per 50 conversations in every configuration. On 26 knowledge questions, the unsupported-claim rate was 1.7% without
RAG, 0.8% with v1 RAG, and 0% with Medi 2.0.

**Safety suite**: 31 cases with written expected behavior (emergencies, vague messages, diagnosis demands, unsafe medication
requests, misleading framing, prompt injection, wellbeing crises, off-topic requests): **30/31** passed. The suite found
real gaps in the emergency rules (for example "I've been thinking about killing myself" wasn't matched), which were fixed.

**Multilingual** (8 questions in all 12 languages): replies in the right language 96/96, safety alerts 24/24, crisis line
12/12, acceptable level of care 59/60.

**Speed**: emergency alerts appear in about 0.04 s (was 1.4 s); a full answer takes about 5 s (was 3 s), the price of the
extra checking steps.

**Limitations**: small, synthetic, developer-written test sets; AI judges from the same model family; no clinician review;
machine-translated language tests. These results are not clinical validation and don't show Medi is safe for independent
medical use.

## 8. Technical contribution and originality

How Medi differs from asking a general chatbot (measured in the experiment above, "No RAG" = the same model without Medi's
pipeline): it shows sources on every answer, recognized one more emergency, and tells people when its library doesn't cover a
question. It also declines off-topic requests (the earlier version wrote a requested poem) and has a safety net that works
even without the AI model.

Distinctive design decisions: a safety layer independent of the language model that acts before anything else; mode-specific
search weighting (wellbeing language is everyday wording, so keywords count less); evidence status decided by a reranker
rather than raw similarity, because testing showed similarity scores barely separated good from bad results; withholding
irrelevant passages instead of letting the model see them; and measuring every component before keeping it (a faster
reranker setting was rejected because it lowered precision).

## 9. Development and implementation

- Frontend: one HTML/JavaScript page (`index.html`) and a developer dashboard (`dev.html`).
- Backend: Python standard library only (`medi/` package, 49 automated tests), running as Vercel serverless functions.
- Knowledge base and evaluation: `rag/`, `evaluation/`.
- Tested failure cases: unavailable AI service (friendly message, safety screener still works), empty or irrelevant
  retrieval, malformed requests, oversized uploads, injected system messages.

**Development process.** [Ethan: describe honestly what you designed, decided, built, and tested yourself, and how AI coding
tools were used, following the WAICY rules on AI assistance.]

## 10. Limitations and future development

- Reliability: larger and more varied test sets; human review of the exported answer sample.
- Safety: more emergency and crisis phrasings; measure unnecessary escalations; fix the open headache-and-stiff-neck case.
- Privacy: verify third-party retention settings; add a platform-level rate limit.
- Accessibility: test with native speakers of each language and with users with different accessibility needs.
- Independent review: qualified clinical review of content, evaluation, and safety boundaries before any real-world use.
- User experience: structured usability testing of whether people understand the guidance and its limits.

## 11. Demonstration plan

1. **Health check**: "I twisted my ankle playing soccer, it's swollen" → follow-up question → urgent care, sources shown.
2. **RAG**: in the developer dashboard (`/dev`), show the A1C passages and scores; then the melatonin question showing the
   *partial* evidence note.
3. **Safety**: "I have crushing chest pain spreading to my left arm" → the 911 screen appears before the answer. Say that
   tests don't prove perfect detection.
4. **Accessibility**: switch the language to Spanish or Chinese, or start a voice call.

## 12. References

MedlinePlus — Symptoms; MedlinePlus — Health Topics; CDC — Respiratory Illnesses; CDC — COVID-19 Symptoms; CTV News —
"Emergency room wait times up by 30 per cent: report"; PBS NewsHour — "Why America faces a primary care shortage – and why
it matters"; Vox — "How America is failing its rural hospitals"; NBC News — "Primary care doctor shortage worsening across
U.S." [Add links and dates; check each source supports the claim it's cited for.]

## 13. Conclusion

Medi explores how AI can make health information more accessible and understandable while taking the risks of generative AI
in health seriously. Its contribution isn't replacing healthcare professionals; it's a more responsible, measurable, and
transparent way for people to interact with health information.

*Medi: making health guidance more accessible, understandable, and responsible for everyone.*
