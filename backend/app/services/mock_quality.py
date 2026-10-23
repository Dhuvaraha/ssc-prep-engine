"""Evidence-based offline mock review; difficulty labels are not evidence.

Blueprints must be supplied by a reviewer. This evaluator neither edits the bank
nor substitutes analytic screening for empirical learner calibration.
"""
from collections import Counter


def evaluate(items, blueprint):
    sections=blueprint.get('sections', {})
    reference=blueprint.get('reference')
    if not sections or blueprint.get('reviewed') is not True or not isinstance(reference,str) or not reference.strip():
        raise ValueError('Reviewed blueprint reference required')
    if any(type(count) is not int or count < 1 for count in sections.values()):
        raise ValueError('Positive section counts required')
    minimum=blueprint.get('minimum_families', {})
    if set(minimum)!=set(sections) or any(type(n) is not int or n<1 or n>sections[s] for s,n in minimum.items()):
        raise ValueError('Explicit feasible family coverage per section required')
    problems=[]
    actual=Counter(item.get('section') for item in items)
    if dict(actual)!=sections:
        problems.append('section_counts_do_not_match_reviewed_blueprint')
    identities=[item.get('revision_id') for item in items]
    if any(not isinstance(i,str) or not i.strip() for i in identities) or len(set(identities))!=len(identities):
        problems.append('missing_or_duplicate_revision_identity')
    families={section:set() for section in sections}
    for index,item in enumerate(items):
        family=item.get('family')
        if item.get('section') in families and isinstance(family,str) and family.strip():
            families[item['section']].add(family)
        else:
            problems.append(f'item_{index}:missing_family_or_section')
        evidence=item.get('quality_evidence',{})
        for field in ('answer_validated','distractors_validated','reasoning_reviewed','source_consistency_checked'):
            if evidence.get(field) is not True:
                problems.append(f'item_{index}:{field}')
        for field in ('reasoning_description','distractor_analysis','review_reference'):
            if not isinstance(evidence.get(field),str) or not evidence[field].strip():
                problems.append(f'item_{index}:missing_{field}')
        if item.get('requires_visual') and evidence.get('visual_reviewed') is not True:
            problems.append(f'item_{index}:visual_review_required')
        if evidence.get('source_inconsistent') is not False:
            problems.append(f'item_{index}:source_consistency_unresolved')
    for section,count in minimum.items():
        if len(families[section])<count:
            problems.append(f'{section}:insufficient_reviewed_family_variation')
    return {'analytic_screen_passed':not problems,'problems':problems,
            'family_counts':{s:len(f) for s,f in families.items()},
            'blueprint_reference':blueprint['reference'],
            'empirically_calibrated':False,'exam_equivalence_proven':False}
