"""Fail-closed, subject-sensitive editorial completeness checks."""
import unittest
from app.services.four_option_readiness import evaluate_four_option_readiness


def fixture(subject="general-awareness"):
    question = dict(subject=subject, options=[{"position": n} for n in (1, 2, 3, 4)],
                    correct_option=4, question_revision="q-v1", answer_version="key-v1",
                    correct_explanation="Article 32 provides the Right to Constitutional Remedies.",
                    correct_solution_reviewed=True, correct_review_reference="independent-review-01")
    notes = [dict(position=n, status="published", knowledge_text=f"Independently reviewed distinction for option {n}",
                  basis_reference="verified-reference-01", review_reference=f"review-{n}",
                  reviewed_at="2026-10-14", question_revision="q-v1", answer_version="key-v1")
             for n in (1, 2, 3)]
    return question, notes


class FourOptionReadinessTests(unittest.TestCase):
    def test_complete_four_option_evidence_still_requires_factual_signoff(self):
        q, notes = fixture()
        report = evaluate_four_option_readiness(q, notes)
        self.assertEqual(report["status"], "structurally_ready_for_editorial_signoff")
        self.assertFalse(report["factual_accuracy_certified"])
        self.assertFalse(report["learner_published"])
        self.assertEqual(len(report["option_status"]), 4)

    def test_missing_gk_distractor_is_not_teaching_ready(self):
        q, notes = fixture()
        report = evaluate_four_option_readiness(q, notes[:2])
        self.assertEqual(report["status"], "requires_review")
        self.assertIn("option_3:missing_review", report["problems"])

    def test_changed_answer_key_or_question_invalidates_old_notes(self):
        q, notes = fixture()
        q["answer_version"] = "key-v2"
        report = evaluate_four_option_readiness(q, notes)
        self.assertIn("option_1:stale_or_unbound_review", report["problems"])

    def test_arbitrary_numeric_distractor_can_explicitly_be_non_diagnostic(self):
        q, notes = fixture("quant")
        notes[0] = dict(notes[0], status="reviewed_not_diagnostic", knowledge_text="", reason="No defensible specific misconception can be inferred from this value")
        report = evaluate_four_option_readiness(q, notes)
        self.assertEqual(report["status"], "structurally_ready_for_editorial_signoff")
        q["subject"] = "general-awareness"
        report = evaluate_four_option_readiness(q, notes)
        self.assertIn("option_1:unapproved_or_unsupported_status", report["problems"])

    def test_invalid_or_duplicate_review_does_not_count_as_coverage(self):
        q, notes = fixture()
        notes.append(dict(notes[0]))
        report = evaluate_four_option_readiness(q, notes)
        self.assertIn("invalid_duplicate_or_out_of_scope_option_review", report["problems"])

    def test_unreviewed_notes_cannot_pass(self):
        q, notes = fixture("english")
        notes[1]["review_reference"] = ""
        self.assertEqual(evaluate_four_option_readiness(q, notes)["status"], "requires_review")

    def test_correct_answer_must_be_in_four_distinct_options(self):
        q, notes = fixture()
        q["options"] = [{"position": 1}] * 4
        result = evaluate_four_option_readiness(q, notes)
        self.assertIn("exactly_four_distinct_option_positions_required", result["problems"])
        self.assertIn("answer_key_not_in_options", result["problems"])

    def test_versionless_legacy_notes_fail_closed(self):
        q, notes = fixture()
        del notes[0]["question_revision"]
        self.assertIn("option_1:stale_or_unbound_review", evaluate_four_option_readiness(q, notes)["problems"])


if __name__ == "__main__":
    unittest.main()
