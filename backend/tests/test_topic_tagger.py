from app.content.topic_tagger import suggest_topic


def test_reasoning_dictionary_order():
    slug, confidence = suggest_topic(
        "reasoning",
        "Select the correct order of the given words as they would appear in an English dictionary.",
    )
    assert slug == "dictionary-order"
    assert confidence > 0


def test_english_error_spotting():
    slug, confidence = suggest_topic(
        "english",
        "Identify the segment that contains a grammatical error.",
    )
    assert slug == "error-spotting"
    assert confidence > 0


def test_quant_time_and_work():
    slug, confidence = suggest_topic(
        "quant",
        "A and B can complete a work in 12 days. How many days will they take together?",
    )
    assert slug == "time-and-work"
    assert confidence > 0
