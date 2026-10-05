# Content pipeline

## Why content is separated from code

The application repository can be public, but private study PDFs and extracted proprietary question text must not be committed. The repository stores parsers, schemas and original demo content only. Private imports belong in ignored local storage.

## Pipeline

1. Keep the source PDF outside Git.
2. Extract text and images locally.
3. Run the heuristic parser to create review candidates.
4. Normalize exam, subject, topic, year, shift and source metadata.
5. Validate option positions and answer keys.
6. Compute a fingerprint and reject duplicates.
7. Import with verification status review_required.
8. Review equations, diagrams and doubtful answer keys.
9. Only verified questions can enter normal practice.

## Visual questions

Mirror image, paper folding, dice and figure-series questions must preserve image assets. Parsed text alone is not sufficient.

## Source policy

Every imported item carries source type, source reference, visibility and verification status. Private study sources must remain private. If the product is ever made public, expose only content for which publication is permitted.

## Topic tagging

Phase 2 initially uses deterministic topic tags from the CGL taxonomy. AI-assisted tagging may be added later, but AI cannot silently mark content verified.