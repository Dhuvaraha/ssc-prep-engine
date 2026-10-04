from app.domain.models import AttemptOutcome, MasterySignal


def mastery_delta(signal: MasterySignal) -> float:
    """Small deterministic update used before we have enough data for a richer model."""
    if signal.outcome == AttemptOutcome.SKIPPED:
        return -1.0

    speed_ratio = (
        signal.expected_time_seconds / max(signal.time_seconds, 1.0)
        if signal.expected_time_seconds > 0
        else 1.0
    )
    speed_bonus = max(-1.0, min(1.0, speed_ratio - 1.0))

    if signal.outcome == AttemptOutcome.CORRECT:
        delta = 4.0 + speed_bonus
        if signal.used_hint:
            delta -= 1.0
        return delta

    return -3.0


def clamp_mastery(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)
