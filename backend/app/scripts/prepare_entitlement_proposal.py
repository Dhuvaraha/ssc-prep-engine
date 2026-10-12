"""Prepare a private, non-executable rights/entitlement proposal offline."""
import argparse
import json
from pathlib import Path

from app.services.entitlement_proposal import propose


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--authorship-evidence", type=Path)
    args = parser.parse_args()
    evidence = json.loads(args.authorship_evidence.read_text(encoding="utf-8")) if args.authorship_evidence else {}
    original_ids = [qid for key in ("quant", "reasoning") for qid in evidence.get(key, {}).get("question_ids", [])]
    proposal = propose(json.loads(args.inventory.read_text(encoding="utf-8")), repository_original_ids=original_ids)
    if evidence:
        proposal["authorship_evidence"] = evidence
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(proposal, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps(proposal["summary"]))


if __name__ == "__main__":
    main()
