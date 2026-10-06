from collections import Counter

from app.content.generators.error_spotting import build_error_spotting_bank


def test_error_spotting_bank_has_professional_shape():
    bank = build_error_spotting_bank()

    assert len(bank) == 100
    counts = Counter(item.pattern_type for item in bank)
    assert len(counts) == 10
    assert set(counts.values()) == {10}

    no_error_count = 0
    for item in bank:
        assert len(item.options) == 4
        assert len(set(item.options)) == 4
        assert item.options[3] == "No error"
        assert 1 <= item.correct_option <= 4
        assert item.explanation
        assert item.fast_method
        assert item.expected_time_seconds > 0
        assert item.difficulty in {1, 2, 3}
        if item.correct_option == 4:
            no_error_count += 1

    assert no_error_count >= 15
