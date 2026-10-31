import unittest

from medi.rag.citations import cited_sources

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
