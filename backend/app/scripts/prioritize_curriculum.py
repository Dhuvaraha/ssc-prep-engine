"""Rank aggregate audit evidence offline; never connects to or edits a database.

Input: collect_learning_quality() JSON; optional reviewed dependency manifest.
No learner data is inferred from content counts. Output contains no question text.
"""
import argparse
import json
from pathlib import Path

from app.services.curriculum_priority import CurriculumGraph, Dependency, QualityEvidence, prioritize


def build_report(audit, manifest=None):
    manifest = manifest or {}
    rows = audit["topic_reports"]
    topics = [f'{r["subject"]}/{r["topic"]}' for r in rows]
    graph = CurriculumGraph(topics,
        [Dependency(**edge) for edge in manifest.get("dependencies", [])],
        reviewed_topics=manifest.get("reviewed_topics", []))
    quality = {}
    for topic, row in zip(topics, rows):
        flags = []
        for key in ("brief_solution_review", "invalid_options_review", "source_reference_review",
                    "template_repeat_candidates"):
            if row.get(key, 0):
                flags.append(f'{key}: {row[key]}')
        quality[topic] = QualityEvidence(
            confirmed_defects=tuple(manifest.get("confirmed_defects", {}).get(topic, [])),
            review_flags=tuple(flags),
            missing_stages=() if row.get("lesson_published") else ("lesson",),
        )
    if set(manifest.get("confirmed_defects", {})) - set(topics):
        raise ValueError("Defect references unknown topic")
    result = prioritize(graph, quality)
    result.update({"exam_slug": audit["exam_slug"], "read_only": True,
                   "learner_evidence_supplied": False,
                   "limitations": ["Length and template similarity are screening flags, not proven errors.",
                                    "Published lessons do not prove pedagogical completeness.",
                                    "Dependency validation does not establish editorial approval."]})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8")) if args.manifest else None
    report = build_report(audit, manifest)
    with args.output.open("x", encoding="utf-8") as out:
        json.dump(report, out, indent=2, ensure_ascii=False)
        out.write("\n")


if __name__ == "__main__":
    main()
