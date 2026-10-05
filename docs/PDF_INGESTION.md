# Private PDF ingestion

The ingestion pipeline is deliberately local-first because the repository is public and some user-provided study PDFs are not licensed for public redistribution.

## Local workflow

From the backend folder:

```bash
python -m app.scripts.ingest_pdf "/path/to/paper.pdf" \
  --output data/private/review/paper.json \
  --assets data/private/assets \
  --year 2024 \
  --source "Private study PDF"
```

The command:

1. extracts page text with PyMuPDF;
2. detects CGL section headings and shift labels;
3. parses question candidates conservatively;
4. suggests topics using deterministic rules;
5. records source page metadata;
6. renders pages that appear to contain visual questions;
7. writes all derived content under ignored `data/private/` paths.

## Important limitation

PDF layouts can scramble formulas, columns, symbols and figure options. Ingestion therefore never auto-verifies a question. Every candidate remains review-required until checked in the review UI.
