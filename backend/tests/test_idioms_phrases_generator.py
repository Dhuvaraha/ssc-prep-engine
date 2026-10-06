from collections import Counter

from app.content.generators.idioms_phrases import build_idioms_phrases_bank


def test_idioms_phrases_bank_has_professional_shape():
    bank = build_idioms_phrases_bank()

    assert len(bank) == 100
    counts = Counter(item.pattern_type for item in bank)
    assert len(counts) == 10
    assert set(counts.values()) == {10}

    for item in bank:
        assert len(item.options) == 4
        assert len(set(item.options)) == 4
        assert 1 <= item.correct_option <= 4
        assert item.explanation
        assert item.fast_method
        assert item.expected_time_seconds > 0
        assert item.difficulty in {1, 2, 3}

    assert sum("meaning of the idiom" in item.question_text.lower() for item in bank) >= 80
    assert sum("context" in item.question_text.lower() for item in bank) >= 10
