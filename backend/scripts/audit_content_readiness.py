from __future__ import annotations

import json

from app.db import SessionLocal
from app.services.content_audit import collect_content_audit


def main() -> None:
    db = SessionLocal()
    try:
        report = collect_content_audit(db)
    finally:
        db.close()

    print(json.dumps(report, indent=2, sort_keys=True))
    if report.get("status") != "ready":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
