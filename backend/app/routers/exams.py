from fastapi import APIRouter

router = APIRouter(prefix="/exams", tags=["exams"])

CGL_TIER_1 = {
    "slug": "ssc-cgl-tier-1",
    "name": "SSC CGL Tier I",
    "duration_minutes": 60,
    "total_questions": 100,
    "positive_marks": 2.0,
    "negative_marks": 0.5,
    "sections": [
        {"slug": "reasoning", "name": "General Intelligence & Reasoning", "questions": 25},
        {"slug": "general-awareness", "name": "General Awareness", "questions": 25},
        {"slug": "quant", "name": "Quantitative Aptitude", "questions": 25},
        {"slug": "english", "name": "English Comprehension", "questions": 25},
    ],
}


@router.get("")
def list_exams() -> list[dict]:
    return [CGL_TIER_1]


@router.get("/{slug}")
def get_exam(slug: str) -> dict:
    if slug == CGL_TIER_1["slug"]:
        return CGL_TIER_1
    return {"error": "Exam not found"}
