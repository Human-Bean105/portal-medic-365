# Judge Q&A practice notes

Short, honest answers, each pointing to evidence. Rehearse them out loud; don't memorize word for word.

**1. Isn't this just ChatGPT with a nicer interface?**
No. The same GPT-4o without Medi's pipeline ("No RAG" in the experiments) showed sources on 0 of 50 answers and missed one of
18 emergencies; Medi showed sources on 50/50 and caught 18/18. Medi also has a rule-based safety layer that works even when
the AI is down, checks every answer before showing it, and says when its library doesn't cover a question (8 of 9 times).
Evidence: `docs/EVALUATION.md` sections 3-4.

**2. What did you build yourself, and what is from OpenAI?**
The models are OpenAI's and pretrained. I built the pipeline that connects them: the safety screener and output checks,
the knowledge-base ingestion and chunking, keyword search and score fusion, the evidence check, the prompts and output
formats, the app, and the evaluation framework. [Be ready to say honestly how you used AI coding tools.]

**3. How does RAG work in Medi, in simple terms?**
Medi has a library of 3,881 short passages from MedlinePlus and guideline summaries. For each question it finds the
passages that match by meaning and by keywords, asks a small model to grade which ones actually answer the question, and
gives the best ones to GPT-4o as reference material. GPT-4o has to say which passages it used, and those become the
"Sources" under the answer. Demo: `/dev`, A1C example.

**4. What happens when retrieval finds nothing useful?**
Passages graded "not relevant" are removed. If the best remaining passage is only loosely related, the evidence status is
"insufficient": GPT-4o is told not to present specifics as sourced, and the person sees "this is general guidance". Demo: the
metformin or melatonin question.

**5. Can Medi miss an emergency?**
Yes. The rules alone catch about 79% of the emergencies in our test messages; GPT-4o catches more, and in testing all 18
emergency scenarios were recognized. But the tests are synthetic and small, so this doesn't prove it will never miss one.
That's why every page says "in an emergency, call 911".

**6. Does it over-react?**
Sometimes. The rules raise an unnecessary alert on about 2% of non-emergency test messages, and in some runs one of 50
scenarios was sent to the ER when urgent care was enough. We chose to err toward caution.

**7. How do you know answers aren't hallucinated?**
We extract each medical claim and check it against reference passages. An AI judge flagged 28 claims; reviewing them by
hand showed 23 were the judge's mistakes, leaving 0-3 questionable claims per 50 conversations. We don't claim zero errors,
and the judge is itself an AI, so a human review sample is exported for checking.

**8. Your old report said 0 hallucinations with RAG vs 5 without. Why did that change?**
The old comparison used different question sets, so it wasn't a fair test. The new experiments give every configuration
the same questions and the same grading, and we reviewed the judge's flags by hand.

**9. Did the new retrieval actually make answers better?**
It found better references (Hit@5 0.911 to 0.967, MRR 0.758 to 0.853). On our 50 textbook symptom cases, end-to-end
grounding was about the same as the original, because those cases were already easy for both. The gains we can show
end-to-end are sources on every answer, honest limitation notes, faster emergency alerts, and 100% acceptable triage in that run.

**10. What data do you collect? Where does it go?**
Nothing is stored on Medi's server. The conversation stays in the browser for the visit; the optional profile is saved on the
person's own device. To answer, the conversation goes to OpenAI; a typed map location goes to Google Maps. Server logs contain
timings and counts only, never what anyone wrote. Evidence: `docs/SECURITY_PRIVACY.md`.

**11. Why should anyone trust health advice from an AI?**
They shouldn't rely on it alone, and Medi says so. It's designed to help people understand information and pick a sensible
next step, not to diagnose. It never gives probabilities or invents doses, and it recommends professional care whenever
the situation warrants it.

**12. Does it work in all 12 languages?**
In our test (8 questions per language, machine-translated), all 96 replies were in the right language and every emergency
and crisis question triggered the safety alert. It hasn't been checked by native speakers, and the medical library is in
English, so we describe it as tested but not validated.

**13. Why does it take 5 seconds?**
Extra steps check the answer: an analyzer (about 1 s) and a reranker (about 1.4 s) before GPT-4o writes. We measured a faster
reranker setting and rejected it because it lowered precision. Emergency alerts skip these steps and appear in about 0.04 s.

**14. What would you do next?**
Test with real users and native speakers, have a clinician review the test cases and answers, enlarge the test sets, and
review the exported answer sample by hand.

**15. What was the hardest problem?**
Measuring honestly. For example, our first emergency rules missed "I've been thinking about killing myself" because they only
matched "kill myself", and the safety test suite caught it. Another: we wrote a held-out test set before changing the rules,
so we wouldn't fool ourselves.
