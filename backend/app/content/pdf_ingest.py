from __future__ import annotations

import json
from pathlib import Path

import fitz

from app.content.answer_key import parse_answer_page
from app.content.candidate_builder import build_review_candidate
from app.content.section_splitter import detect_shift, detect_subject
from app.content.text_parser import parse_text_candidates


VISUAL_MARKERS = (
    "mirror image",
    "paper is folded",
    "when unfolded",
    "figure series",
    "given figure",
    "venn diagram",
    "dice",
    "histogram",
    "pie chart",
    "bar graph",
    "graph",
    "diagram",
)


def page_needs_visual(text: str) -> bool:
    normalized = text.lower()
    return any(marker in normalized for marker in VISUAL_MARKERS)


def ingest_pdf(
    pdf_path: Path,
    *,
    output_json: Path,
    asset_root: Path,
    year: int | None = None,
    source_reference: str | None = None,
    exam_slug: str = "ssc-cgl-tier-1",
) -> dict[str, int]:
    document = fitz.open(pdf_path)
    page_count = document.page_count
    source_reference = source_reference or pdf_path.name
    source_key = pdf_path.stem.replace(" ", "-").lower()
    source_asset_dir = asset_root / source_key
    source_asset_dir.mkdir(parents=True, exist_ok=True)

    pages: list[dict] = []
    subject_slug: str | None = None
    shift_label: str | None = None

    # First pass: preserve page context and collect answer keys.
    answer_maps: dict[str | None, dict[tuple[str, int], int]] = {}
    for page_index in range(page_count):
        page = document.load_page(page_index)
        text = page.get_text("text")
        subject_slug = detect_subject(text, subject_slug)
        shift_label = detect_shift(text, shift_label)
        pages.append(
            {
                "index": page_index,
                "text": text,
                "subject_slug": subject_slug,
                "shift_label": shift_label,
            }
        )
        page_answers = parse_answer_page(text)
        if page_answers:
            answer_maps.setdefault(shift_label, {}).update(page_answers)

    review_items: list[dict] = []
    rendered_pages = 0
    recovered_answers = 0

    # Second pass: parse question candidates and attach answer keys when available.
    for page_info in pages:
        page_index = int(page_info["index"])
        text = str(page_info["text"])
        subject_slug = page_info["subject_slug"]
        shift_label = page_info["shift_label"]

        if not subject_slug:
            continue

        parsed = parse_text_candidates(text)
        if not parsed:
            continue

        visual = page_needs_visual(text)
        private_page_url: str | None = None
        if visual:
            image_name = f"page-{page_index + 1:04d}.png"
            image_path = source_asset_dir / image_name
            page = document.load_page(page_index)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
            pixmap.save(image_path)
            private_page_url = f"private://{source_key}/{image_name}"
            rendered_pages += 1

        shift_answers = answer_maps.get(shift_label, {})
        fallback_answers = answer_maps.get(None, {})

        for candidate in parsed:
            if candidate.correct_option is None:
                recovered = shift_answers.get((subject_slug, candidate.number))
                if recovered is None:
                    recovered = fallback_answers.get((subject_slug, candidate.number))
                if recovered is not None:
                    candidate.correct_option = recovered
                    recovered_answers += 1

            item = build_review_candidate(
                candidate,
                exam_slug=exam_slug,
                subject_slug=subject_slug,
                year=year,
                shift=shift_label,
                source_reference=source_reference,
            )
            item["source_page"] = page_index + 1
            if item["requires_visual_review"]:
                item["question_image_url"] = private_page_url
            review_items.append(item)

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(review_items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    document.close()

    return {
        "pages": page_count,
        "candidates": len(review_items),
        "rendered_pages": rendered_pages,
        "recovered_answers": recovered_answers,
    }
