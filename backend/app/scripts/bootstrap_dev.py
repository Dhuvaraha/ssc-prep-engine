from pathlib import Path

from app.scripts.import_questions import import_questions
from app.scripts.seed_cgl import seed
from app.scripts.seed_lessons import seed_lessons


def bootstrap() -> None:
    seed()
    seed_lessons()
    import_questions(Path("data/demo_questions.json"))


if __name__ == "__main__":
    bootstrap()
