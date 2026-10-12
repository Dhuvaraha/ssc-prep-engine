"""python -m app.phase_a_admin MANIFEST [--apply-reviewed-sha SHA]

Requires an explicitly configured PHASE_A_ADMIN_DATABASE_URL. No default to
production settings, no credentials printed, and dry run is the default.
"""
import argparse
import json
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import normalize_database_url
from app.services.entitlement_admin import apply_manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--apply-reviewed-sha")
    args = parser.parse_args()
    url = os.environ.get("PHASE_A_ADMIN_DATABASE_URL")
    if not url:
        parser.error("Set PHASE_A_ADMIN_DATABASE_URL explicitly; no default database is used")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    engine = create_engine(normalize_database_url(url))
    with Session(engine) as db:
        report = apply_manifest(db, manifest, approved_digest=args.apply_reviewed_sha)
        if args.apply_reviewed_sha:
            db.commit()
        else:
            db.rollback()
        print(json.dumps(report, sort_keys=True))
    engine.dispose()


if __name__ == "__main__":
    main()
