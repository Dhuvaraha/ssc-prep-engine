import pytest
from app.services.entitlement_coverage import coverage


def fixture(svg='<svg xmlns="http://www.w3.org/2000/svg"><rect width="2"/></svg>'):
    return ({'assets':[{'usage':'stem','question_ids':[1],'asset_url':'data:image/svg+xml,'+svg}],
             'resources':[{'kind':'lesson','id':1,'topic_id':1}]},
            {'question_groups':[{'ids':[1],'exam_id':1,'subject_id':1,'topic_id':1,'difficulty':1}]},
            {'sources':[{'id':'a','authorship_status':'repository_generated_content_match'}],
             'bindings':[{'resource_kind':'question','resource_id':1,'source_id':'a'}],
             'courses':[{'user_id':1,'exam_id':1,'active':False}],'grants':[]})


def test_asset_mapping_is_not_visual_or_rights_approval():
    result=coverage(*fixture())
    assert result['assets'][0]['source_ids']==['a']
    assert result['assets'][0]['static_svg_screen_passed']
    assert not result['assets'][0]['visual_review_complete']
    assert result['active_source_grants']==0
    assert result['resource_mapping_gaps'][0]['contributor_status']=='unresolved'


@pytest.mark.parametrize('svg',['<svg><script>bad()</script></svg>','<svg onload="bad()"/>','<svg><image href="https://example.invalid"/></svg>','<!DOCTYPE svg><svg/>','broken'])
def test_unsafe_or_malformed_assets_remain_blocked(svg):
    assert not coverage(*fixture(svg))['assets'][0]['static_svg_screen_passed']


def test_missing_bindings_rejected():
    inventory,topology,proposal=fixture()
    proposal['bindings']=[]
    with pytest.raises(ValueError):
        coverage(inventory,topology,proposal)


def test_rehearsal_checks_asset_mapping_without_granting_rights():
    from app.scripts.rehearse_entitlement_inventory import validate_asset_coverage
    inventory,topology,proposal=fixture()
    report=coverage(inventory,topology,proposal)
    assert validate_asset_coverage(inventory,proposal,report)['mapped_asset_reference_groups']==1
    report['assets'][0]['rights_approved']=True
    with pytest.raises(ValueError,match='approval'):
        validate_asset_coverage(inventory,proposal,report)


def test_rehearsal_rejects_changed_source_and_missing_asset():
    from app.scripts.rehearse_entitlement_inventory import validate_asset_coverage
    inventory,topology,proposal=fixture()
    report=coverage(inventory,topology,proposal)
    report['assets'][0]['source_ids']=['wrong-source']
    with pytest.raises(ValueError,match='contributor'):
        validate_asset_coverage(inventory,proposal,report)


def test_stale_asset_bytes_cannot_reuse_screening():
    from app.scripts.rehearse_entitlement_inventory import validate_asset_coverage
    inventory,topology,proposal=fixture()
    report=coverage(inventory,topology,proposal)
    inventory['assets'][0]['asset_url']='data:image/svg+xml,<svg onload="bad()"/>'
    with pytest.raises(ValueError,match='coverage'):
        validate_asset_coverage(inventory,proposal,report)
    report['assets']=[]
    with pytest.raises(ValueError,match='coverage'):
        validate_asset_coverage(inventory,proposal,report)
