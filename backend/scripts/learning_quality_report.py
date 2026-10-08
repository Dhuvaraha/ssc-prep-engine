"""Run from backend/: python -m scripts.learning_quality_report --exam ssc-cgl-tier-1

Read-only. Requires DATABASE_URL pointing to the desired *audited* dataset.
Never edits or publishes questions.
"""
import argparse
import json

from app.db import SessionLocal
from app.services.learning_quality_audit import collect_learning_quality


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exam", default="ssc-cgl-tier-1")
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    with SessionLocal() as db:
        report = collect_learning_quality(db, exam_slug=args.exam)
    if args.summary_only:
        report.pop("topic_reports")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
