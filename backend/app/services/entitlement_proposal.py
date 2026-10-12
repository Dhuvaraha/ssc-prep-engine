"""Build a non-executable review proposal from a private read-only inventory.

Recorded source references are candidate lineage, never proof of rights or all
contributors. No approval or learner grant is invented by this module.
"""
from collections import Counter
from hashlib import sha256
import json


def propose(inventory, *, repository_original_ids=()):
    original_ids = set(repository_original_ids)
    inventory_ids = {qid for group in inventory["sources"] for qid in group["question_ids"]}
    if not original_ids <= inventory_ids:
        raise ValueError("Authorship evidence references unknown question IDs")
    groups = []
    for group in inventory["sources"]:
        for is_original in (True, False):
            ids = [qid for qid in group["question_ids"] if (qid in original_ids) is is_original]
            if ids:
                groups.append({**group, "question_ids": ids, "repository_original": is_original})
    sources, bindings, seen = [], [], set()
    for group in groups:
        identity = json.dumps([group["exam_id"], group["source_type"], group["source_reference"], group["repository_original"]],
                              ensure_ascii=False, separators=(",", ":"))
        source_id = "review-" + sha256(identity.encode()).hexdigest()[:32]
        sources.append({"id": source_id, "exam_id": group["exam_id"],
                        "recorded_source_type": group["source_type"],
                        "recorded_source_reference": group["source_reference"],
                        "rights_basis": "original" if group["repository_original"] else None,
                        "authorship_status": "repository_generated_content_match" if group["repository_original"] else "unresolved",
                        "third_party_republication_approval_needed": False if group["repository_original"] else None,
                        "approval_reference": None,
                        "private_use_approved": False, "public_use_approved": False,
                        "lineage_review_status": "pending", "question_count": len(group["question_ids"])})
        for question_id in group["question_ids"]:
            if question_id in seen:
                raise ValueError("Question appears in multiple inventory source groups")
            seen.add(question_id)
            bindings.append({"resource_kind": "question", "resource_id": question_id,
                             "source_id": source_id, "review_status": "candidate_recorded_reference",
                             "complete_contributors_confirmed": False})
    if len(seen) != inventory["baseline"]["questions"]:
        raise ValueError("Question inventory is incomplete")
    courses = []
    for user in inventory["users"]:
        observed = set(user.get("observed_exam_ids", []))
        observed.update(exam["id"] for exam in inventory["exams"] if exam["slug"] == user.get("focus"))
        for exam_id in sorted(observed):
            courses.append({"user_id": user["id"], "exam_id": exam_id, "active": False,
                            "proposed_access": "preserve_observed_course_access",
                            "review_status": "pending_explicit_account_decision"})
    unresolved = [{"resource_kind": r["kind"], "resource_id": r["id"],
                   "topic_id": r["topic_id"], "exam_id": r["exam_id"],
                   "recorded_source_notes": r.get("recorded_source_notes"),
                   "reason": "Complete contributing sources not recorded in normalized lineage",
                   "proposed_source_ids": []} for r in inventory["resources"]]
    result = {"format_version": 1, "approval_status": "draft", "executable": False,
              "operator": "pending_operator_review", "reason": "Read-only recovery proposal; not authorization",
              "sources": sources, "bindings": bindings, "courses": courses,
              "grants": [], "assessment_assets": [],
              "unresolved_resource_bindings": unresolved,
              "lesson_block_inventory": inventory["lesson_blocks"],
              "assets_pending_crop_and_hash_review": inventory["assets"],
              "source_grant_decisions": [{"user_id": c["user_id"], "exam_id": c["exam_id"],
                                          "permitted_source_ids": None,
                                          "decision": "pending; no blanket grant proposed"} for c in courses],
              "baseline": inventory["baseline"]}
    result["summary"] = {"question_binding_candidates": len(bindings), "source_decisions": len(sources),
                         "repository_original_questions": len(original_ids),
                         "unresolved_resources": dict(Counter(r["resource_kind"] for r in unresolved)),
                         "lesson_blocks": len(inventory["lesson_blocks"]),
                         "asset_reference_groups": len(inventory["assets"]),
                         "account_course_decisions": len(courses), "active_grants": 0}
    return result
