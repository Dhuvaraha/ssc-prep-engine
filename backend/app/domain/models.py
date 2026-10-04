from dataclasses import dataclass
from enum import StrEnum


class AttemptOutcome(StrEnum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    SKIPPED = "skipped"


class MistakeType(StrEnum):
    CONCEPT = "concept"
    FORMULA = "formula"
    CALCULATION = "calculation"
    MISREAD = "misread"
    GUESS = "guess"
    TIME_PRESSURE = "time_pressure"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class MasterySignal:
    topic_id: str
    outcome: AttemptOutcome
    time_seconds: float
    expected_time_seconds: float
    confidence: int | None = None
    used_hint: bool = False
