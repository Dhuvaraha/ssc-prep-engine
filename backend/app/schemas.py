from pydantic import BaseModel


class OptionOut(BaseModel):
    position: int
    text: str | None = None
    image_url: str | None = None


class QuestionOut(BaseModel):
    id: int
    question_text: str
    question_image_url: str | None = None
    difficulty: int
    options: list[OptionOut]

    model_config = {"from_attributes": True}


class PracticeSubmit(BaseModel):
    question_id: int
    selected_option: int | None
    time_seconds: float
    confidence: int | None = None
    used_hint: bool = False
    mistake_type: str | None = None


class PracticeResult(BaseModel):
    correct: bool
    correct_option: int
    explanation: str | None = None
    fast_method: str | None = None
