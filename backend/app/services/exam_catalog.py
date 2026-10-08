"""Read-only 2026 SSC exam-stage catalog.

The catalog is a product blueprint, not a promise that a course is published.
Only CGL Tier I is enabled until content, timings, assessment and data
isolation for the other stages pass release gates.
"""

from copy import deepcopy

SSC_CGL_NOTICE = "https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/Notice_of_adv_cgl_2025.pdf"
SSC_JE_NOTICE = "https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/Notice_of_adv_je_2026.pdf"

EXAM_CATALOG = (
    {
        "slug": "ssc-cgl-tier-1",
        "family": "cgl",
        "stage": "tier-1",
        "stream": None,
        "name": "SSC CGL Tier I",
        "subtitle": "Graduate Level · screening",
        "status": "ready",
        "total_questions": 100,
        "duration_minutes": 60,
        "positive_marks": 2.0,
        "negative_marks": 0.5,
        "sections": [
            {"slug": "reasoning", "name": "General Intelligence & Reasoning", "questions": 25, "minutes": 15, "kind": "mcq", "qualifying": False},
            {"slug": "general-awareness", "name": "General Awareness", "questions": 25, "minutes": 15, "kind": "mcq", "qualifying": False},
            {"slug": "quant", "name": "Quantitative Aptitude", "questions": 25, "minutes": 15, "kind": "mcq", "qualifying": False},
            {"slug": "english", "name": "English Comprehension", "questions": 25, "minutes": 15, "kind": "mcq", "qualifying": False},
        ],
        "extra_assessments": [],
        "notice_url": SSC_CGL_NOTICE,
    },
    {
        "slug": "ssc-cgl-tier-2",
        "family": "cgl",
        "stage": "tier-2",
        "stream": None,
        "name": "SSC CGL Tier II",
        "subtitle": "Common Paper I · Computer Knowledge + DEST",
        "status": "planned",
        "total_questions": 160,
        "duration_minutes": 135,
        "positive_marks": 3.0,
        "negative_marks": 1.0,
        "sections": [
            {"slug": "mathematical-abilities", "name": "Mathematical Abilities", "questions": 30, "minutes": 30, "kind": "mcq", "qualifying": False},
            {"slug": "reasoning", "name": "Reasoning and General Intelligence", "questions": 30, "minutes": 30, "kind": "mcq", "qualifying": False},
            {"slug": "english", "name": "English Language & Comprehension", "questions": 45, "minutes": 40, "kind": "mcq", "qualifying": False},
            {"slug": "general-awareness", "name": "General Awareness", "questions": 25, "minutes": 20, "kind": "mcq", "qualifying": False},
            {"slug": "computer-knowledge", "name": "Computer Knowledge Test", "questions": 20, "minutes": 15, "kind": "mcq", "qualifying": True},
        ],
        "extra_assessments": [
            {"slug": "dest", "name": "Data Entry Speed Test", "kind": "typing", "minutes": 15, "qualifying": True}
        ],
        "notice_url": SSC_CGL_NOTICE,
    },
    {
        "slug": "ssc-je-telecom-paper-1",
        "family": "je",
        "stage": "paper-1",
        "stream": "telecom",
        "name": "SSC JE Telecom Paper I",
        "subtitle": "Reasoning, GA & Telecom technical",
        "status": "planned",
        "total_questions": 200,
        "duration_minutes": 120,
        "positive_marks": 1.0,
        "negative_marks": 0.25,
        "sections": [
            {"slug": "reasoning", "name": "General Intelligence & Reasoning", "questions": 50, "minutes": None, "kind": "mcq", "qualifying": False},
            {"slug": "general-awareness", "name": "General Awareness", "questions": 50, "minutes": None, "kind": "mcq", "qualifying": False},
            {"slug": "telecom-technical", "name": "General Engineering · Telecommunication (Part G)", "questions": 100, "minutes": None, "kind": "mcq", "qualifying": False},
        ],
        "extra_assessments": [],
        "notice_url": SSC_JE_NOTICE,
    },
    {
        "slug": "ssc-je-telecom-paper-2",
        "family": "je",
        "stage": "paper-2",
        "stream": "telecom",
        "name": "SSC JE Telecom Paper II",
        "subtitle": "Telecom technical · advanced",
        "status": "planned",
        "total_questions": 100,
        "duration_minutes": 120,
        "positive_marks": 3.0,
        "negative_marks": 1.0,
        "sections": [
            {"slug": "telecom-technical", "name": "General Engineering · Telecommunication (Part G)", "questions": 100, "minutes": None, "kind": "mcq", "qualifying": False},
        ],
        "extra_assessments": [],
        "notice_url": SSC_JE_NOTICE,
    },
)


def list_exam_catalog() -> list[dict]:
    """Return copies so API or future caller mutations cannot alter blueprints."""
    return [deepcopy(item) for item in EXAM_CATALOG]


def get_exam_blueprint(slug: str) -> dict | None:
    for item in EXAM_CATALOG:
        if item["slug"] == slug:
            return deepcopy(item)
    return None


def is_published_exam(slug: str) -> bool:
    item = get_exam_blueprint(slug)
    return bool(item and item["status"] == "ready")
