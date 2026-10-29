from datetime import datetime
from decimal import Decimal
import pytest
from app.services.percentage_journey import question, assess, ITEMS


def test_original_keys_and_four_option_explanations():
    answers = [Decimal(500)*Decimal('.8')*Decimal('.9'),
               Decimal(800)*Decimal('.75')*Decimal('.9'),
               100-Decimal(140)*Decimal('.9')*Decimal('.8')*Decimal('.95'),
               Decimal(1200)*Decimal('.85')*Decimal('.8')]
    assert answers == [Decimal(360),Decimal(540),Decimal('4.24'),Decimal(816)]
    assert [i['answer'] for i in ITEMS] == [2,2,1,2]
    assert all(len(i['explanations']) == len(i['repairs']) == 4 for i in ITEMS)


def test_delivery_has_no_key_or_repair_leak():
    assert set(question('transfer')) == {'id','stem','options'}


@pytest.mark.parametrize('assisted,repeated', [(True,False),(False,True),(True,True)])
def test_assisted_or_repeated_answers_do_not_create_mastery(assisted,repeated):
    result=assess('transfer',1,assisted=assisted,previously_answered=repeated,now=datetime(2026,10,23))
    assert result['correct'] and not result['independent_evidence']
    assert result['revision_due_at'] is None


def test_wrong_choice_gets_specific_repair_and_independent_transfer_schedules_revision():
    now=datetime(2026,10,23)
    wrong=assess('transfer',4,assisted=False,previously_answered=False,now=now)
    assert 'customer payment' in wrong['repair'] and not wrong['independent_evidence']
    right=assess('transfer',1,assisted=False,previously_answered=False,now=now)
    assert right['revision_due_at']=='2026-10-24T00:00:00' and right['exam_readiness'] is None
