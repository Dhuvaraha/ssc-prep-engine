import pytest

from app.content.cgl_topics import CGL_TOPICS
from app.scripts.prioritize_curriculum import build_report
from app.services.curriculum_priority import (
    CurriculumGraph, Dependency, LearnerEvidence, QualityEvidence, prioritize,
)


def graph():
    return CurriculumGraph(["ratio", "percentage", "profit"], [
        Dependency("ratio", "percentage", "Percent is a ratio with denominator 100."),
        Dependency("percentage", "profit", "Profit percent compares gain to cost price."),
    ], reviewed_topics=["ratio", "percentage", "profit"])


def test_defect_beats_frequency_and_prerequisites_gate_learner():
    report = prioritize(graph(), {
        "profit": QualityEvidence(confirmed_defects=("review:wrong-base",),
                                  paper_frequency=.9, benchmark_reference="synthetic-paper-review"),
    }, {"profit": LearnerEvidence(error_rate=1)})
    assert report["global_quality_queue"][0]["topic"] == "profit"
    assert report["learner_study_queue"][0]["topic"] == "ratio"
    profit = next(r for r in report["learner_study_queue"] if r["topic"] == "profit")
    assert profit["action"] == "content_repair"
    assert profit["blocked_by"] == ["percentage", "ratio"]
    assert not report["changes_daily_pace"]


def test_transitive_remediation_and_retention_without_compressing_foundations():
    report = prioritize(graph(), {}, {
        "ratio": LearnerEvidence(independent_mastery=True, retention_due=True),
    }, required_topics=["profit"])
    assert report["scope_topics"] == 3
    rows = {r["topic"]: r for r in report["learner_study_queue"]}
    assert rows["ratio"]["action"] == "spaced_revision"
    assert rows["percentage"]["ready"]
    assert rows["profit"]["blocked_by"] == ["percentage"]


def test_all_74_topics_accounted_for_without_inventing_frequency_or_dependencies():
    topics = [f"{subject}/{topic}" for subject, names in CGL_TOPICS.items() for topic in names]
    report = prioritize(CurriculumGraph(topics), {}, {})
    assert report["scope_topics"] == 74
    assert all(r["paper_frequency"] is None for r in report["global_quality_queue"])
    assert all(r["action"] == "mapping_review" for r in report["learner_study_queue"])


@pytest.mark.parametrize("dependencies", [
    [Dependency("a", "b", "r"), Dependency("b", "a", "r")],
    [Dependency("a", "a", "r")], [Dependency("missing", "b", "r")],
    [Dependency("a", "b", "")],
])
def test_invalid_graph_rejected(dependencies):
    with pytest.raises(ValueError):
        CurriculumGraph(["a", "b"], dependencies)


def test_frequency_requires_evidence_and_invalid_learner_rates_rejected():
    with pytest.raises(ValueError):
        QualityEvidence(paper_frequency=.9)
    with pytest.raises(ValueError):
        LearnerEvidence(error_rate=float("nan"))
    with pytest.raises(ValueError):
        LearnerEvidence(independent_mastery="false")
    with pytest.raises(ValueError):
        QualityEvidence(paper_frequency=.9, benchmark_reference="  ")


def test_aggregate_report_does_not_turn_screening_flags_into_confirmed_defects():
    result = build_report({"exam_slug": "ssc-cgl-tier-1", "topic_reports": [
        {"subject": "reasoning", "topic": "Syllogism", "lesson_published": True,
         "brief_solution_review": 100, "template_repeat_candidates": 90},
    ]})
    row = result["global_quality_queue"][0]
    assert row["confirmed_defects"] == []
    assert len(row["review_flags"]) == 2
    assert row["paper_frequency"] is None
    assert not result["learner_evidence_supplied"]
