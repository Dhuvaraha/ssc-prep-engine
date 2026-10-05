# Topic tagging

Phase 2 uses deterministic tagging rules as a first pass. The rules are intentionally conservative: a tag suggestion is never equivalent to verification.

The initial rules reflect recurring question families visible across the user's SSC CGL paper bank, including reasoning series/coding/dictionary/mirror/paper-folding/dice/sign-operations, quant work/speed/percentage/DI, English error spotting/vocabulary/voice/narration/jumbles, and broad GA domains.

## Flow

1. Parse candidate.
2. Assign subject from paper section.
3. Run deterministic topic suggestion.
4. Display suggestion and confidence in the review screen.
5. Human review may accept/change the topic.
6. Mark question verified only after text, options, answer and visuals are checked.

This avoids silently misclassifying damaged PDF text or image-heavy questions.
