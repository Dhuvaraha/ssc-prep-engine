"""Explainable editorial and learner queues; no writes or exam-equivalence claims.

An edge must carry its teaching rationale. Structural validation is distinct
from editorial validation and from evidence that a learner understands a skill.
No question counts or unverified source labels are used as PYQ frequencies.
"""
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class Dependency:
    prerequisite: str
    topic: str
    rationale: str


class CurriculumGraph:
    def __init__(self, topics, dependencies=(), *, reviewed_topics=()):
        supplied = list(topics)
        self.topics = set(supplied)
        if len(self.topics) != len(supplied):
            raise ValueError("Duplicate topic identity")
        self.reviewed = set(reviewed_topics)
        if not self.reviewed <= self.topics:
            raise ValueError("Unknown reviewed topic")
        self.parents = {topic: set() for topic in self.topics}
        self.rationales = {}
        for edge in dependencies:
            if edge.topic not in self.topics or edge.prerequisite not in self.topics:
                raise ValueError("Unknown prerequisite endpoint")
            if not edge.rationale.strip():
                raise ValueError("Prerequisite requires a teaching rationale")
            if edge.prerequisite in self.parents[edge.topic]:
                raise ValueError("Duplicate dependency")
            self.parents[edge.topic].add(edge.prerequisite)
            self.rationales[(edge.prerequisite, edge.topic)] = edge.rationale
        self.ancestors = {}
        visiting = set()

        def visit(topic):
            if topic in visiting:
                raise ValueError("Cyclic prerequisite graph")
            if topic in self.ancestors:
                return self.ancestors[topic]
            visiting.add(topic)
            ancestors = set(self.parents[topic])
            for parent in self.parents[topic]:
                ancestors.update(visit(parent))
            visiting.remove(topic)
            self.ancestors[topic] = ancestors
            return ancestors

        for topic in sorted(self.topics):
            visit(topic)


@dataclass(frozen=True)
class QualityEvidence:
    confirmed_defects: tuple[str, ...] = ()  # review references, not guessed errors
    review_flags: tuple[str, ...] = ()
    missing_stages: tuple[str, ...] = ()
    # Share of reviewed papers containing this topic, not share of database rows.
    paper_frequency: float | None = None
    benchmark_reference: str | None = None

    def __post_init__(self):
        if self.paper_frequency is not None:
            if not isfinite(self.paper_frequency) or not 0 <= self.paper_frequency <= 1:
                raise ValueError("Invalid paper frequency")
            if not self.benchmark_reference or not self.benchmark_reference.strip():
                raise ValueError("Frequency requires reviewed paper evidence")


@dataclass(frozen=True)
class LearnerEvidence:
    # Set only from independent unseen checks, never lesson opens or repeats.
    independent_mastery: bool = False
    retention_due: bool = False
    error_rate: float = 0.0
    speed_needs_work: bool = False

    def __post_init__(self):
        if any(type(value) is not bool for value in
               (self.independent_mastery, self.retention_due, self.speed_needs_work)):
            raise ValueError("Learner state flags must be booleans")
        if not isfinite(self.error_rate) or not 0 <= self.error_rate <= 1:
            raise ValueError("Invalid independent error rate")


def prioritize(graph, quality, learner=None, *, required_topics=None):
    if set(quality) - graph.topics or set(learner or {}) - graph.topics:
        raise ValueError("Evidence references unknown topic")
    required = graph.topics if required_topics is None else set(required_topics)
    if not required <= graph.topics:
        raise ValueError("Unknown exam requirement")
    scope = required | {p for topic in required for p in graph.ancestors[topic]}
    evidence = {topic: quality.get(topic, QualityEvidence()) for topic in scope}
    global_queue, study_queue = [], []
    for topic in sorted(scope):
        item = evidence[topic]
        dependents = sum(topic in graph.ancestors[child] for child in scope)
        tier = (0 if item.confirmed_defects else 1 if item.missing_stages else
                2 if item.review_flags else 3)
        row = {"topic": topic, "tier": tier, "unlocks_topics": dependents,
               "confirmed_defects": list(item.confirmed_defects),
               "review_flags": list(item.review_flags), "missing_stages": list(item.missing_stages),
               "paper_frequency": item.paper_frequency,
               "benchmark_reference": item.benchmark_reference,
               "prerequisites_reviewed": topic in graph.reviewed,
               "uncertainties": (["PYQ frequency unmeasured"] if item.paper_frequency is None else [])
                   + (["Prerequisite mapping incomplete"] if topic not in graph.reviewed else [])}
        global_queue.append(row)
        if learner is None:
            continue
        state = learner.get(topic, LearnerEvidence())
        blocked_by = sorted(p for p in graph.ancestors[topic]
                            if not learner.get(p, LearnerEvidence()).independent_mastery
                            or evidence[p].confirmed_defects)
        mapping_incomplete = any(p not in graph.reviewed for p in graph.ancestors[topic] | {topic})
        action = ("content_repair" if item.confirmed_defects else
                  "mapping_review" if mapping_incomplete else
                  "prerequisite_remediation" if blocked_by else
                  "spaced_revision" if state.retention_due else
                  "foundation" if not state.independent_mastery else
                  "timed_practice" if state.speed_needs_work else "maintenance")
        study_queue.append({"topic": topic, "action": action, "blocked_by": blocked_by,
                            "ready": not (item.confirmed_defects or blocked_by or mapping_incomplete),
                            "error_rate": state.error_rate, "retention_due": state.retention_due})
    # Correctness wins over coverage, prerequisite reach, then evidenced exam relevance.
    # Missing frequency is explicit uncertainty and never presented as observed zero.
    global_queue.sort(key=lambda r: (r["tier"], -r["unlocks_topics"],
                                    -(r["paper_frequency"] or 0), r["topic"]))
    study_queue.sort(key=lambda r: (not r["ready"], not r["retention_due"],
                                   -r["error_rate"], r["topic"]))
    return {"global_quality_queue": global_queue, "learner_study_queue": study_queue,
            "scope_topics": len(scope), "changes_daily_pace": False,
            "exam_equivalence_established": False}
