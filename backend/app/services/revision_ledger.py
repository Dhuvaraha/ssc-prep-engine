"""Isolated editorial ledger. Never writes legacy questions or learner attempts.

This local SQLite workspace is deliberately not connected to application routes.
Production rollout requires the separate PostgreSQL migration and delivery adapter.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import json
import sqlite3
from uuid import uuid4


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value):
    return sha256(canonical(value).encode()).hexdigest()


def validate(payload):
    required = {"stem", "options", "answer_option_id", "explanation", "difficulty",
                "topic_id", "taxonomy_version", "provenance", "assets"}
    if set(payload) != required:
        raise ValueError("Revision must contain exactly the versioned content fields")
    for key in ("stem", "explanation", "taxonomy_version"):
        if not isinstance(payload[key], str) or not payload[key].strip():
            raise ValueError(f"Missing {key}")
    if type(payload["difficulty"]) is not int or payload["difficulty"] not in (1, 2, 3):
        raise ValueError("Invalid difficulty")
    if type(payload["topic_id"]) is not int or payload["topic_id"] < 1:
        raise ValueError("Invalid topic")
    options = payload["options"]
    if not isinstance(options, list) or len(options) != 4:
        raise ValueError("Single-answer MCQ requires four options")
    ids, positions, texts = set(), set(), set()
    asset_ids = set()
    if not isinstance(payload["assets"], list) or not isinstance(payload["provenance"], list) or not payload["provenance"]:
        raise ValueError("Explicit provenance and asset inventory required")
    for source in payload["provenance"]:
        if not isinstance(source, str) or not source.strip():
            raise ValueError("Empty provenance reference")
    for asset in payload["assets"]:
        if set(asset) != {"id", "sha256", "alt"} or not all(isinstance(v, str) and v.strip() for v in asset.values()):
            raise ValueError("Versioned assets require identity, hash and accessible alternative")
        if asset["id"] in asset_ids or len(asset["sha256"]) != 64 or any(c not in '0123456789abcdef' for c in asset["sha256"]):
            raise ValueError("Invalid asset identity/hash")
        asset_ids.add(asset["id"])
    for option in options:
        if set(option) != {"id", "position", "text", "asset_id"}:
            raise ValueError("Invalid option fields")
        oid, position, text = option["id"], option["position"], option["text"]
        if not isinstance(oid, str) or not oid.strip() or oid in ids:
            raise ValueError("Option identities must be unique")
        if type(position) is not int or position in positions:
            raise ValueError("Option positions must be unique integers")
        if not isinstance(text, str) or (not text.strip() and not option["asset_id"]):
            raise ValueError("Empty option")
        if option["asset_id"] is not None and option["asset_id"] not in asset_ids:
            raise ValueError("Unversioned option asset")
        normalized = " ".join(text.casefold().split())
        signature = (normalized, option["asset_id"])
        if signature in texts:
            raise ValueError("Duplicate options")
        ids.add(oid); positions.add(position); texts.add(signature)
    if positions != {1, 2, 3, 4} or payload["answer_option_id"] not in ids:
        raise ValueError("Invalid answer or option positions")
    canonical(payload)


class Ledger:
    def __init__(self, path):
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        for row in self.db.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name IN ('revisions','reviews','publications','pins')"):
            if 'WITHOUT ROWID' not in row['sql'].upper():
                self.db.close()
                raise ValueError('Unsupported older ledger schema; preserve it for explicit migration')
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA recursive_triggers=ON")
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS revisions (
            id TEXT PRIMARY KEY, question_id INTEGER NOT NULL, parent_id TEXT REFERENCES revisions(id),
            payload TEXT NOT NULL, content_hash TEXT NOT NULL, answer_version TEXT NOT NULL,
            author TEXT NOT NULL, reason TEXT NOT NULL, capture_kind TEXT NOT NULL, captured_at TEXT NOT NULL) WITHOUT ROWID;
          CREATE TABLE IF NOT EXISTS reviews (
            revision_id TEXT PRIMARY KEY REFERENCES revisions(id), reviewer TEXT NOT NULL,
            evidence TEXT NOT NULL, reviewed_at TEXT NOT NULL) WITHOUT ROWID;
          CREATE TABLE IF NOT EXISTS publications (
            id TEXT PRIMARY KEY, question_id INTEGER NOT NULL, revision_id TEXT NOT NULL REFERENCES revisions(id),
            previous_id TEXT REFERENCES publications(id), actor TEXT NOT NULL, published_at TEXT NOT NULL) WITHOUT ROWID;
          CREATE TABLE IF NOT EXISTS pins (
            attempt_key TEXT NOT NULL, question_id INTEGER NOT NULL, revision_id TEXT REFERENCES revisions(id),
            blueprint TEXT NOT NULL, original_version_unknown INTEGER NOT NULL,
            stored_result TEXT, captured_at TEXT NOT NULL, PRIMARY KEY(attempt_key, question_id)) WITHOUT ROWID;
          CREATE UNIQUE INDEX IF NOT EXISTS publication_successor ON publications(previous_id) WHERE previous_id IS NOT NULL;
          CREATE UNIQUE INDEX IF NOT EXISTS publication_root ON publications(question_id) WHERE previous_id IS NULL;
        """)
        for table in ("revisions", "reviews", "publications", "pins"):
            keys = {'revisions':('id',), 'reviews':('revision_id',), 'publications':('id',), 'pins':('attempt_key','question_id')}[table]
            predicate = ' AND '.join(f'{key}=NEW.{key}' for key in keys)
            self.db.execute(f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_replace BEFORE INSERT ON {table} WHEN EXISTS (SELECT 1 FROM {table} WHERE {predicate}) BEGIN SELECT RAISE(ABORT, 'immutable evidence'); END")
            for operation in ("UPDATE", "DELETE"):
                self.db.execute(f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{operation} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT, 'immutable evidence'); END")
        self.db.execute("""CREATE TRIGGER IF NOT EXISTS immutable_publication_unique_replace
            BEFORE INSERT ON publications WHEN EXISTS (SELECT 1 FROM publications WHERE
              (NEW.previous_id IS NOT NULL AND previous_id=NEW.previous_id) OR
              (NEW.previous_id IS NULL AND previous_id IS NULL AND question_id=NEW.question_id))
            BEGIN SELECT RAISE(ABORT, 'immutable evidence'); END""")

    def close(self):
        self.db.close()

    @contextmanager
    def transaction(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def revision(self, revision_id):
        row = self.db.execute("SELECT * FROM revisions WHERE id=?", (revision_id,)).fetchone()
        if row is None:
            raise ValueError("Unknown revision")
        result = dict(row)
        result["payload"] = json.loads(result["payload"])
        return result

    def head(self, question_id):
        row = self.db.execute("SELECT p.* FROM publications p WHERE question_id=? AND NOT EXISTS (SELECT 1 FROM publications n WHERE n.previous_id=p.id)", (question_id,)).fetchone()
        return dict(row) if row else None

    def candidate(self, question_id, payload, *, author, reason, parent_id=None, legacy_capture=False):
        validate(payload)
        if type(question_id) is not int or question_id < 1 or not author.strip() or not reason.strip():
            raise ValueError("Question identity, author and reason required")
        if parent_id and self.revision(parent_id)["question_id"] != question_id:
            raise ValueError("Parent belongs to another question")
        # Bind key version to stable option identity AND assessed option content.
        answer_version = digest({"answer": payload["answer_option_id"], "options": payload["options"],
                                 "assets": payload["assets"]})
        rid = str(uuid4())
        self.db.execute("INSERT INTO revisions VALUES (?,?,?,?,?,?,?,?,?,?)", (rid, question_id, parent_id,
            canonical(payload), digest(payload), answer_version, author, reason,
            "legacy_capture_at_migration" if legacy_capture else "editorial_candidate", datetime.now(timezone.utc).isoformat()))
        return rid

    def patch(self, revision_id, changes, *, author, reason):
        old = self.revision(revision_id)
        return self.candidate(old["question_id"], {**old["payload"], **changes}, author=author, reason=reason, parent_id=revision_id)

    def review(self, revision_id, *, reviewer, evidence):
        revision = self.revision(revision_id)
        checks = {"answer_verified", "all_options_checked", "instruction_reviewed", "visual_reviewed"}
        if not reviewer.strip() or reviewer == revision["author"]:
            raise ValueError("Independent reviewer required")
        if set(evidence) != checks | {"reference"} or any(evidence[c] is not True for c in checks) or not isinstance(evidence["reference"], str) or not evidence["reference"].strip():
            raise ValueError("Complete independent review evidence required")
        self.db.execute("INSERT INTO reviews VALUES (?,?,?,?)", (revision_id, reviewer, canonical(evidence), datetime.now(timezone.utc).isoformat()))

    def publish(self, revision_id, *, actor, expected_publication_id):
        """Editorial head only: does not publish to learners or confer access."""
        if not actor.strip():
            raise ValueError("Actor required")
        with self.transaction():
            revision = self.revision(revision_id)
            if self.db.execute("SELECT 1 FROM reviews WHERE revision_id=?", (revision_id,)).fetchone() is None:
                raise ValueError("Unreviewed revision")
            head = self.head(revision["question_id"])
            if (head["id"] if head else None) != expected_publication_id:
                raise ValueError("Stale editorial precondition")
            if revision["parent_id"] != (head["revision_id"] if head else None):
                raise ValueError("Candidate must descend from current head")
            pid = str(uuid4())
            self.db.execute("INSERT INTO publications VALUES (?,?,?,?,?,?)", (pid, revision["question_id"], revision_id, expected_publication_id, actor, datetime.now(timezone.utc).isoformat()))
        return pid

    def pin(self, attempt_key, question_id, *, revision_id, blueprint, legacy_result=None, historical=False):
        if not isinstance(attempt_key, str) or not attempt_key.strip():
            raise ValueError("Attempt identity required")
        if type(historical) is not bool or type(question_id) is not int or question_id < 1:
            raise ValueError("Valid question identity and explicit historical flag required")
        if not isinstance(blueprint, dict) or not isinstance(blueprint.get("version"), str) or not blueprint['version'].strip() or not isinstance(blueprint.get("scoring"), dict) or not blueprint['scoring'] or not isinstance(blueprint.get("timing"), dict) or not blueprint['timing']:
            raise ValueError("Versioned blueprint, scoring and timing required")
        with self.transaction():
            if historical:
                if revision_id is not None:
                    raise ValueError("Historical original revision is unknown; do not backfill a current snapshot")
            else:
                revision = self.revision(revision_id)
                if revision["question_id"] != question_id:
                    raise ValueError("Question/revision mismatch")
                head = self.head(question_id)
                if not head or head["revision_id"] != revision_id:
                    raise ValueError("Only the current reviewed editorial head may be newly pinned")
            self.db.execute("INSERT INTO pins VALUES (?,?,?,?,?,?,?)", (attempt_key, question_id, revision_id,
                canonical(blueprint), int(historical), canonical(legacy_result), datetime.now(timezone.utc).isoformat()))

    def history(self, attempt_key, question_id):
        row = self.db.execute("SELECT * FROM pins WHERE attempt_key=? AND question_id=?", (attempt_key, question_id)).fetchone()
        if row is None:
            raise ValueError("Unknown attempt pin")
        result = dict(row)
        result["blueprint"] = json.loads(result["blueprint"])
        result["stored_result"] = json.loads(result["stored_result"])
        result["revision"] = self.revision(result["revision_id"]) if result["revision_id"] else None
        return result
