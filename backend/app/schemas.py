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


class ProfileUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


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
    subtopic: str | None = None
    pattern_type: str | None = None
    question_text: str
    question_image_url: str | None = None
    difficulty: int
    expected_time_seconds: int | None = None
    year: int | None = None
    shift: str | None = None
    options: list[OptionOut]

    model_config = {"from_attributes": True}


class SolvedExampleOut(BaseModel):
    id: int
    pattern_type: str | None = None
    question_text: str
    question_image_url: str | None = None
    difficulty: int
    expected_time_seconds: int | None = None
    year: int | None = None
    shift: str | None = None
    correct_option: int
    explanation: str | None = None
    fast_method: str | None = None
    options: list[OptionOut]

    model_config = {"from_attributes": True}


class PracticeSubmit(BaseModel):
    question_id: int
    selected_option: int | None = Field(ge=1, le=4)
    time_seconds: float = Field(ge=0)
    confidence: int | None = Field(default=None, ge=1, le=3)
    used_hint: bool = False
    mistake_type: str | None = None


class PracticeCoaching(BaseModel):
    pattern_name: str | None = None
    skill: str | None = None
    recognition_cues: str | None = None
    standard_method: str | None = None
    fast_method: str | None = None
    common_trap: str | None = None
    difficulty_rule: str | None = None
    worked_example: str | None = None
    hint_steps: list[str] = Field(default_factory=list)
    archetype_exact: bool = False


class PracticeResult(BaseModel):
    attempt_id: int
    correct: bool
    correct_option: int
    explanation: str | None = None
    fast_method: str | None = None
    mastery_score: float | None = None
    revision_scheduled: bool = False
    coaching: PracticeCoaching | None = None


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


class LessonBlockOut(BaseModel):
    id: int
    lesson_id: int
    block_type: str
    title: str
    body: str
    difficulty: int | None = None
    sort_order: int

    model_config = {"from_attributes": True}


class QuestionArchetypeOut(BaseModel):
    id: int
    topic_id: int
    slug: str
    name: str
    skill: str
    recognition_cues: str
    canonical_method: str
    shortcut_method: str | None = None
    common_trap: str | None = None
    easy_rule: str | None = None
    medium_rule: str | None = None
    hard_rule: str | None = None
    expected_time_seconds: int
    source_notes: str | None = None

    model_config = {"from_attributes": True}


class MistakeUpdate(BaseModel):
    mistake_type: str


class MockStartRequest(BaseModel):
    mode: str = Field(pattern="^(mini|full|sectional|topic)$")
    subject_slug: str | None = None
    topic_id: int | None = None


class MockResponseUpdate(BaseModel):
    question_id: int
    selected_option: int | None = Field(default=None, ge=1, le=4)
    marked_for_review: bool = False
    time_seconds: float = Field(default=0, ge=0)


class MockQuestionOut(BaseModel):
    position: int
    section_slug: str
    question: QuestionOut


class MockStartResponse(BaseModel):
    attempt_id: int
    mode: str
    duration_minutes: int
    questions: list[MockQuestionOut]
    resumed_existing: bool = False


class MockSubmitResponse(BaseModel):
    attempt_id: int
    score: float
    correct: int
    incorrect: int
    unattempted: int
    total_questions: int
