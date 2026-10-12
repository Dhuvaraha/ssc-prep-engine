import json

import fitz

from app.content.source_audit import audit_corpus, scan_pdf


def make_pdf(path, texts):
    with fitz.open() as document:
        for text in texts:
            page = document.new_page()
            page.insert_text((30, 30), text)
        document.save(path)


def test_inventory_never_promotes_candidate_choices_or_carries_shift(tmp_path):
    pdf = tmp_path / "synthetic.pdf"
    make_pdf(pdf, [
        "Exam Date 25/09/2024\nExam Time 4:00 PM - 5:00 PM\n"
        "Candidate Name PRIVATE_NAME\nQ.1 Secret stem\nQuestion ID : 12345\nChosen Option : 3",
        "Question ID : 54321\nAnswer: B",
        "",
    ])
    before = pdf.read_bytes()
    report = scan_pdf(pdf)
    assert pdf.read_bytes() == before
    assert report["page_count"] == 3
    assert report["candidate_choice_markers"] == 1
    assert report["printed_key_markers"] == 1
    assert report["pages"][1]["explicit_exam_dates"] == []
    assert report["pages"][0]["explicit_exam_times"] == ["4:00 PM - 5:00 PM"]
    assert report["pages_without_extractable_text"] == 2  # short text needs review
    assert report["publication_rights_status"] == "unreviewed"
    assert report["authenticity_status"] == "unverified"
    serialized = json.dumps(report)
    for private in ("PRIVATE_NAME", "Secret stem", "Chosen Option", '"correct_option"'):
        assert private not in serialized


def test_exact_file_duplicates_not_counted_as_new_papers(tmp_path):
    first, copy = tmp_path / "first.pdf", tmp_path / "copy.pdf"
    make_pdf(first, ["Question ID : 12345\nQuestion ID : 12345"])
    copy.write_bytes(first.read_bytes())
    report = audit_corpus([first, copy])
    assert report["files_supplied"] == 2
    assert report["unique_documents"] == 1
    assert report["unique_document_pages"] == 1
    assert len(report["duplicate_files"]) == 1
    assert report["documents"][0]["repeated_source_question_ids"] == 1


def test_prior_hash_audit_reused_without_page_extraction(tmp_path, monkeypatch):
    from app.content import source_audit
    original, renamed = tmp_path / "original.pdf", tmp_path / "renamed.pdf"
    make_pdf(original, ["Question ID : 12345"])
    prior = audit_corpus([original])
    renamed.write_bytes(original.read_bytes())
    def must_not_scan(path):
        raise AssertionError("Identical bytes must reuse the prior extraction")
    monkeypatch.setattr(source_audit, "scan_pdf", must_not_scan)
    report = audit_corpus([renamed], previous_report=prior)
    assert report["reused_document_audits"] == 1
    assert report["documents"][0]["filename"] == "renamed.pdf"
    assert prior["documents"][0]["filename"] == "original.pdf"


def test_new_hash_is_extracted_even_when_filename_matches_prior(tmp_path):
    path = tmp_path / "paper.pdf"
    make_pdf(path, ["Question ID : 1"])
    prior = audit_corpus([path])
    path.unlink()
    make_pdf(path, ["Question ID : 2", "Question ID : 3"])
    current = audit_corpus([path], previous_report=prior)
    assert current["reused_document_audits"] == 0
    assert current["unique_document_pages"] == 2

