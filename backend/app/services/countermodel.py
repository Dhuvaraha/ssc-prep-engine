"""Bounded, deterministic checking of learner-built categorical countermodels."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Statement = tuple[Literal['all','no','some','some_not'], str, str]


class CountermodelTask(BaseModel):
    model_config = ConfigDict(extra='forbid')
    terms: list[str] = Field(min_length=1,max_length=4)
    premises: list[Statement] = Field(min_length=1,max_length=8)
    conclusion: Statement

    @model_validator(mode='after')
    def known_terms(self):
        if len(set(self.terms))!=len(self.terms) or any(not t.strip() or len(t)>40 for t in self.terms):
            raise ValueError('Distinct, nonblank, bounded category names required')
        if any(a not in self.terms or b not in self.terms for _,a,b in [*self.premises,self.conclusion]):
            raise ValueError('Statement references an unknown category')
        return self


def holds(statement, objects):
    kind,a,b=statement
    if kind=='all':
        return all(b in obj for obj in objects if a in obj)
    if kind=='no':
        return all(b not in obj for obj in objects if a in obj)
    if kind=='some':
        return any(a in obj and b in obj for obj in objects)
    return any(a in obj and b not in obj for obj in objects)


def check(task, objects):
    task=CountermodelTask.model_validate(task)
    if (not isinstance(objects,list) or len(objects)>8
        or any(not isinstance(obj,list) or len(obj)>4
               or any(not isinstance(term,str) or term not in task.terms for term in obj)
               or len(set(obj))!=len(obj) for obj in objects)):
        raise ValueError('Submit up to eight objects, with each known category at most once per object')
    failed=[i+1 for i,p in enumerate(task.premises) if not holds(p,objects)]
    if failed:
        return False,'Your model violates premise(s) '+', '.join(map(str,failed))+'. Keep every premise true.'
    if holds(task.conclusion,objects):
        return False,'Your model satisfies the premises but also makes the conclusion true. A counterexample must make it false.'
    return True,'Every premise is true in your model and the conclusion is false. This is a valid counterexample.'
