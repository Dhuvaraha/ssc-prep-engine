from pydantic import BaseModel, Field


class ImportedOption(BaseModel):
    position: int = Field(ge=1, le=10)
    text: str | None = None
    image_url: str | None = None


class ImportedQuestion(BaseModel):
    exam_slug: str
    subject_slug: str
    topic_slug: str | None = None
    question_text: str
    question_image_url: str | None = None
    options: list[ImportedOption]
    correct_option: int | None = None
    explanation: str | None = None
    fast_method: str | None = None
    difficulty: int = Field(default=2, ge=1, le=5)
    expected_time_seconds: int | None = Field(default=None, ge=1)
    year: int | None = None
    shift: str | None = None
    source_type: str = "user_private"
    source_reference: str | None = None
    source_page: int | None = Field(default=None, ge=1)
    requires_visual_review: bool = False
    source_chosen_option: int | None = Field(default=None, ge=1, le=10)
    source_question_id: str | None = None
    source_status: str | None = None
    visibility: str = "private"
    verification_status: str = "review_required"
