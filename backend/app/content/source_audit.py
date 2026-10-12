"""Read-only PDF evidence inventory; never imports or authenticates questions.

Only explicit source markers are recorded. Candidate choices are never keys.
The report contains no candidate identity, stems, options or answer text.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import re

import fitz

QUESTION_ID = re.compile(r"Question ID\s*:\s*(\d+)", re.I)
EXAM_DATE = re.compile(r"Exam Date\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})", re.I)
EXAM_TIME = re.compile(r"Exam Time\s*:?\s*(\d{1,2}:\d{2}\s*[AP]M\s*-\s*\d{1,2}:\d{2}\s*[AP]M)", re.I)
QUESTION_START = re.compile(r"(?m)^\s*(?:Q\.\s*\d{1,3}|\d{1,3})\.?(?:\s|$)")
PRINTED_KEY = re.compile(r"(?m)^\s*(?:Answer|Correct\s+(?:Answer|Option))\s*:\s*([A-D1-4])\b", re.I)
CHOICE = re.compile(r"Chosen Option\s*:", re.I)


def scan_pdf(path: Path) -> dict:
    fingerprint = sha256(path.read_bytes()).hexdigest()
    pages = []
    source_ids = Counter()
    with fitz.open(path) as document:
        for index, page in enumerate(document):
            text = page.get_text("text")
            ids = QUESTION_ID.findall(text)
            source_ids.update(ids)
            dates = sorted(set(EXAM_DATE.findall(text)))
            times = sorted(set(EXAM_TIME.findall(text)))
            # Page-local evidence only: PDF extraction order can put a header
            # after a preceding question. Never carry a guessed shift forward.
            pages.append({
                "page": index + 1,
                "text_characters": len(text.strip()),
                "image_count": len(page.get_images()),
                "source_question_ids": ids,
                "explicit_exam_dates": dates,
                "explicit_exam_times": times,
                "printed_key_markers": len(PRINTED_KEY.findall(text)),
                "candidate_choice_markers": len(CHOICE.findall(text)),
                "question_start_candidates": len(QUESTION_START.findall(text)),
                "third_party_brand_marker": "cracku.in" in text.casefold(),
                "requires_visual_review": bool(page.get_images()) or len(text.strip()) < 40,
            })
    return {
        "filename": path.name, "sha256": fingerprint, "bytes": path.stat().st_size,
        "page_count": len(pages),
        "pages_without_extractable_text": sum(p["text_characters"] < 40 for p in pages),
        "source_question_id_occurrences": sum(source_ids.values()),
        "distinct_source_question_ids": len(source_ids),
        "repeated_source_question_ids": sum(n > 1 for n in source_ids.values()),
        "printed_key_markers": sum(p["printed_key_markers"] for p in pages),
        "candidate_choice_markers": sum(p["candidate_choice_markers"] for p in pages),
        "explicit_exam_dates": sorted({d for p in pages for d in p["explicit_exam_dates"]}),
        "pages_with_third_party_brand": sum(p["third_party_brand_marker"] for p in pages),
        "authenticity_status": "unverified",
        "answer_verification_status": "pending_independent_review",
        "publication_rights_status": "unreviewed",
        "pages": pages,
    }


def audit_corpus(paths: list[Path], *, previous_report: dict | None = None) -> dict:
    records, duplicates, by_hash = [], [], {}
    if previous_report is not None and previous_report.get("format_version") != 1:
        raise ValueError("Unsupported prior audit format")
    cached = {record["sha256"]: record for record in (previous_report or {}).get("documents", [])}
    reused = 0
    for path in sorted(paths):
        fingerprint = sha256(path.read_bytes()).hexdigest()
        if fingerprint in by_hash:
            duplicates.append({"filename": path.name, "duplicate_of": by_hash[fingerprint], "sha256": fingerprint})
            continue
        if fingerprint in cached:
            result = deepcopy(cached[fingerprint])
            if result["bytes"] != path.stat().st_size:
                raise ValueError("Prior audit byte count disagrees with identical hash")
            result["filename"] = path.name
            reused += 1
        else:
            result = scan_pdf(path)
        by_hash[fingerprint] = path.name
        records.append(result)
    return {
        "format_version": 1, "read_only": True,
        "files_supplied": len(paths), "unique_documents": len(records),
        "reused_document_audits": reused,
        "duplicate_files": duplicates,
        "unique_document_pages": sum(r["page_count"] for r in records),
        "documents": records,
        "limitations": [
            "Metadata and similarity do not authenticate SSC origin or publication rights.",
            "Printed answer markers are unverified evidence; candidate choices are not answer keys.",
            "Page-local date/time is not automatically associated with every question on that page.",
            "Question-start candidates are not a validated question count.",
            "Scanned pages, diagrams, cross-page items and passages require visual/editorial review.",
            "No database content or learner history is modified.",
        ],
    }

