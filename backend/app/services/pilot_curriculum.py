"""Fixed Phase D scope and version-bound authored objective contracts.

Structural acceptance is never a substitute for subject/teaching/source review.
"""
import hashlib
import json
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator
from app.services.teaching_journey import JourneyContent, JourneyConflict

DATA = Path(__file__).resolve().parents[2] / 'data'
SCOPE = json.loads((DATA / 'phase_d_scope.json').read_text(encoding='utf-8'))
OBJECTIVES = {o['id']: {**o, 'topic': t['topic']} for t in SCOPE['topics'] for o in t['objectives']}
STAGES = ('entry', 'faded', 'independent_a', 'independent_b', 'revision')


class WorkedStep(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: str = Field(min_length=1)
    justification: str = Field(min_length=1)


class Point(BaseModel):
    model_config = ConfigDict(extra='forbid')
    x: float = Field(ge=-100,le=100,allow_inf_nan=False)
    y: float = Field(ge=-100,le=100,allow_inf_nan=False)


class Scene(BaseModel):
    model_config = ConfigDict(extra='forbid')
    description: str = Field(min_length=1)
    polygons: list[list[Point]] = Field(default_factory=list,max_length=8)
    dots: list[Point] = Field(default_factory=list,max_length=12)
    lines: list[list[Point]] = Field(default_factory=list,max_length=32)

    @model_validator(mode='after')
    def shape(self):
        if any(not 3<=len(p)<=12 for p in self.polygons) or any(len(line)!=2 for line in self.lines):
            raise ValueError('Invalid vector geometry')
        return self


class Figure(BaseModel):
    model_config = ConfigDict(extra='forbid')
    stem: Scene
    options: list[Scene] = Field(min_length=4,max_length=4)


class Check(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(min_length=1)
    family: str = Field(min_length=1)
    context: str = Field(min_length=1)
    stem: str = Field(min_length=1)
    options: list[str] = Field(min_length=4, max_length=4)
    answer: StrictInt = Field(ge=1, le=4)
    explanations: list[str] = Field(min_length=4, max_length=4)
    repairs: list[str] = Field(min_length=4, max_length=4)
    reason_prompt: str = Field(min_length=1)
    reason_options: list[str] = Field(min_length=2, max_length=4)
    reason_answer: StrictInt = Field(ge=1, le=4)
    reason_explanation: str = Field(min_length=1)
    passage: str | None = None
    figure: Figure | None = None
    diagram: Scene | None = None

    @model_validator(mode='after')
    def complete(self):
        for values in (self.options, self.explanations, self.repairs, self.reason_options):
            if any(not value.strip() for value in values):
                raise ValueError('Blank instructional content')
        if len(set(self.options)) != 4 or len(set(self.reason_options)) != len(self.reason_options):
            raise ValueError('Duplicate choices')
        if self.reason_answer > len(self.reason_options):
            raise ValueError('Reason key outside choices')
        return self


class ObjectiveUnit(BaseModel):
    model_config = ConfigDict(extra='forbid')
    objective_id: str
    prerequisites: list[str] = Field(min_length=1)
    explanation: str = Field(min_length=1)
    worked: list[WorkedStep] = Field(min_length=2)
    illustrations: list[Scene] = Field(default_factory=list,max_length=8)
    hint: str = Field(min_length=1)
    shortcut: str = Field(min_length=1)
    limitation: str = Field(min_length=1)
    checks: dict[str, list[Check]]
    sources: list[str] = Field(min_length=1)
    subject_review: str = ''
    teaching_review: str = ''
    review_digest: str = ''

    @model_validator(mode='after')
    def coverage(self):
        if self.objective_id not in OBJECTIVES or set(self.checks) != set(STAGES):
            raise ValueError('Approved objective and complete stage mapping required')
        if any(not items for items in self.checks.values()):
            raise ValueError('Each stage requires authored checks')
        if len(self.checks['revision']) < 2:
            raise ValueError('Two held-out delayed forms are required for the retention contract')
        checks = [q for items in self.checks.values() for q in items]
        if len({q.id for q in checks}) != len(checks) or len({q.stem for q in checks}) != len(checks):
            raise ValueError('Repeated assessment identity or stem')
        a, b, delayed = (self.checks[s][0] for s in ('independent_a','independent_b','revision'))
        if len({a.context,b.context,delayed.context}) != 3:
            raise ValueError('Independent and delayed contextual forms must differ')
        return self

    def digest(self):
        payload = self.model_dump(exclude={'subject_review','teaching_review','review_digest'})
        return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()

    def reviewed(self):
        return bool(self.subject_review.strip() and self.teaching_review.strip()
                    and self.review_digest == self.digest() and not self.release_gaps())

    def release_gaps(self):
        # Retry capacity is a release gate, not permission to manufacture clones.
        gaps=[f'{stage}: fresh repair check missing' for stage in STAGES[:-1] if len(self.checks[stage])<2]
        if len(self.checks['revision'])<4:
            gaps.append('revision: delayed failure/repair/recheck reserve missing')
        return gaps

    def content(self):
        def question(state):
            seen = {event.get('question_id') for event in state['history']}
            available = [q for q in self.checks[state['stage']] if q.id not in seen]
            if not available:
                raise JourneyConflict('No fresh reviewed check remains; further editorial content is required')
            return available[0].model_dump(exclude_none=True)
        lesson = dict(objective=OBJECTIVES[self.objective_id]['description'],
            prerequisites=self.prerequisites,worked_example=[self.explanation]+[
                step.action+' — '+step.justification for step in self.worked],
            shortcut=self.shortcut,limit=self.limitation)
        if self.illustrations:
            lesson['illustrations']=[scene.model_dump() for scene in self.illustrations]
        return JourneyContent(self.digest(),lesson,question,self.hint,
            learning_stages=STAGES[:-1],guided_stages=('entry','faded'),track_exposure=True,
            repeat_revision=False,reason_after_answer=True)


def load_unit(objective_id):
    if objective_id not in OBJECTIVES:
        return None
    path = DATA / 'phase_d_units' / (objective_id+'.json')
    return ObjectiveUnit.model_validate_json(path.read_text(encoding='utf-8')) if path.exists() else None


def audit():
    result = {}
    for oid in OBJECTIVES:
        try:
            unit = load_unit(oid)
            result[oid] = 'reviewed' if unit and unit.reviewed() else 'draft' if unit else 'missing'
        except ValueError:
            result[oid] = 'invalid'
    return dict(objectives=result, engineering_complete=False,
                note='Coverage and review status only; integrated phase acceptance remains separate.')
