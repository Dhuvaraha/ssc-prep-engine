from pathlib import Path

from app.scripts.import_questions import import_questions
from app.scripts.seed_cgl import seed


def bootstrap() -> None:
    seed()
    import_questions(Path("data/demo_questions.json"))


if __name__ == "__main__":
    bootstrap()
