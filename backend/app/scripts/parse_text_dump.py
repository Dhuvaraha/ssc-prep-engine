import json
import sys
from pathlib import Path

from app.content.text_parser import parse_text_candidates


def main(input_path: Path, output_path: Path) -> None:
    text = input_path.read_text(encoding="utf-8", errors="replace")
    candidates = parse_text_candidates(text)

    payload = [
        {
            "number": c.number,
            "question_text": c.question_text,
            "options": [{"position": p, "text": t} for p, t in c.options],
            "correct_option": c.correct_option,
            "verification_status": "review_required",
            "raw_text": c.raw_text,
        }
        for c in candidates
    ]
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(payload)} review candidates to {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python -m app.scripts.parse_text_dump input.txt output.json")
    main(Path(sys.argv[1]), Path(sys.argv[2]))
