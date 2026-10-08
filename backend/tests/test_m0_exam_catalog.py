"""M0 safety gates: stage catalog is accurate, immutable and not a fake launch."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.exam_catalog import (
    EXAM_CATALOG,
    get_exam_blueprint,
    is_published_exam,
    list_exam_catalog,
)


def test_exact_catalog_and_only_existing_cgl_stage_is_ready():
    entries = list_exam_catalog()
    assert [item["slug"] for item in entries] == [
        "ssc-cgl-tier-1",
        "ssc-cgl-tier-2",
        "ssc-je-telecom-paper-1",
        "ssc-je-telecom-paper-2",
    ]
    assert [item["status"] for item in entries] == ["ready", "planned", "planned", "planned"]
    assert is_published_exam("ssc-cgl-tier-1")
    for item in entries[1:]:
        assert not is_published_exam(item["slug"])
    assert not is_published_exam("not-real")


@pytest.mark.parametrize(
    ("slug", "total", "minutes", "positive", "negative", "counts"),
    [
        ("ssc-cgl-tier-1", 100, 60, 2.0, 0.5, [25, 25, 25, 25]),
        ("ssc-cgl-tier-2", 160, 135, 3.0, 1.0, [30, 30, 45, 25, 20]),
        ("ssc-je-telecom-paper-1", 200, 120, 1.0, 0.25, [50, 50, 100]),
        ("ssc-je-telecom-paper-2", 100, 120, 3.0, 1.0, [100]),
    ],
)
def test_exam_stage_blueprint_shapes(slug, total, minutes, positive, negative, counts):
    item = get_exam_blueprint(slug)
    assert item is not None
    assert item["total_questions"] == total
    assert item["duration_minutes"] == minutes
    assert item["positive_marks"] == positive
    assert item["negative_marks"] == negative
    assert [section["questions"] for section in item["sections"]] == counts
    assert sum(counts) == total
    assert all(section["kind"] == "mcq" for section in item["sections"])


def test_cgl_tier_two_requires_separate_qualifying_dest_not_fabricated_mcq():
    item = get_exam_blueprint("ssc-cgl-tier-2")
    computer = next(section for section in item["sections"] if section["slug"] == "computer-knowledge")
    assert computer["qualifying"] is True
    assert item["extra_assessments"] == [
        {"slug": "dest", "name": "Data Entry Speed Test", "kind": "typing", "minutes": 15, "qualifying": True}
    ]


def test_je_paper_two_is_technical_only_and_branch_explicit():
    item = get_exam_blueprint("ssc-je-telecom-paper-2")
    assert item["stream"] == "telecom"
    assert len(item["sections"]) == 1
    assert item["sections"][0]["slug"] == "telecom-technical"


def test_catalog_copies_cannot_mutate_server_blueprint():
    items = list_exam_catalog()
    items[0]["sections"][0]["questions"] = 999
    assert get_exam_blueprint("ssc-cgl-tier-1")["sections"][0]["questions"] == 25
    assert EXAM_CATALOG[0]["sections"][0]["questions"] == 25


def test_exam_catalog_http_contract_and_unknown_returns_404():
    client = TestClient(app)
    response = client.get("/api/v1/exams")
    assert response.status_code == 200
    assert len(response.json()) == 4
    stage = client.get("/api/v1/exams/ssc-cgl-tier-1")
    assert stage.status_code == 200
    assert stage.json()["status"] == "ready"
    missing = client.get("/api/v1/exams/not-real")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Exam not found"
