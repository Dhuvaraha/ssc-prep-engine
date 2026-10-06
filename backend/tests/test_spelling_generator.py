from collections import Counter
from app.content.generators.spelling import build_spelling_bank

def test_spelling_bank_shape():
    bank=build_spelling_bank()
    assert len(bank)==100
    assert len(Counter(q.pattern_type for q in bank))==2
    for q in bank:
        assert len(q.options)==4
        assert len(set(q.options))==4
        assert 1 <= q.correct_option <= 4
        assert q.explanation and q.fast_method
