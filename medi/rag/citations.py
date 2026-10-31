"""Shows retrieved passages to the model and maps its citation numbers back to real, retrieved sources."""


def reference_note(passages):
    lines = [f"[{n}] {p['t']} (source: {p['s']})\n{p['x']}" for n, p in enumerate(passages, 1)]
    return "REFERENCE MATERIAL (retrieved for this conversation):\n\n" + "\n\n".join(lines)


def cited_sources(result, passages):
    """Turns the model's citation numbers into a deduplicated list of real sources the app can show.
    Numbers that don't match a retrieved passage are dropped, so a citation can never point to an invented source."""
    sources, seen = [], set()
    for n in result.get("citations", []):
        if isinstance(n, int) and 1 <= n <= len(passages):
            p = passages[n - 1]
            if p["u"] not in seen:
                seen.add(p["u"])
                sources.append({"title": p["t"], "source": p["s"], "url": p["u"]})
    return sources
