from sqlalchemy import select

from app.db import Base, SessionLocal, engine
from app.models import Flashcard, Topic


CARDS = [
    ("percentage", "What is 25% as a fraction?", "1/4", "50% = 1/2, 20% = 1/5, 12.5% = 1/8", "formula"),
    ("average", "Core average formula?", "Average = Sum / Count", "So Sum = Average × Count", "formula"),
    ("time-and-work", "Fast starting point for time & work?", "Convert days into work rates or use an LCM total-work unit.", "Higher efficiency means fewer days.", "formula"),
    ("coding-decoding", "Alphabet position shortcut?", "A=1, B=2, ... Z=26", "Also test reverse positions when a normal shift does not fit.", "reasoning"),
    ("dictionary-order", "How do you compare words quickly?", "Ignore the common prefix and compare from the first differing letter.", None, "reasoning"),
    ("syllogism", "Main syllogism rule?", "Accept only conclusions that are definitely true from the statements.", "Do not add real-world assumptions.", "reasoning"),
    ("error-spotting", "Subject-verb shortcut?", "Find the true head subject, not a nearby noun inside a phrase.", "Example: 'The list of items is...'", "english"),
    ("synonyms-and-antonyms", "Vocabulary recall method?", "Replace the word with a simple meaning, then choose the closest/opposite option.", None, "english"),
    ("physics", "SI unit of electric current?", "Ampere (A)", "Voltage = volt, resistance = ohm, power = watt.", "gk"),
    ("important-days", "How should important-day facts be revised?", "Use active recall with spaced repetition rather than rereading.", "Keep current-affairs-sensitive facts separate from static GK.", "gk"),
]


def seed_flashcards() -> None:
    Base.metadata.create_all(engine)

    with SessionLocal() as db:
        for topic_slug, front, back, related_fact, card_type in CARDS:
            topic = db.scalar(select(Topic).where(Topic.slug == topic_slug))
            if not topic:
                continue

            existing = db.scalar(
                select(Flashcard).where(
                    Flashcard.topic_id == topic.id,
                    Flashcard.front == front,
                )
            )
            if existing:
                continue

            db.add(
                Flashcard(
                    topic_id=topic.id,
                    front=front,
                    back=back,
                    related_fact=related_fact,
                    card_type=card_type,
                )
            )

        db.commit()


if __name__ == "__main__":
    seed_flashcards()
