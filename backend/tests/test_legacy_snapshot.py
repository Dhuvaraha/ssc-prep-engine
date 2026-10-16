import base64
import sqlite3

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from app.db import Base
from app.models import Question, QuestionOption
from app.services.legacy_snapshot import capture_question
from app.services.revision_ledger import Ledger


@pytest.fixture
def rows():
    engine=create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine,expire_on_commit=False) as db:
        q=Question(id=42,exam_id=1,subject_id=1,topic_id=None,question_text='Incomplete legacy stem',
            correct_option=None,explanation=None,fast_method='Retain this',source_type='unknown',
            source_reference='legacy-source',source_chosen_option=3,review_notes='Uncertain',
            question_image_url='https://example.invalid/private-figure')
        options=[QuestionOption(id=8,question_id=42,position=3,text=None,image_url='data:image/svg+xml;base64,'+base64.b64encode(b'<svg/>').decode()),
                 QuestionOption(id=9,question_id=42,position=1,text='Text',image_url=None)]
        db.add_all([q,*options]);db.commit()
        db.refresh(q)
        for option in options:db.refresh(option)
        db.refresh(q,['options'])
        yield db,q,options
    engine.dispose()


def test_all_legacy_columns_and_nulls_preserved(rows):
    db,q,options=rows
    expected={c.key:getattr(q,c.key) for c in inspect(q).mapper.column_attrs}
    captured=capture_question(q,options,expected_option_ids={8,9})
    assert captured['question']==expected
    assert captured['question']['correct_option'] is None
    assert captured['question']['source_chosen_option']==3
    assert [o['id'] for o in captured['options']]==[8,9]
    assert [o['position'] for o in captured['options']]==[3,1]
    assert captured['original_version_unknown'] and not captured['publication_eligible']
    assert not db.dirty and not db.new and not db.deleted
    assert captured['asset_refs'][0]['content_sha256'] is None
    assert captured['asset_refs'][1]['bytes_verified']


def test_capture_restart_immutability_and_no_publication(rows,tmp_path):
    _,q,options=rows
    ledger=Ledger(tmp_path/'captures.sqlite')
    snapshot=capture_question(q,options,expected_option_ids={8,9})
    cid=ledger.capture_legacy(snapshot,operator='editor')
    before=ledger.legacy_capture(cid)
    assert ledger.capture_legacy(snapshot,operator='later-retry')==cid
    assert ledger.legacy_capture(cid)==before
    for statement in ["UPDATE legacy_captures SET operator='changed'",'DELETE FROM legacy_captures',
                      'INSERT OR REPLACE INTO legacy_captures SELECT * FROM legacy_captures']:
        with pytest.raises(sqlite3.IntegrityError,match='immutable'):ledger.db.execute(statement)
    with pytest.raises(ValueError,match='Unknown revision'):
        ledger.publish(cid,actor='editor',expected_publication_id=None)
    assert ledger.head(42) is None
    ledger.close()


def test_snapshot_detached_from_later_edits(rows):
    _,q,options=rows
    old=capture_question(q,options,expected_option_ids={8,9})
    q.explanation='Later correction'
    options[0].image_url='data:image/svg+xml;base64,'+base64.b64encode(b'<svg><rect/></svg>').decode()
    new=capture_question(q,options,expected_option_ids={8,9})
    assert old['question']['explanation'] is None
    assert new['asset_refs'][1]['content_sha256']!=old['asset_refs'][1]['content_sha256']


def test_no_implicit_database_queries(rows):
    db,q,options=rows
    db.expire(q,['explanation'])
    with pytest.raises(ValueError,match='explicitly loaded'):capture_question(q,options,expected_option_ids={8,9})


def test_wrong_question_options_rejected(rows):
    _,q,options=rows
    options[0].question_id=99
    with pytest.raises(ValueError,match='another question'):capture_question(q,options,expected_option_ids={8,9})


def test_partial_option_set_rejected(rows):
    _,q,options=rows
    with pytest.raises(ValueError,match='complete loaded option set'):
        capture_question(q,options[:1],expected_option_ids={8,9})


def test_unloaded_options_rejected_without_query(rows):
    db,q,options=rows
    db.expire(q,['options'])
    with pytest.raises(ValueError,match='complete options'):
        capture_question(q,options,expected_option_ids={8,9})


def test_filtered_loaded_relation_cannot_claim_complete_capture(rows):
    from sqlalchemy import select
    from sqlalchemy.orm import contains_eager
    db,q,_=rows
    db.expunge_all()
    expected=set(db.scalars(select(QuestionOption.id).where(QuestionOption.question_id==42)))
    filtered=db.scalars(select(Question).join(Question.options).where(Question.id==42,QuestionOption.id==8)
        .options(contains_eager(Question.options))).unique().one()
    assert len(filtered.options)==1
    with pytest.raises(ValueError,match='independent option-ID evidence'):
        capture_question(filtered,filtered.options,expected_option_ids=expected)
