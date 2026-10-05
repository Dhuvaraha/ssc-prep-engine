import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from app.content.import_schema import ImportedQuestion
from app.db import SessionLocal
from app.services.question_import import import_question


ALLOWED_KEYS = set(ImportedQuestion.model_fields)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a private review package")
    parser.add_argument("review_json", type=Path)
    args = parser.parse_args()

    raw = json.loads(args.review_json.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise SystemExit("Review package must be a JSON array")

    inserted = 0
    duplicates = 0
    incomplete = 0
    invalid = 0

    with SessionLocal() as db:
        for item in raw:
            if item.get("correct_option") is None:
                incomplete += 1
                continue

            payload = {key: value for key, value in item.items() if key in ALLOWED_KEYS}
            try:
                question = ImportedQuestion.model_validate(payload)
                _, was_inserted = import_question(db, question)
                inserted += int(was_inserted)
                duplicates += int(not was_inserted)
            except (ValidationError, ValueError):
                invalid += 1

        db.commit()

    print(
        f"Imported {inserted}; duplicates {duplicates}; "
        f"incomplete-answer {incomplete}; invalid {invalid}"
    )


if __name__ == "__main__":
    main()
