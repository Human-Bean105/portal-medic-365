"""Keyword search with Okapi BM25, in plain Python. It finds passages that contain the exact terms someone used
(drug names, test names like "A1C", rare conditions), which embedding search can rank too low."""
import math
import re
from collections import Counter, defaultdict

TOKEN = re.compile(r"[a-z0-9]+")
STOPWORDS = set("""a about above after again against all am an and any are as at be because been before being below
between both but by can could did do does doing down during each few for from further had has have having he her here
hers herself him himself his how i if in into is it its itself just me more most my myself no nor not now of off on once
only or other our ours ourselves out over own same she should so some such than that the their theirs them themselves
then there these they this those through to too under until up very was we were what when where which while who whom why
will with you your yours yourself yourselves im ive dont cant get got feel feeling like really also may might""".split())
SUFFIXES = ("ations", "ation", "ings", "ing", "edly", "ies", "ied", "ed", "s")


def stem(word):
    """A deliberately light stemmer: "headaches" and "headache" match, "bleeding" and "bleed" match. Plural "-es"
    isn't stripped, because that would split "diseases" from "disease"."""
    for suffix in SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3 and not word.endswith(("ss", "eed")):
            return word[:-len(suffix)] + ("y" if suffix in ("ies", "ied") else "")
    return word


def tokens(text):
    return [stem(w) for w in TOKEN.findall(text.lower()) if w not in STOPWORDS]


class BM25:
    def __init__(self, documents, k1=1.2, b=0.75):
        self.k1, self.b = k1, b
        self.lengths = []
        self.postings = defaultdict(list)
        for i, doc in enumerate(documents):
            counts = Counter(tokens(doc))
            self.lengths.append(sum(counts.values()))
            for term, tf in counts.items():
                self.postings[term].append((i, tf))
        n = len(documents)
        self.avg = sum(self.lengths) / max(n, 1)
        self.idf = {t: math.log(1 + (n - len(p) + 0.5) / (len(p) + 0.5)) for t, p in self.postings.items()}

    def search(self, query, n=50):
        """[(score, doc_index)] for the n best-matching documents."""
        scores = defaultdict(float)
        for term in set(tokens(query)):
            idf = self.idf.get(term)
            if idf is None:
                continue
            for i, tf in self.postings[term]:
                norm = tf + self.k1 * (1 - self.b + self.b * self.lengths[i] / self.avg)
                scores[i] += idf * tf * (self.k1 + 1) / norm
        return sorted(((s, i) for i, s in scores.items()), reverse=True)[:n]


def passage_text(chunk):
    """What BM25 indexes for a passage: the title (weighted three times), alternate names, and the text."""
    return " ".join([chunk["t"]] * 3 + chunk.get("also_called", []) + [chunk["x"]])
