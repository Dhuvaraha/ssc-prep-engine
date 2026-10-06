from collections import Counter

from app.content.generators.one_word_substitution import build_one_word_substitution_bank


def test_one_word_substitution_bank_has_professional_shape():
    bank = build_one_word_substitution_bank()

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
        assert item.question_text.startswith("Select the one-word substitute for:")

    assert sum("study" in item.question_text.lower() for item in bank) >= 8
    assert sum("killing" in item.question_text.lower() for item in bank) >= 5
    assert sum("fear" in item.question_text.lower() for item in bank) >= 5
