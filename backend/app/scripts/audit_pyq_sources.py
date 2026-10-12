"""Usage: python -m app.scripts.audit_pyq_sources INPUT_DIR --output PRIVATE_JSON."""
import argparse
import json
from pathlib import Path

from app.content.source_audit import audit_corpus


def main():
    parser = argparse.ArgumentParser(description="Read-only SSC PDF evidence inventory; no DB connection")
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reuse-report", type=Path,
                        help="Reuse prior page metadata for matching SHA-256; scan only new documents")
    args = parser.parse_args()
    paths = sorted(args.input_dir.glob("*.pdf"))
    if not paths:
        parser.error("No PDF files found")
    if args.output.suffix.lower() != ".json" or args.output.resolve() in {p.resolve() for p in paths}:
        parser.error("Output must be a separate JSON file")
    previous = json.loads(args.reuse_report.read_text(encoding="utf-8")) if args.reuse_report else None
    report = audit_corpus(paths, previous_report=previous)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Refuse overwrite so prior evidence is not silently replaced.
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    args.output.chmod(0o600)
    print(json.dumps({k: report[k] for k in ("files_supplied", "unique_documents", "unique_document_pages")}))


if __name__ == "__main__":
    main()

