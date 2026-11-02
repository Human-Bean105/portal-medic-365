import unittest

from medi import config
from medi.rag import index, retrieval
from medi.rag.bm25 import BM25, tokens
from medi.rag.chunking import build_chunks, chunk_document
from medi.rag.citations import cited_sources

DOC = {"doc_id": "mlp-1", "type": "health_topic", "source": "MedlinePlus", "title": "Sprains", "url": "u", "groups": [],
       "also_called": [], "text": "## What is it?\nA sprain is a stretched ligament. It often happens in the ankle. Ice helps.\n"
                                  "## Treatment\nRest the joint. Use a compression bandage. Raise the leg.\n- Take breaks"}


class ChunkingTest(unittest.TestCase):
    def test_chunks_keep_whole_sentences_and_headings(self):
        chunks = chunk_document(DOC, max_chars=60, overlap=0)
        self.assertTrue(all(c["text"].startswith("Sprains (") for c in chunks))
        self.assertTrue(all(c["text"].rstrip().endswith((".", "breaks")) for c in chunks))
        self.assertEqual({c["heading"] for c in chunks}, {"What is it?", "Treatment"})

    def test_overlap_repeats_the_last_sentence_within_a_section(self):
        chunks = chunk_document(DOC, max_chars=60, overlap=1)
        first, second = chunks[0]["text"], chunks[1]["text"]
        self.assertIn(first.split(". ")[-1].rstrip("."), second)

    def test_sections_never_mix(self):
        for c in chunk_document(DOC, max_chars=10000, overlap=1):
            self.assertFalse("ligament" in c["text"] and "compression" in c["text"])

    def test_duplicates_are_removed_and_ids_are_stable(self):
        chunks, dropped = build_chunks([DOC, {**DOC, "doc_id": "mlp-2"}], max_chars=60, overlap=0)
        self.assertEqual(dropped, len(chunks))
        self.assertEqual(chunks[0]["id"], "mlp-1#0")


class KeywordSearchTest(unittest.TestCase):
    def test_stemming_and_stopwords(self):
        self.assertEqual(tokens("The headaches"), ["headache"])
        self.assertEqual(tokens("diseases bleeding allergies"), tokens("disease bleed allergy"))
        self.assertEqual(tokens("illness"), ["illness"])

    def test_bm25_prefers_documents_with_rare_query_terms(self):
        bm = BM25(["metformin side effects diarrhea", "diabetes overview", "metformin"])
        self.assertEqual(bm.search("metformin diarrhea", 3)[0][1], 0)


class HybridRetrievalTest(unittest.TestCase):
    def test_hybrid_finds_exact_terms_vector_search_ranks_lower(self):
        idx = index.get()
        lice = next(i for i, c in enumerate(idx.chunks) if c["t"] == "Head Lice")
        qvec = list(idx.vectors[lice * idx.dims:(lice + 1) * idx.dims])  # a query vector about something else
        cfg = config.DEFAULT.but(top_k=5)
        vector_titles = [p["t"] for p in retrieval.search_with(cfg.but(retriever="vector", min_score=0.0), "A1C", qvec)]
        hybrid_titles = [p["t"] for p in retrieval.search_with(cfg.but(alpha=0.5), "A1C", qvec)]
        self.assertNotIn("A1C", vector_titles)
        self.assertIn("A1C", hybrid_titles)

    def test_at_most_two_passages_per_topic(self):
        ranked = [{"t": "X"}] * 4 + [{"t": "Y"}]
        self.assertEqual([p["t"] for p in retrieval.select(ranked, config.DEFAULT.but(top_k=5))], ["X", "X", "Y"])

PASSAGES = [
    {"t": "Headache", "s": "MedlinePlus", "u": "https://medlineplus.gov/headache.html", "x": "..."},
    {"t": "Headache", "s": "MedlinePlus", "u": "https://medlineplus.gov/headache.html", "x": "..."},
    {"t": "Migraine", "s": "MedlinePlus", "u": "https://medlineplus.gov/migraine.html", "x": "..."},
]


class CitationTest(unittest.TestCase):
    def test_citations_map_only_to_retrieved_passages(self):
        sources = cited_sources({"citations": [3, 0, 7, -1]}, PASSAGES)
        self.assertEqual([s["title"] for s in sources], ["Migraine"])

    def test_duplicate_sources_are_merged(self):
        self.assertEqual(len(cited_sources({"citations": [1, 2]}, PASSAGES)), 1)

    def test_no_passages_means_no_sources(self):
        self.assertEqual(cited_sources({"citations": [1, 2]}, []), [])


if __name__ == "__main__":
    unittest.main()
