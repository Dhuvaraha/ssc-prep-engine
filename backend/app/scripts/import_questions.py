import json
import sys
from pathlib import Path

from app.content.import_schema import ImportedQuestion
from app.db import SessionLocal
from app.services.question_import import import_question


def load_questions(path: Path) -> list[ImportedQuestion]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Import file must contain a JSON array")
    return [ImportedQuestion.model_validate(item) for item in raw]


def import_questions(path: Path) -> None:
    rows = load_questions(path)

    with SessionLocal() as db:
        inserted = 0
        skipped = 0
        for item in rows:
            _, was_inserted = import_question(db, item)
            inserted += int(was_inserted)
            skipped += int(not was_inserted)

        db.commit()
        print(f"Imported {inserted}; skipped {skipped} duplicates")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m app.scripts.import_questions questions.json")
    import_questions(Path(sys.argv[1]))
