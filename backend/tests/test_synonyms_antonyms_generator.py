from collections import Counter

from app.content.generators.synonyms_antonyms import build_synonyms_antonyms_bank


def test_synonyms_antonyms_bank_has_professional_shape():
    bank = build_synonyms_antonyms_bank()

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

    assert sum("synonym" in item.question_text.lower() for item in bank) >= 20
    assert sum("antonym" in item.question_text.lower() for item in bank) >= 20
