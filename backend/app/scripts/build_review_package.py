import argparse
import json
from pathlib import Path

from app.content.candidate_builder import build_review_candidate
from app.content.text_parser import parse_text_candidates


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a private SSC question review package")
    parser.add_argument("input_text", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--year", type=int)
    parser.add_argument("--shift")
    parser.add_argument("--source", required=True)
    parser.add_argument("--exam", default="ssc-cgl-tier-1")
    args = parser.parse_args()

    text = args.input_text.read_text(encoding="utf-8", errors="replace")
    parsed = parse_text_candidates(text)
    package = [
        build_review_candidate(
            item,
            exam_slug=args.exam,
            subject_slug=args.subject,
            year=args.year,
            shift=args.shift,
            source_reference=args.source,
        )
        for item in parsed
    ]

    args.output_json.write_text(
        json.dumps(package, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    visual_count = sum(1 for item in package if item["requires_visual_review"])
    print(
        f"Built {len(package)} review candidates; "
        f"{visual_count} flagged for visual review."
    )


if __name__ == "__main__":
    main()
