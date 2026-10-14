"""Structure-only regression for the original, non-published polity teaching pilot."""
import json
import unittest
from pathlib import Path


PILOT_PATH = Path(__file__).resolve().parents[1] / "data" / "original_four_option_polity_pilot.json"


class OriginalFourOptionPolityPilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.item = json.loads(PILOT_PATH.read_text(encoding="utf-8"))

    def test_stays_unpublished_and_not_mislabeled_as_pyq(self):
        self.assertEqual(self.item["status"], "editorial_draft_not_published")
        self.assertIn("Not an authenticated SSC PYQ", self.item["authorship"])
        self.assertFalse(self.item["ai_required"])

    def test_four_explanations_have_sources_and_distinctions(self):
        options = self.item["options"]
        self.assertEqual([o["position"] for o in options], [1, 2, 3, 4])
        self.assertEqual(sum(o["role"] == "correct" for o in options), 1)
        self.assertEqual(self.item["correct_position"], 4)
        for option in options:
            self.assertTrue(option["actual_meaning"].strip())
            self.assertTrue(option["source"].startswith("https://"))
            self.assertTrue((option.get("why_this_question") or option.get("why_not_this_question") or "").strip())

    def test_related_226_and_retrieval_not_missing(self):
        self.assertEqual(self.item["related_concept"]["name"], "Article 226")
        self.assertIn("High Courts", self.item["related_concept"]["explanation"])
        self.assertTrue(self.item["independent_check"]["question"])
        self.assertTrue(self.item["independent_check"]["reason"])
        self.assertEqual(self.item["independent_check"]["correct_position"], 4)
        self.assertIn("Independent legal", self.item["editorial_gates"][0])


if __name__ == "__main__":
    unittest.main()
