import pytest

from app.services.entitlement_admin import apply_manifest, manifest_digest
from app.services.entitlement_proposal import propose
from app.scripts.rehearse_entitlement_inventory import run


def inventory():
    return {"sources": [{"exam_id": 1, "source_type": "official", "source_reference": "Synthetic fact source",
                         "question_ids": [10, 11]}],
            "users": [{"id": 5, "observed_exam_ids": [1], "focus": "cgl"}],
            "exams": [{"id": 1, "slug": "cgl"}],
            "resources": [{"kind": "lesson", "id": 7, "topic_id": 3, "exam_id": 1}],
            "lesson_blocks": [{"id": 8, "lesson_id": 7}], "assets": [],
            "baseline": {"questions": 2}}


def test_proposal_preserves_exact_ids_without_inventing_rights_or_grants():
    proposal = propose(inventory())
    assert [r["resource_id"] for r in proposal["bindings"]] == [10, 11]
    assert proposal["sources"][0]["rights_basis"] is None
    assert not proposal["sources"][0]["private_use_approved"]
    assert proposal["courses"][0]["active"] is False
    assert proposal["grants"] == []
    assert proposal["unresolved_resource_bindings"][0]["proposed_source_ids"] == []
    assert proposal == propose(inventory())


def test_draft_is_rejected_before_database_access_even_with_matching_digest():
    proposal = propose(inventory())
    with pytest.raises(ValueError, match="Draft entitlement"):
        apply_manifest(None, proposal, approved_digest=manifest_digest(proposal))


def test_truncated_inventory_is_rejected():
    data = inventory()
    data["baseline"]["questions"] = 3
    with pytest.raises(ValueError, match="incomplete"):
        propose(data)


def test_evidenced_originals_are_separated_from_unresolved_content_without_grants():
    proposal = propose(inventory(), repository_original_ids=[10])
    assert len(proposal["sources"]) == 2
    original = next(s for s in proposal["sources"] if s["rights_basis"] == "original")
    assert original["third_party_republication_approval_needed"] is False
    assert not original["private_use_approved"] and not original["public_use_approved"]
    assert proposal["grants"] == []
    assert len({b["source_id"] for b in proposal["bindings"]}) == 2
    with pytest.raises(ValueError, match="unknown question"):
        propose(inventory(), repository_original_ids=[999])


def test_changing_draft_header_cannot_bypass_unresolved_lineage():
    proposal = propose(inventory())
    proposal.update(approval_status="reviewed", executable=True)
    with pytest.raises(ValueError, match="unresolved resource"):
        apply_manifest(None, proposal)
    proposal["unresolved_resource_bindings"] = []
    with pytest.raises(ValueError, match="contributors"):
        apply_manifest(None, proposal)


@pytest.mark.parametrize("url", [
    "postgresql+psycopg://u@remote.example/ssc_phase_a_test",
    "postgresql+psycopg://u@127.0.0.1/production",
    "postgresql+psycopg://u@127.0.0.1/ssc_phase_a_test?host=remote.example",
    "postgresql+psycopg://u@127.0.0.1/ssc_phase_a_test?hostaddr=192.0.2.1",
    "postgresql+psycopg://u@127.0.0.1/ssc_phase_a_test?service=remote",
])
def test_rehearsal_rejects_remote_or_override_before_any_inventory_or_connection(url):
    with pytest.raises(ValueError):
        run({}, {}, url)
