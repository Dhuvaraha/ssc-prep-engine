import argparse
from pathlib import Path

from app.content.pdf_ingest import ingest_pdf


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract a private SSC review package from a PDF")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--assets", type=Path, default=Path("data/private/assets"))
    parser.add_argument("--year", type=int)
    parser.add_argument("--source")
    args = parser.parse_args()

    stats = ingest_pdf(
        args.pdf,
        output_json=args.output,
        asset_root=args.assets,
        year=args.year,
        source_reference=args.source,
    )
    print(
        f"Processed {stats['pages']} pages; "
        f"{stats['candidates']} question candidates; "
        f"{stats['rendered_pages']} visual pages rendered; "
        f"{stats['recovered_answers']} answers recovered."
    )


if __name__ == "__main__":
    main()
