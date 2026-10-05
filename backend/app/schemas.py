from pydantic import BaseModel, EmailStr, Field


class UserOut(BaseModel):
    id: int
    email: EmailStr
    display_name: str | None = None

    model_config = {"from_attributes": True}


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class SubjectOut(BaseModel):
    id: int
    slug: str
    name: str
    sort_order: int

    model_config = {"from_attributes": True}


class TopicOut(BaseModel):
    id: int
    subject_id: int
    slug: str
    name: str
    priority: int

    model_config = {"from_attributes": True}


class OptionOut(BaseModel):
    position: int
    text: str | None = None
    image_url: str | None = None

    model_config = {"from_attributes": True}


class QuestionOut(BaseModel):
    id: int
    topic_id: int | None = None
    question_text: str
    question_image_url: str | None = None
    difficulty: int
    expected_time_seconds: int | None = None
    year: int | None = None
    shift: str | None = None
    options: list[OptionOut]

    model_config = {"from_attributes": True}


class PracticeSubmit(BaseModel):
    question_id: int
    selected_option: int | None
    time_seconds: float = Field(ge=0)
    confidence: int | None = Field(default=None, ge=1, le=3)
    used_hint: bool = False
    mistake_type: str | None = None


class PracticeResult(BaseModel):
    correct: bool
    correct_option: int
    explanation: str | None = None
    fast_method: str | None = None
    mastery_score: float | None = None
    revision_scheduled: bool = False


class LessonOut(BaseModel):
    id: int
    topic_id: int
    title: str
    intro: str
    concept: str
    shortcut: str | None = None
    worked_example: str | None = None
    memory_rule: str | None = None
    common_traps: str | None = None
    estimated_minutes: int

    model_config = {"from_attributes": True}
