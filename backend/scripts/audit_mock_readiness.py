import json

from app.db import SessionLocal
from app.services.mock_readiness import collect_mock_readiness


def main() -> None:
    with SessionLocal() as db:
        report = collect_mock_readiness(db)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
