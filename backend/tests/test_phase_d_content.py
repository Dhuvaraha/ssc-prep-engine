"""Content evidence checks do not award editorial or production approval."""
import re
import json
from fractions import Fraction as F
from app.services.pilot_curriculum import DATA, load_unit


def test_authored_files_are_valid_but_not_implicitly_reviewed():
    for path in (DATA/'phase_d_units').glob('*.json'):
        unit=load_unit(path.stem)
        assert unit is not None
        assert not unit.reviewed()
        assert not unit.subject_review and not unit.teaching_review


def test_time_work_keys_independently_recomputed_from_stems():
    for oid in ('TW-1','TW-2','TW-3','TW-4','TW-5'):
        unit=load_unit(oid)
        for checks in unit.checks.values():
            for q in checks:
                if q.family.startswith('contextual-'):
                    continue  # Verified separately with work/rate equations below.
                numbers=[int(n) for n in re.findall(r'\d+',q.stem.split('\n')[0])]
                actual=q.options[q.answer-1].removesuffix(' days')
                if oid=='TW-1':
                    expected=F(numbers[1],numbers[0]) if 'work units' in q.stem else F(numbers[0])*F(3,4)
                elif oid=='TW-2':
                    if 'per day?' in q.stem:
                        assert actual==f'1/{numbers[0]} job/day'
                        continue
                    expected=F(numbers[1]*60)
                elif oid=='TW-3':
                    a,b=numbers
                    expected=F(a*b,a+b) if q.family=='simultaneous-rate' else F(a*b,b-a)
                elif oid=='TW-4':
                    if q.family=='retry':
                        a,b,t=numbers
                        expected=t+(1-F(t,a))/(F(1,a)+F(1,b))
                    elif q.family=='transfer':
                        a,b,c,total=numbers
                        expected=(1-F(total,a))/(F(1,b)+F(1,c))
                    else:
                        a,b=numbers;remaining=F(1);expected=F(0);day=0
                        while remaining:
                            rate=F(1,a if day%2==0 else b)
                            duration=min(F(1),remaining/rate)
                            remaining-=rate*duration;expected+=duration;day+=1
                else:
                    a,b,t=numbers
                    expected=F(t*a,b) if 'equal jobs' in q.stem else F(t*(a+b),a)
                assert F(actual)==expected,(oid,q.id,actual,expected)


def test_percentage_grid_has_twenty_five_equal_cells_shaded():
    unit=load_unit('PCT-1')
    scene=unit.illustrations[1]
    assert len(scene.lines)==22
    polygon=scene.polygons[0]
    area=abs(sum(polygon[i].x*polygon[(i+1)%len(polygon)].y
                 -polygon[(i+1)%len(polygon)].x*polygon[i].y for i in range(len(polygon))))/2
    assert area/(100*100)==0.25


def test_contextual_time_work_delayed_keys_from_independent_equations():
    expected = {
        'TW-1': [(2+F(1,2))/5, F(30,30+2*10), 240*(1-F(3,8)), F(80-30,80)],
        'TW-2': [F(30,60)/F(5,2), 1/F(3,10), 1-F(18,48), F(60,12)],
        'TW-3': [F(150,24+36), 1/(F(1,6)-F(1,15)), F(90-25-35), 1-2*(F(1,8)+F(1,12))],
        'TW-5': [F(3,2), F(20)/F(125,100), F(64*3,3+5), F(12,18)],
    }
    for oid, values in expected.items():
        for q, value in zip(load_unit(oid).checks['revision'], values, strict=True):
            assert F(q.options[q.answer-1].replace(':','/')) == value, q.id


def test_time_work_assumptions_numeric_models():
    values = {
        'fatigue': F(20,10)+F(20,5), 'shared-resource': F(900,min(30+30,45)),
        'leak-sign': F(150-30,20-5), 'downtime': 24*(15-5), 'availability': 15*(2+3),
    }
    for checks in load_unit('TW-6').checks.values():
        for q in checks:
            if q.family in values:
                assert F(q.options[q.answer-1].split()[0]) == values[q.family]


def test_percentage_comparison_and_product_keys_from_stated_quantities():
    for oid in ('PCT-4','PCT-5','PCT-6'):
        for checks in load_unit(oid).checks.values():
            for q in checks:
                stem=q.stem.split(' Partly worked:')[0]
                numbers=[F(n) for n in re.findall(r'\d+(?:/\d+)?',stem)]
                if q.family=='restoring-after-two-losses':
                    expected=(1/((1-F(20,100))*(1-F(25,100)))-1)*100
                elif q.family=='budget-from-absolute-amounts':
                    expected=(12-F(660,60))/12*100
                elif q.family=='compound-unit-price':
                    expected=(1-1/((1+F(20,100))*(1-F(5,100))))*100
                elif oid=='PCT-4':
                    if q.family=='forward':
                        original,rise,fall=numbers
                        expected=original+original*rise/100
                        expected-=expected*fall/100
                    elif q.family=='reverse':
                        rise,fall,final=numbers
                        expected=final*100/(100-fall)*100/(100+rise)
                    else:
                        rise,target=numbers
                        expected=(rise-target)/(100+rise)*100
                elif oid=='PCT-5':
                    p=numbers[0]
                    expected=p*100/(100+p if 'more than' in stem.split('.')[0] else 100-p)
                else:
                    price=numbers[0]*(-1 if 'price falls' in stem else 1)
                    budget=0 if len(numbers)==1 else numbers[1]*(-1 if 'spending falls' in stem else 1)
                    expected=abs(F(100+budget,100+price)-1)*100
                assert F(q.options[q.answer-1])==expected,(q.id,expected)


def test_authored_text_has_no_corrupted_embedded_question_mark():
    for path in (DATA/'phase_d_units').glob('*.json'):
        assert not re.search(r'[\w)]\?[\w(]',path.read_text(encoding='utf-8')),path.name


def test_authored_delivery_varies_positions_and_preserves_answer_reason_alignment():
    from app.services import teaching_journey as journey
    for path in (DATA/'phase_d_units').glob('*.json'):
        unit=load_unit(path.stem);content=unit.content()
        answer_positions=set();reason_positions=set()
        for stage,checks in unit.checks.items():
            state=journey.initial(content);state['stage']=stage
            for raw in checks:
                delivered=content.question(state)
                assert delivered['options'][delivered['answer']-1]==raw.options[raw.answer-1]
                assert delivered['explanations'][delivered['answer']-1]==raw.explanations[raw.answer-1]
                assert delivered['reason_options'][delivered['reason_answer']-1]==raw.reason_options[raw.reason_answer-1]
                answer_positions.add(delivered['answer']);reason_positions.add(delivered['reason_answer'])
                state['history'].append({'question_id':raw.id})
        assert len(answer_positions)>1,path.name
        assert len(reason_positions)>1,path.name


def test_categorical_translation_options_are_not_logically_equivalent():
    from app.content.syllogism import evaluate
    kinds=('all','no','some','some_not')
    unit=load_unit('SYL-1')
    for checks in unit.checks.values():
        for q in checks:
            source=(q.family.removeprefix('translate-'),'A','B')
            equivalent=[]
            for kind in kinds:
                candidate=(kind,'A','B')
                equivalent.append(evaluate([source],candidate)['must_follow']
                                  and evaluate([candidate],source)['must_follow'])
            assert equivalent==[i==q.answer-1 for i in range(4)]


def test_finite_model_keys_and_rendered_membership_evidence():
    unit=load_unit('SYL-2')
    questions={q.id:q for checks in unit.checks.values() for q in checks}
    evidence=json.loads((DATA/'phase_d_logic_evidence.json').read_text(encoding='utf-8'))
    assert {row['question_id'] for row in evidence}==set(questions)
    for row in evidence:
        q=questions[row['question_id']]
        accepted=[]
        for index,model in enumerate(row['models']):
            results=[]
            for kind,left,right in row['premises']:
                if kind=='all':
                    results.append(all(right in obj for obj in model if left in obj))
                elif kind=='no':
                    results.append(all(right not in obj for obj in model if left in obj))
                elif kind=='some':
                    results.append(any(left in obj and right in obj for obj in model))
                else:
                    assert kind=='some_not'
                    results.append(any(left in obj and right not in obj for obj in model))
            accepted.append(all(results))
            rendered=('No objects exist.' if not model else '; '.join(
                f'Object {i+1} belongs exactly to '+', '.join(obj) for i,obj in enumerate(model))
                +'. No other objects exist.')
            assert q.options[index]==rendered
        assert accepted==[i==q.answer-1 for i in range(4)]


def test_necessity_keys_against_all_valid_categorical_models():
    from app.content.syllogism import evaluate
    questions={q.id:q for checks in load_unit('SYL-3').checks.values() for q in checks}
    evidence=json.loads((DATA/'phase_d_necessity_evidence.json').read_text(encoding='utf-8'))
    assert {row['question_id'] for row in evidence}==set(questions)
    for row in evidence:
        result=evaluate(row['premises'],row['conclusion'])
        key=(4 if not result['consistent'] else 1 if result['must_follow']
             else 2 if result['possible'] else 3)
        assert questions[row['question_id']].answer==key
