"""Evidence sufficiency: how well the retrieved passages cover the question, and what Medi should do about it.

The status comes from the reranker's grades (3 = directly answers, 2 = partly useful, 1 = loosely related, 0 = not
relevant). The cut-offs were checked against the retrieval benchmark (evaluation/reports/evidence_calibration.md)."""

STATUSES = ("sufficient", "partial", "insufficient", "none")
LIMITATION = {
    "partial": "Medi's reference library only partly covers this question.",
    "insufficient": "Medi's reference library doesn't cover this question well, so this is general guidance.",
    "none": "Medi couldn't find this in its reference library, so this is general guidance.",
}


def status_from_grades(grades):
    graded = [g for g in grades if g is not None]
    if not graded or max(graded) == 0:
        return "none"
    best = max(graded)
    return "sufficient" if best == 3 else "partial" if best == 2 else "insufficient"


def usable(passages):
    """Passages graded 0 (not relevant) are not shown to the model at all."""
    return [p for p in passages if p.get("grade", 1) > 0]


def prompt_note(status):
    """Tells the generator how much to rely on the reference material."""
    if status == "sufficient":
        return ""
    if status == "partial":
        return ("EVIDENCE CHECK: the reference material only partly covers this. Use it where it applies; for anything it "
                "doesn't cover, keep to general, well-established guidance and don't present specifics as sourced.")
    return ("EVIDENCE CHECK: Medi's reference library has little or nothing relevant to this message. Don't state specific "
            "facts (numbers, doses, thresholds, detailed guideline content) as if they were sourced. Keep to general, "
            "well-established guidance, say plainly that you can't point to a reference for the details, and where useful "
            "ask a clarifying question or suggest a pharmacist or clinician for specifics. Cite nothing.")
