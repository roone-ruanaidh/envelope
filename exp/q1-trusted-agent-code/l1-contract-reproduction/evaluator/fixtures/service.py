"""Evaluator-only lease service fixtures.

Run with::

    python3 -m evaluator.fixtures.service

The independent behavioral reference and each deliberately defective variant share this process
entry point.  ``CT_FIXTURE_MODE`` selects the behavior; see ``FIXTURE_MODES``.
This module intentionally uses only the Python standard library so the fixture
bank cannot silently inherit dependencies from the candidate implementation.
"""

from __future__ import annotations

import json
import os
import secrets
import signal
import sqlite3
import sys
import threading
import time
import uuid
from contextlib import closing, contextmanager
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterator, Mapping, NoReturn
from urllib.parse import unquote, urlsplit


CONTRACT_VERSION = "1.0.0"
MAX_TTL_MS = 60_000
MAX_TIME_MS = 9_223_372_036_854_775_807
MAX_REQUEST_BYTES = 1_048_576
FIXTURE_MODES = frozenset(
    {
        "reference",
        "schema_extra",
        "non_idempotent",
        "racy_idempotency",
        "stale_replay",
        "drip_response",
        "wall_clock_expiry",
        "exclusive_expiry",
        "renewal_from_expiry",
        "stale_authority",
        "double_claim",
        "volatile",
        "abrupt_volatile",
        "persistent_clock",
        "signal_exit",
        "ignore_sigterm",
    }
)


class GracefulShutdown(Exception):
    """Interrupt the main serve loop so SIGTERM can close and exit zero."""


@dataclass(frozen=True)
class Configuration:
    host: str
    port: int
    database_path: Path
    clock_initial_ms: int
    mode: str

    @classmethod
    def from_environment(cls) -> "Configuration":
        host = os.environ.get("CT_HOST", "127.0.0.1")
        try:
            port = int(os.environ.get("CT_PORT", "8000"))
            clock_initial_ms = int(os.environ.get("CT_CLOCK_INITIAL_MS", "0"))
        except ValueError as exc:
            raise SystemExit(f"invalid integer fixture configuration: {exc}") from exc
        if not 0 <= port <= 65_535:
            raise SystemExit("CT_PORT must be between 0 and 65535")
        if not 0 <= clock_initial_ms <= MAX_TIME_MS:
            raise SystemExit(f"CT_CLOCK_INITIAL_MS must be between 0 and {MAX_TIME_MS}")
        database_path = Path(
            os.environ.get("CT_DATABASE_PATH", "/tmp/ct-evaluator-fixture.sqlite3")
        )
        mode = os.environ.get("CT_FIXTURE_MODE", "reference")
        if mode not in FIXTURE_MODES:
            choices = ", ".join(sorted(FIXTURE_MODES))
            raise SystemExit(f"unknown CT_FIXTURE_MODE {mode!r}; expected one of: {choices}")
        return cls(host, port, database_path, clock_initial_ms, mode)


class ApiError(Exception):
    """A contract error that should be returned as the standard error envelope."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def validation_error(message: str) -> NoReturn:
    raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "validation_error", message)


def reject_nonstandard_json_constant(value: str) -> NoReturn:
    raise ValueError(f"nonstandard JSON constant {value}")


def require_object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        validation_error("request body must be a JSON object")
    return value


def require_exact_fields(
    value: Mapping[str, Any], required: set[str], *, context: str = "request body"
) -> None:
    fields = set(value)
    missing = sorted(required - fields)
    extra = sorted(fields - required)
    if missing:
        validation_error(f"{context} is missing required field(s): {', '.join(missing)}")
    if extra:
        validation_error(f"{context} has unknown field(s): {', '.join(extra)}")


def require_string(
    value: Any,
    field: str,
    *,
    nonempty: bool = True,
    max_length: int | None = None,
) -> str:
    if not isinstance(value, str):
        validation_error(f"{field} must be a string")
    if nonempty and not value:
        validation_error(f"{field} must not be empty")
    if max_length is not None and len(value) > max_length:
        validation_error(f"{field} must contain at most {max_length} code points")
    return value


def require_nonnegative_integer(value: Any, field: str) -> int:
    # bool is an int subclass, but is not an integer in the wire contract.
    if type(value) is not int or not 0 <= value <= MAX_TIME_MS:
        validation_error(f"{field} must be an integer between 0 and {MAX_TIME_MS}")
    return value


def require_ttl(value: Any) -> int:
    if type(value) is not int or not 1 <= value <= MAX_TTL_MS:
        validation_error(f"ttl_ms must be an integer between 1 and {MAX_TTL_MS}")
    return value


def normalize_uuid(value: str) -> str:
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError):
        validation_error("job_id must be a valid UUID")
    canonical = str(parsed)
    if canonical != value.lower():
        validation_error("job_id must use canonical UUID textual form")
    return canonical


def require_lease_token(value: Any) -> str:
    return require_string(value, "lease_token", max_length=256)


class PairRendezvous:
    """Pairs concurrent callers without holding a database lock.

    Fault adapters use it to force a check-then-act overlap. The first caller
    waits briefly for a peer that observed the same precondition.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._waiting: dict[str, threading.Event] = {}

    def meet(self, key: str) -> None:
        with self._lock:
            peer = self._waiting.pop(key, None)
            if peer is None:
                event = threading.Event()
                self._waiting[key] = event
                is_first = True
            else:
                event = peer
                is_first = False
        if not is_first:
            event.set()
            return
        event.wait(timeout=0.2)
        with self._lock:
            if self._waiting.get(key) is event:
                del self._waiting[key]


class FixtureStore:
    """SQLite-backed state machine for the reference and mutant fixtures."""

    def __init__(self, config: Configuration) -> None:
        self.config = config
        self._double_claim_rendezvous = PairRendezvous()
        self._idempotency_rendezvous = PairRendezvous()
        self._clean_marker = Path(f"{config.database_path}.clean-shutdown")
        database_existed = config.database_path.exists()
        previous_exit_was_clean = self._clean_marker.exists()
        self._clean_marker.unlink(missing_ok=True)
        self._discard_previous_state = (
            config.mode == "abrupt_volatile" and database_existed and not previous_exit_was_clean
        )
        config.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.config.database_path,
            isolation_level=None,
            timeout=5.0,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    state TEXT NOT NULL CHECK (
                        state IN ('pending', 'leased', 'succeeded', 'failed')
                    ),
                    lease_worker_id TEXT,
                    lease_token TEXT,
                    lease_expires_at_ms INTEGER,
                    lease_wall_deadline_ns INTEGER,
                    result TEXT,
                    failure_code TEXT,
                    failure_message TEXT
                );

                CREATE INDEX IF NOT EXISTS jobs_by_state ON jobs(state);

                CREATE TABLE IF NOT EXISTS lease_history (
                    lease_token TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
                    worker_id TEXT NOT NULL
                );
                """
            )
            if self.config.mode in {"non_idempotent", "racy_idempotency"}:
                connection.execute("DROP INDEX IF EXISTS jobs_idempotency_key")
            else:
                connection.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS jobs_idempotency_key "
                    "ON jobs(idempotency_key)"
                )
            connection.execute(
                "INSERT OR IGNORE INTO metadata(key, value) VALUES('clock_ms', ?)",
                (str(self.config.clock_initial_ms),),
            )
            # The injected clock belongs to a process run, not durable domain
            # state.  A restarted process receives its initial instant again
            # from the evaluator-owned environment.
            if self.config.mode != "persistent_clock":
                connection.execute(
                    "UPDATE metadata SET value = ? WHERE key = 'clock_ms'",
                    (str(self.config.clock_initial_ms),),
                )
            if self.config.mode == "volatile" or self._discard_previous_state:
                # Deliberate durability defects: one loses every restart;
                # the other loses only after an unclean process exit.
                connection.execute("DELETE FROM lease_history")
                connection.execute("DELETE FROM jobs")

    def mark_clean_shutdown(self) -> None:
        if self.config.mode == "abrupt_volatile":
            self._clean_marker.write_text("clean\n", encoding="ascii")

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.execute("COMMIT")
        except BaseException:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    @staticmethod
    def _clock(connection: sqlite3.Connection) -> int:
        row = connection.execute(
            "SELECT value FROM metadata WHERE key = 'clock_ms'"
        ).fetchone()
        if row is None:  # pragma: no cover - guarded by initialization
            raise RuntimeError("clock metadata is missing")
        return int(row["value"])

    def get_clock(self) -> int:
        with closing(self._connect()) as connection:
            return self._clock(connection)

    def set_clock(self, now_ms: int) -> int:
        if type(now_ms) is not int or not 0 <= now_ms <= MAX_TIME_MS:
            validation_error(f"now_ms must be an integer between 0 and {MAX_TIME_MS}")
        with self._transaction() as connection:
            current = self._clock(connection)
            if now_ms < current:
                raise ApiError(
                    HTTPStatus.CONFLICT,
                    "clock_rewind",
                    "the evaluator clock cannot move backwards",
                )
            connection.execute(
                "UPDATE metadata SET value = ? WHERE key = 'clock_ms'",
                (str(now_ms),),
            )
            return now_ms

    def _normalize_expired(
        self, connection: sqlite3.Connection, job_id: str | None = None
    ) -> None:
        if self.config.mode == "wall_clock_expiry":
            parameters: list[Any] = [time.monotonic_ns()]
            job_clause = ""
            if job_id is not None:
                job_clause = " AND job_id = ?"
                parameters.append(job_id)
            connection.execute(
                f"""
                UPDATE jobs
                   SET state = 'pending',
                       lease_worker_id = NULL,
                       lease_token = NULL,
                       lease_expires_at_ms = NULL,
                       lease_wall_deadline_ns = NULL
                 WHERE state = 'leased'
                   AND lease_wall_deadline_ns <= ?
                   {job_clause}
                """,
                parameters,
            )
            return
        now_ms = self._clock(connection)
        comparison = "<" if self.config.mode == "exclusive_expiry" else "<="
        parameters: list[Any] = [now_ms]
        job_clause = ""
        if job_id is not None:
            job_clause = " AND job_id = ?"
            parameters.append(job_id)
        connection.execute(
            f"""
            UPDATE jobs
               SET state = 'pending',
                   lease_worker_id = NULL,
                   lease_token = NULL,
                   lease_expires_at_ms = NULL,
                   lease_wall_deadline_ns = NULL
             WHERE state = 'leased'
               AND lease_expires_at_ms {comparison} ?
               {job_clause}
            """,
            parameters,
        )

    @staticmethod
    def _job_from_row(row: sqlite3.Row) -> dict[str, Any]:
        lease: dict[str, Any] | None = None
        if row["state"] == "leased":
            lease = {
                "worker_id": row["lease_worker_id"],
                "expires_at_ms": row["lease_expires_at_ms"],
            }
        failure: dict[str, str] | None = None
        if row["state"] == "failed":
            failure = {
                "code": row["failure_code"],
                "message": row["failure_message"],
            }
        return {
            "job_id": row["job_id"],
            "idempotency_key": row["idempotency_key"],
            "payload": row["payload"],
            "state": row["state"],
            "lease": lease,
            "result": row["result"],
            "failure": failure,
        }

    @staticmethod
    def _load_job(connection: sqlite3.Connection, job_id: str) -> sqlite3.Row:
        row = connection.execute(
            "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        if row is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "job_not_found", "job was not found")
        return row

    def _insert_job(
        self, connection: sqlite3.Connection, idempotency_key: str, payload: str
    ) -> tuple[int, dict[str, Any]]:
        job_id = str(uuid.uuid4())
        connection.execute(
            "INSERT INTO jobs(job_id, idempotency_key, payload, state) "
            "VALUES (?, ?, ?, 'pending')",
            (job_id, idempotency_key, payload),
        )
        return HTTPStatus.CREATED, self._job_from_row(self._load_job(connection, job_id))

    def _submit_serialized(
        self, idempotency_key: str, payload: str
    ) -> tuple[int, dict[str, Any]]:
        with self._transaction() as connection:
            if self.config.mode != "non_idempotent":
                existing = connection.execute(
                    "SELECT * FROM jobs WHERE idempotency_key = ?",
                    (idempotency_key,),
                ).fetchone()
                if existing is not None:
                    if existing["payload"] != payload:
                        raise ApiError(
                            HTTPStatus.CONFLICT,
                            "idempotency_conflict",
                            "idempotency_key is already associated with a different payload",
                        )
                    # Exact replays return this job's current normalized
                    # representation.  A new submission does not eagerly scan
                    # unrelated jobs.
                    self._normalize_expired(connection, str(existing["job_id"]))
                    replay = self._job_from_row(
                        self._load_job(connection, str(existing["job_id"]))
                    )
                    if self.config.mode == "stale_replay":
                        replay.update(
                            {"state": "pending", "lease": None, "result": None, "failure": None}
                        )
                    return HTTPStatus.OK, replay
            return self._insert_job(connection, idempotency_key, payload)

    def submit(self, idempotency_key: str, payload: str) -> tuple[int, dict[str, Any]]:
        if self.config.mode != "racy_idempotency":
            return self._submit_serialized(idempotency_key, payload)
        with closing(self._connect()) as connection:
            exists = connection.execute(
                "SELECT 1 FROM jobs WHERE idempotency_key = ? LIMIT 1", (idempotency_key,)
            ).fetchone()
        if exists is not None:
            return self._submit_serialized(idempotency_key, payload)
        self._idempotency_rendezvous.meet(idempotency_key)
        with self._transaction() as connection:
            # Deliberate defect: insert after an unlocked eligibility check
            # without rechecking the idempotency key.
            return self._insert_job(connection, idempotency_key, payload)

    def get_job(self, job_id: str) -> dict[str, Any]:
        with self._transaction() as connection:
            self._normalize_expired(connection, job_id)
            return self._job_from_row(self._load_job(connection, job_id))

    def _grant_pending(
        self, connection: sqlite3.Connection, row: sqlite3.Row, worker_id: str, ttl_ms: int
    ) -> dict[str, Any]:
        now_ms = self._clock(connection)
        token = secrets.token_urlsafe(32)
        expires_at_ms = now_ms + ttl_ms
        wall_deadline_ns = (
            time.monotonic_ns() + ttl_ms * 1_000_000
            if self.config.mode == "wall_clock_expiry"
            else None
        )
        connection.execute(
            """
            UPDATE jobs
               SET state = 'leased', lease_worker_id = ?, lease_token = ?,
                   lease_expires_at_ms = ?, lease_wall_deadline_ns = ?,
                   result = NULL, failure_code = NULL, failure_message = NULL
             WHERE job_id = ?
            """,
            (worker_id, token, expires_at_ms, wall_deadline_ns, row["job_id"]),
        )
        connection.execute(
            "INSERT INTO lease_history(lease_token, job_id, worker_id) VALUES (?, ?, ?)",
            (token, row["job_id"], worker_id),
        )
        updated = self._load_job(connection, row["job_id"])
        return {"job": self._job_from_row(updated), "lease_token": token}

    def _peek_pending_job_id(self) -> str | None:
        with self._transaction() as connection:
            self._normalize_expired(connection)
            row = connection.execute(
                """
                SELECT job_id FROM jobs
                 WHERE state = 'pending'
                 LIMIT 1
                """
            ).fetchone()
            return None if row is None else str(row["job_id"])

    def _claim_with_double_claim_defect(
        self, worker_id: str, ttl_ms: int
    ) -> dict[str, Any] | None:
        job_id = self._peek_pending_job_id()
        if job_id is None:
            return None
        self._double_claim_rendezvous.meet(job_id)
        with self._transaction() as connection:
            # Deliberate defect: the earlier eligibility observation is not
            # rechecked after obtaining the write lock.
            row = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
            if row is None or row["state"] in ("succeeded", "failed"):
                return None
            return self._grant_pending(connection, row, worker_id, ttl_ms)

    def claim(self, worker_id: str, ttl_ms: int) -> dict[str, Any] | None:
        if self.config.mode == "double_claim":
            return self._claim_with_double_claim_defect(worker_id, ttl_ms)
        with self._transaction() as connection:
            self._normalize_expired(connection)
            row = connection.execute(
                """
                SELECT * FROM jobs
                 WHERE state = 'pending'
                 LIMIT 1
                """
            ).fetchone()
            if row is None:
                return None
            return self._grant_pending(connection, row, worker_id, ttl_ms)

    def _authorize(
        self, connection: sqlite3.Connection, job_id: str, token: str
    ) -> sqlite3.Row:
        self._normalize_expired(connection, job_id)
        row = self._load_job(connection, job_id)
        if row["state"] != "leased":
            raise ApiError(
                HTTPStatus.CONFLICT,
                "lease_not_current",
                "the supplied lease token is not current",
            )
        if str(row["lease_token"]) == token:
            return row
        if self.config.mode == "stale_authority":
            historic = connection.execute(
                "SELECT worker_id FROM lease_history WHERE job_id = ? AND lease_token = ?",
                (job_id, token),
            ).fetchone()
            if historic is not None:
                # Deliberate defect: restore the stale holder as current.
                connection.execute(
                    "UPDATE jobs SET lease_token = ?, lease_worker_id = ? WHERE job_id = ?",
                    (token, historic["worker_id"], job_id),
                )
                return self._load_job(connection, job_id)
        raise ApiError(
            HTTPStatus.CONFLICT,
            "lease_not_current",
            "the supplied lease token is not current",
        )

    def heartbeat(self, job_id: str, token: str, ttl_ms: int) -> dict[str, Any]:
        with self._transaction() as connection:
            now_ms = self._clock(connection)
            row = self._authorize(connection, job_id, token)
            if self.config.mode == "renewal_from_expiry":
                expires_at_ms = int(row["lease_expires_at_ms"]) + ttl_ms
            else:
                expires_at_ms = now_ms + ttl_ms
            wall_deadline_ns = (
                time.monotonic_ns() + ttl_ms * 1_000_000
                if self.config.mode == "wall_clock_expiry"
                else None
            )
            connection.execute(
                """
                UPDATE jobs
                   SET lease_expires_at_ms = ?, lease_wall_deadline_ns = ?
                 WHERE job_id = ?
                """,
                (expires_at_ms, wall_deadline_ns, job_id),
            )
            updated = self._load_job(connection, job_id)
            return self._job_from_row(updated)

    def complete(self, job_id: str, token: str, result: str) -> dict[str, Any]:
        with self._transaction() as connection:
            self._authorize(connection, job_id, token)
            connection.execute(
                """
                UPDATE jobs
                   SET state = 'succeeded', lease_worker_id = NULL, lease_token = NULL,
                       lease_expires_at_ms = NULL, lease_wall_deadline_ns = NULL, result = ?,
                       failure_code = NULL, failure_message = NULL
                 WHERE job_id = ?
                """,
                (result, job_id),
            )
            return self._job_from_row(self._load_job(connection, job_id))

    def fail(
        self, job_id: str, token: str, failure_code: str, failure_message: str
    ) -> dict[str, Any]:
        with self._transaction() as connection:
            self._authorize(connection, job_id, token)
            connection.execute(
                """
                UPDATE jobs
                   SET state = 'failed', lease_worker_id = NULL, lease_token = NULL,
                       lease_expires_at_ms = NULL, lease_wall_deadline_ns = NULL, result = NULL,
                       failure_code = ?, failure_message = ?
                 WHERE job_id = ?
                """,
                (failure_code, failure_message, job_id),
            )
            return self._job_from_row(self._load_job(connection, job_id))


class FixtureServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], store: FixtureStore) -> None:
        self.store = store
        super().__init__(address, FixtureHandler)


class FixtureHandler(BaseHTTPRequestHandler):
    """Small HTTP adapter around ``FixtureStore``."""

    protocol_version = "HTTP/1.1"
    server: FixtureServer

    def log_message(self, format: str, *args: Any) -> None:
        # The bank controller owns result reporting.  Keep fixture processes
        # quiet unless an uncaught exception reaches the server.
        return

    @property
    def store(self) -> FixtureStore:
        return self.server.store

    def _send_json(self, status: int, body: Mapping[str, Any]) -> None:
        response_body = dict(body)
        if (
            self.store.config.mode == "schema_extra"
            and status < 400
            and urlsplit(self.path).path.startswith("/v1/")
        ):
            response_body["unexpected_fixture_field"] = True
        encoded = json.dumps(
            response_body, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        if (
            self.store.config.mode == "drip_response"
            and status == HTTPStatus.OK
            and urlsplit(self.path).path == "/_evaluator/clock"
        ):
            try:
                for byte in encoded:
                    self.wfile.write(bytes([byte]))
                    self.wfile.flush()
                    time.sleep(0.2)
            except (BrokenPipeError, ConnectionResetError):
                pass
            return
        self.wfile.write(encoded)

    def _send_empty(self, status: int) -> None:
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _send_error(self, error: ApiError) -> None:
        self._send_json(
            error.status,
            {"error": {"code": error.code, "message": error.message}},
        )

    def _read_json(self) -> dict[str, Any]:
        content_type = self.headers.get("Content-Type", "")
        media_type = content_type.split(";", 1)[0].strip().lower()
        if media_type != "application/json":
            self.close_connection = True
            raise ApiError(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                "unsupported_media_type",
                "Content-Type must be application/json",
            )
        raw_length = self.headers.get("Content-Length")
        try:
            length = int(raw_length) if raw_length is not None else 0
        except ValueError as exc:
            self.close_connection = True
            raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_json", "invalid request body") from exc
        if length < 0 or length > MAX_REQUEST_BYTES:
            self.close_connection = True
            raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_json", "invalid request body")
        raw = self.rfile.read(length)
        try:
            decoded = json.loads(
                raw.decode("utf-8"),
                parse_constant=reject_nonstandard_json_constant,
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise ApiError(
                HTTPStatus.BAD_REQUEST, "invalid_json", "request body is not valid JSON"
            ) from exc
        return require_object(decoded)

    @staticmethod
    def _path_parts(raw_path: str) -> list[str]:
        path = urlsplit(raw_path).path
        return [unquote(part) for part in path.split("/") if part]

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        try:
            parts = self._path_parts(self.path)
            if parts == ["healthz"]:
                self._send_json(
                    HTTPStatus.OK,
                    {"status": "ok", "contract_version": CONTRACT_VERSION},
                )
                return
            if parts == ["_evaluator", "clock"]:
                self._send_json(HTTPStatus.OK, {"now_ms": self.store.get_clock()})
                return
            if len(parts) == 3 and parts[:2] == ["v1", "jobs"]:
                job_id = normalize_uuid(parts[2])
                self._send_json(HTTPStatus.OK, self.store.get_job(job_id))
                return
            self._send_empty(HTTPStatus.NOT_FOUND)
        except ApiError as error:
            self._send_error(error)

    def do_PUT(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        try:
            parts = self._path_parts(self.path)
            if parts != ["_evaluator", "clock"]:
                self._send_empty(HTTPStatus.NOT_FOUND)
                return
            body = self._read_json()
            require_exact_fields(body, {"now_ms"})
            now_ms = require_nonnegative_integer(body["now_ms"], "now_ms")
            self._send_json(HTTPStatus.OK, {"now_ms": self.store.set_clock(now_ms)})
        except ApiError as error:
            self._send_error(error)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        try:
            parts = self._path_parts(self.path)
            if parts == ["v1", "jobs"]:
                body = self._read_json()
                require_exact_fields(body, {"idempotency_key", "payload"})
                idempotency_key = require_string(
                    body["idempotency_key"], "idempotency_key", max_length=128
                )
                payload = require_string(
                    body["payload"], "payload", nonempty=False, max_length=65_536
                )
                status, job = self.store.submit(idempotency_key, payload)
                self._send_json(status, job)
                return
            if parts == ["v1", "leases"]:
                body = self._read_json()
                require_exact_fields(body, {"worker_id", "ttl_ms"})
                worker_id = require_string(
                    body["worker_id"], "worker_id", max_length=128
                )
                ttl_ms = require_ttl(body["ttl_ms"])
                grant = self.store.claim(worker_id, ttl_ms)
                if grant is None:
                    self._send_empty(HTTPStatus.NO_CONTENT)
                else:
                    self._send_json(HTTPStatus.OK, grant)
                return
            if len(parts) == 4 and parts[:2] == ["v1", "jobs"]:
                action = parts[3]
                if action == "heartbeat":
                    body = self._read_json()
                    require_exact_fields(body, {"lease_token", "ttl_ms"})
                    token = require_lease_token(body["lease_token"])
                    ttl_ms = require_ttl(body["ttl_ms"])
                    job_id = normalize_uuid(parts[2])
                    self._send_json(
                        HTTPStatus.OK, self.store.heartbeat(job_id, token, ttl_ms)
                    )
                    return
                if action == "complete":
                    body = self._read_json()
                    require_exact_fields(body, {"lease_token", "result"})
                    token = require_lease_token(body["lease_token"])
                    result = require_string(
                        body["result"], "result", nonempty=False, max_length=65_536
                    )
                    job_id = normalize_uuid(parts[2])
                    self._send_json(
                        HTTPStatus.OK, self.store.complete(job_id, token, result)
                    )
                    return
                if action == "fail":
                    body = self._read_json()
                    require_exact_fields(body, {"lease_token", "failure"})
                    token = require_lease_token(body["lease_token"])
                    failure = require_object(body["failure"])
                    require_exact_fields(
                        failure, {"code", "message"}, context="failure"
                    )
                    code = require_string(
                        failure["code"], "failure.code", max_length=64
                    )
                    message = require_string(
                        failure["message"], "failure.message", max_length=4_096
                    )
                    job_id = normalize_uuid(parts[2])
                    self._send_json(
                        HTTPStatus.OK, self.store.fail(job_id, token, code, message)
                    )
                    return
            self._send_empty(HTTPStatus.NOT_FOUND)
        except ApiError as error:
            self._send_error(error)


def run() -> None:
    config = Configuration.from_environment()
    store = FixtureStore(config)
    server = FixtureServer((config.host, config.port), store)
    if config.mode == "ignore_sigterm":
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    elif config.mode != "signal_exit":
        def handle_sigterm(_signum: int, _frame: object) -> None:
            raise GracefulShutdown

        signal.signal(signal.SIGTERM, handle_sigterm)

    clean_shutdown = False
    try:
        server.serve_forever(poll_interval=0.05)
    except (GracefulShutdown, KeyboardInterrupt):
        clean_shutdown = True
    finally:
        server.server_close()
        if clean_shutdown:
            store.mark_clean_shutdown()


if __name__ == "__main__":
    run()
