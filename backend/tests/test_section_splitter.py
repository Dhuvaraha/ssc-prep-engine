from app.content.section_splitter import detect_shift, detect_subject


def test_detects_reasoning_heading():
    assert detect_subject("General Intelligence and Reasoning\n1. Question") == "reasoning"


def test_detects_quant_heading():
    assert detect_subject("Quantitative Aptitude\n51. Question") == "quant"


def test_keeps_current_subject_without_heading():
    assert detect_subject("continuation of questions", "english") == "english"


def test_detects_shift_label():
    detected = detect_shift("SSC CGL Tier I 24th July 2023 Shift-2")
    assert detected is not None
    assert "Shift-2".lower() in detected.lower()
