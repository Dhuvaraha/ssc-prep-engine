from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import fitz

from app.content.topic_tagger import suggest_topic

SOLUTION_QUESTION = re.compile(r"(?m)^\s*(\d{1,3})[.)]\s+")
RESPONSE_QUESTION = re.compile(r"(?m)^\s*Q\.\s*(\d{1,3})\s*")
ANSWER_MARKER = re.compile(r"(?im)^\s*(?:Answer\s*:\s*[A-D1-4]|Ans\s*)$")
VISUAL_MARKERS = (
    "figure",
    "diagram",
    "graph",
    "histogram",
    "pie chart",
    "mirror",
    "dice",
    "paper is folded",
    "shown below",
    "given below",
)


def detect_section(text: str, current: str | None) -> str | None:
    lower = text.lower()
    if "general intelligence and reasoning" in lower:
        return "reasoning"
    if re.search(r"(?im)^\s*general awareness\s*$", text):
        return "general-awareness"
    if re.search(r"(?im)^\s*quantitative aptitude\s*$", text):
        return "quant"
    if "english comprehension" in lower or re.search(r"(?im)^\s*english language\s*$", text):
        return "english"
    return current


def section_by_number(filename: str, number: int) -> str | None:
    old_pattern = bool(re.search(r"\b(2010|2014|2015)\b", filename))
    if old_pattern:
        if 1 <= number <= 50:
            return "reasoning"
        if 51 <= number <= 100:
            return "general-awareness"
        if 101 <= number <= 150:
            return "quant"
        if 151 <= number <= 200:
            return "english"
    else:
        if 1 <= number <= 25:
            return "reasoning"
        if 26 <= number <= 50:
            return "general-awareness"
        if 51 <= number <= 75:
            return "quant"
        if 76 <= number <= 100:
            return "english"
    return None


def extract_question_blocks(text: str, response_sheet: bool) -> list[tuple[int, str]]:
    pattern = RESPONSE_QUESTION if response_sheet else SOLUTION_QUESTION
    matches = list(pattern.finditer(text))
    blocks: list[tuple[int, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.end():end].strip()
        if len(block) >= 10:
            blocks.append((int(match.group(1)), block))
    return blocks


def analyse_pdf(path: Path) -> dict:
    document = fitz.open(path)
    filename = path.name
    current_section: str | None = None
    response_sheet = False
    section_counts: Counter[str] = Counter()
    topic_counts: Counter[str] = Counter()
    visual_count = 0
    answer_tagged = 0
    question_count = 0
    pages_with_images = 0

    for page in document:
        text = page.get_text("text") or ""
        if page.get_images(full=True):
            pages_with_images += 1

        if "Question ID :" in text or re.search(r"(?m)^\s*Q\.\s*\d+", text):
            response_sheet = True

        current_section = detect_section(text, current_section)
        blocks = extract_question_blocks(text, response_sheet)

        for number, block in blocks:
            if response_sheet:
                section = current_section
                question_text = re.split(r"(?im)^\s*Ans\s*$", block, maxsplit=1)[0].strip()
            else:
                section = section_by_number(filename, number) or current_section
                answer_match = re.search(r"(?im)^\s*Answer\s*:\s*[A-D1-4]\b", block)
                if answer_match:
                    answer_tagged += 1
                    question_text = block[: answer_match.start()].strip()
                else:
                    question_text = block

            if not section or len(question_text) < 10:
                continue

            question_count += 1
            section_counts[section] += 1
            topic_slug, confidence = suggest_topic(section, question_text)
            topic_counts[f"{section}:{topic_slug or 'unclassified'}"] += 1
            if any(marker in question_text.lower() for marker in VISUAL_MARKERS):
                visual_count += 1

    return {
        "file": filename,
        "pages": len(document),
        "questions_detected": question_count,
        "answer_tagged": answer_tagged,
        "pages_with_images": pages_with_images,
        "visual_question_hints": visual_count,
        "sections": dict(section_counts),
        "topics": dict(topic_counts),
        "response_sheet_format": response_sheet,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyse private SSC CGL PDFs without exporting copyrighted question text."
    )
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("output_json", type=Path)
    args = parser.parse_args()

    pdfs = sorted(args.input_dir.glob("*.pdf"))
    results = [analyse_pdf(path) for path in pdfs]

    subject_totals: Counter[str] = Counter()
    topic_totals: Counter[str] = Counter()
    for result in results:
        subject_totals.update(result["sections"])
        topic_totals.update(result["topics"])

    report = {
        "files_analysed": len(results),
        "questions_detected": sum(item["questions_detected"] for item in results),
        "answer_tagged": sum(item["answer_tagged"] for item in results),
        "visual_question_hints": sum(item["visual_question_hints"] for item in results),
        "subjects": dict(subject_totals),
        "topics": dict(topic_totals.most_common()),
        "files": results,
        "note": (
            "Counts are heuristic trend signals, not official SSC weightage. "
            "Question text is intentionally excluded from the report."
        ),
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Analysed {len(results)} PDFs and wrote {args.output_json}")


if __name__ == "__main__":
    main()
