from copy import deepcopy
import pytest
from app.services.mock_quality import evaluate


def fixture():
    blueprint={'reviewed':True,'reference':'synthetic-review','sections':{'quant':2,'ga':1},'minimum_families':{'quant':2,'ga':1}}
    evidence={'answer_validated':True,'distractors_validated':True,'reasoning_reviewed':True,
        'source_consistency_checked':True,'source_inconsistent':False,'reasoning_description':'Translate changing bases into a model',
        'distractor_analysis':'Each wrong option isolates a different error','review_reference':'independent-calculation'}
    items=[{'revision_id':str(i),'section':s,'family':f,'quality_evidence':deepcopy(evidence)}
           for i,(s,f) in enumerate([('quant','successive_rates'),('quant','geometry_feasibility'),('ga','dated_recall')])]
    return items,blueprint


def test_labels_cannot_establish_quality():
    items,blueprint=fixture()
    for item in items:item.update(difficulty=3,quality_evidence={})
    assert not evaluate(items,blueprint)['analytic_screen_passed']


def test_valid_screen_does_not_claim_empirical_equivalence():
    report=evaluate(*fixture())
    assert report['analytic_screen_passed']
    assert not report['empirically_calibrated'] and not report['exam_equivalence_proven']


@pytest.mark.parametrize('defect',['duplicate','family','section','visual','inconsistent','missing_reasoning'])
def test_real_quality_defects_are_blocked(defect):
    items,blueprint=fixture()
    if defect=='duplicate':items[1]['revision_id']=items[0]['revision_id']
    if defect=='family':items[1]['family']=items[0]['family']
    if defect=='section':items[1]['section']='ga'
    if defect=='visual':items[1]['requires_visual']=True
    if defect=='inconsistent':items[1]['quality_evidence']['source_inconsistent']=True
    if defect=='missing_reasoning':items[1]['quality_evidence']['reasoning_description']=' '
    assert not evaluate(items,blueprint)['analytic_screen_passed']


@pytest.mark.parametrize('reference',[None,1,True,'',' '])
def test_missing_review_reference_is_not_stringified(reference):
    items,blueprint=fixture()
    blueprint['reference']=reference
    with pytest.raises(ValueError,match='reference'):
        evaluate(items,blueprint)
