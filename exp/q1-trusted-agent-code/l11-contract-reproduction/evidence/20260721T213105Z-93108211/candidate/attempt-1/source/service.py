from __future__ import annotations

import json
import os
import re
import secrets
import sqlite3
import threading
import uuid
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Annotated, Literal

import uvicorn
from fastapi import FastAPI, Path, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.types import ASGIApp, Message, Receive, Scope, Send


MAX_INT64 = 9_223_372_036_854_775_807
JOB_ID_PATTERN = r"^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$"

JobState = Literal["pending", "leased", "succeeded", "failed"]
ErrorCode = Literal[
    "validation_error",
    "invalid_json",
    "unsupported_media_type",
    "job_not_found",
    "idempotency_conflict",
    "lease_not_current",
    "clock_rewind",
]

NowMs = Annotated[int, Field(ge=0, le=MAX_INT64)]
TtlMs = Annotated[int, Field(ge=1, le=60_000)]
IdempotencyKey = Annotated[str, Field(min_length=1, max_length=128)]
WorkerId = Annotated[str, Field(min_length=1, max_length=128)]
LeaseToken = Annotated[str, Field(min_length=1, max_length=256)]
Payload = Annotated[str, Field(min_length=0, max_length=65_536)]
Result = Annotated[str, Field(min_length=0, max_length=65_536)]
FailureCode = Annotated[str, Field(min_length=1, max_length=64)]
FailureMessage = Annotated[str, Field(min_length=1, max_length=4_096)]
JobIdPath = Annotated[str, Path(pattern=JOB_ID_PATTERN)]
CanonicalJobId = Annotated[
    str,
    Field(
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    ),
]


class ContractModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class Health(ContractModel):
    status: Literal["ok"]
    contract_version: Literal["1.0.0"]


class Clock(ContractModel):
    now_ms: NowMs


class Failure(ContractModel):
    code: FailureCode
    message: FailureMessage


class LeaseInfo(ContractModel):
    worker_id: WorkerId
    expires_at_ms: NowMs


class Job(ContractModel):
    job_id: CanonicalJobId
    idempotency_key: IdempotencyKey
    payload: Payload
    state: JobState
    lease: LeaseInfo | None
    result: Result | None
    failure: Failure | None


class SubmitJobRequest(ContractModel):
    idempotency_key: IdempotencyKey
    payload: Payload


class AcquireLeaseRequest(ContractModel):
    worker_id: WorkerId
    ttl_ms: TtlMs


class LeaseGrant(ContractModel):
    job: Job
    lease_token: LeaseToken


class HeartbeatRequest(ContractModel):
    lease_token: LeaseToken
    ttl_ms: TtlMs


class CompleteJobRequest(ContractModel):
    lease_token: LeaseToken
    result: Result


class FailJobRequest(ContractModel):
    lease_token: LeaseToken
    failure: Failure


class ErrorDetail(ContractModel):
    code: ErrorCode
    message: Annotated[str, Field(min_length=1, max_length=4_096)]


class ErrorEnvelope(ContractModel):
    error: ErrorDetail


@dataclass(frozen=True)
class StoredJob:
    job_id: str
    idempotency_key: str
    payload: str
    state: JobState
    worker_id: str | None
    lease_token: str | None
    expires_at_ms: int | None
    result: str | None
    failure_code: str | None
    failure_message: str | None


@dataclass(frozen=True)
class Submission:
    created: bool
    job: StoredJob


@dataclass(frozen=True)
class LeaseAcquisition:
    job: StoredJob
    lease_token: str


OperationStatus = Literal["not_found", "not_current", "updated"]


@dataclass(frozen=True)
class OperationOutcome:
    status: OperationStatus
    job: StoredJob | None


@dataclass(frozen=True)
class PublicOperationOutcome:
    status: OperationStatus
    job: Job | None


@dataclass(frozen=True)
class RuntimeConfig:
    host: str
    port: int
    database_path: str
    clock_initial_ms: int


class LogicalClock:
    def __init__(self, initial_ms: int) -> None:
        self._lock = threading.Lock()
        self._now_ms = initial_ms

    def now_ms(self) -> int:
        with self._lock:
            return self._now_ms

    def set_ms(self, requested_ms: int) -> tuple[bool, int]:
        with self._lock:
            if requested_ms < self._now_ms:
                return False, self._now_ms
            self._now_ms = requested_ms
            return True, self._now_ms


class Database:
    def __init__(self, path: str) -> None:
        self._path = path

    def initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    payload TEXT NOT NULL,
                    state TEXT NOT NULL,
                    worker_id TEXT,
                    lease_token TEXT,
                    expires_at_ms INTEGER,
                    result TEXT,
                    failure_code TEXT,
                    failure_message TEXT
                );
                CREATE TABLE IF NOT EXISTS lease_tokens (
                    lease_token TEXT PRIMARY KEY NOT NULL
                );
                CREATE INDEX IF NOT EXISTS jobs_lease_eligibility
                    ON jobs(state, expires_at_ms);
                """
            )
            connection.commit()

    def submit(self, idempotency_key: str, payload: str) -> Submission:
        with self._write_transaction() as connection:
            existing = self._select_by_idempotency_key(connection, idempotency_key)
            if existing is not None:
                if existing.payload != payload:
                    raise IdempotencyConflict
                return Submission(created=False, job=existing)

            job_id = self._new_job_id(connection)
            connection.execute(
                """
                INSERT INTO jobs (
                    job_id, idempotency_key, payload, state, worker_id,
                    lease_token, expires_at_ms, result, failure_code, failure_message
                ) VALUES (?, ?, ?, 'pending', NULL, NULL, NULL, NULL, NULL, NULL)
                """,
                (job_id, idempotency_key, payload),
            )
            created = self._select_by_job_id(connection, job_id)
            if created is None:
                raise DatabaseInvariantError("inserted job was not readable")
            return Submission(created=True, job=created)

    def get_job(self, job_id: str) -> StoredJob | None:
        with self._connection() as connection:
            return self._select_by_job_id(connection, job_id)

    def acquire(
        self,
        worker_id: str,
        ttl_ms: int,
        now_ms: int,
    ) -> LeaseAcquisition | None:
        expires_at_ms = now_ms + ttl_ms
        with self._write_transaction() as connection:
            eligible = connection.execute(
                """
                SELECT
                    job_id, idempotency_key, payload, state, worker_id,
                    lease_token, expires_at_ms, result, failure_code, failure_message
                FROM jobs
                WHERE state = 'pending'
                   OR (state = 'leased' AND expires_at_ms IS NOT NULL AND expires_at_ms <= ?)
                LIMIT 1
                """,
                (now_ms,),
            ).fetchone()
            current = self._decode_optional_row(eligible)
            if current is None:
                return None

            lease_token = self._new_lease_token(connection)
            updated = connection.execute(
                """
                UPDATE jobs
                SET state = 'leased', worker_id = ?, lease_token = ?,
                    expires_at_ms = ?, result = NULL, failure_code = NULL,
                    failure_message = NULL
                WHERE job_id = ?
                """,
                (worker_id, lease_token, expires_at_ms, current.job_id),
            )
            if updated.rowcount != 1:
                raise DatabaseInvariantError("lease update affected the wrong number of jobs")

            leased = self._select_by_job_id(connection, current.job_id)
            if leased is None:
                raise DatabaseInvariantError("leased job was not readable")
            return LeaseAcquisition(job=leased, lease_token=lease_token)

    def heartbeat(
        self,
        job_id: str,
        lease_token: str,
        ttl_ms: int,
        now_ms: int,
    ) -> OperationOutcome:
        expires_at_ms = now_ms + ttl_ms
        with self._write_transaction() as connection:
            current = self._select_by_job_id(connection, job_id)
            if current is None:
                return OperationOutcome(status="not_found", job=None)
            if not self._is_current_lease(current, lease_token, now_ms):
                return OperationOutcome(status="not_current", job=None)

            connection.execute(
                "UPDATE jobs SET expires_at_ms = ? WHERE job_id = ?",
                (expires_at_ms, job_id),
            )
            renewed = self._select_by_job_id(connection, job_id)
            if renewed is None:
                raise DatabaseInvariantError("renewed job was not readable")
            return OperationOutcome(status="updated", job=renewed)

    def complete(
        self,
        job_id: str,
        lease_token: str,
        result: str,
        now_ms: int,
    ) -> OperationOutcome:
        with self._write_transaction() as connection:
            current = self._select_by_job_id(connection, job_id)
            if current is None:
                return OperationOutcome(status="not_found", job=None)
            if not self._is_current_lease(current, lease_token, now_ms):
                return OperationOutcome(status="not_current", job=None)

            connection.execute(
                """
                UPDATE jobs
                SET state = 'succeeded', worker_id = NULL, lease_token = NULL,
                    expires_at_ms = NULL, result = ?, failure_code = NULL,
                    failure_message = NULL
                WHERE job_id = ?
                """,
                (result, job_id),
            )
            completed = self._select_by_job_id(connection, job_id)
            if completed is None:
                raise DatabaseInvariantError("completed job was not readable")
            return OperationOutcome(status="updated", job=completed)

    def fail(
        self,
        job_id: str,
        lease_token: str,
        failure_code: str,
        failure_message: str,
        now_ms: int,
    ) -> OperationOutcome:
        with self._write_transaction() as connection:
            current = self._select_by_job_id(connection, job_id)
            if current is None:
                return OperationOutcome(status="not_found", job=None)
            if not self._is_current_lease(current, lease_token, now_ms):
                return OperationOutcome(status="not_current", job=None)

            connection.execute(
                """
                UPDATE jobs
                SET state = 'failed', worker_id = NULL, lease_token = NULL,
                    expires_at_ms = NULL, result = NULL, failure_code = ?,
                    failure_message = ?
                WHERE job_id = ?
                """,
                (failure_code, failure_message, job_id),
            )
            failed = self._select_by_job_id(connection, job_id)
            if failed is None:
                raise DatabaseInvariantError("failed job was not readable")
            return OperationOutcome(status="updated", job=failed)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._path, timeout=3.0)
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def _write_transaction(self) -> Iterator[sqlite3.Connection]:
        with self._connection() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                yield connection
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    def _select_by_job_id(
        self,
        connection: sqlite3.Connection,
        job_id: str,
    ) -> StoredJob | None:
        row = connection.execute(
            """
            SELECT
                job_id, idempotency_key, payload, state, worker_id,
                lease_token, expires_at_ms, result, failure_code, failure_message
            FROM jobs
            WHERE job_id = ?
            """,
            (job_id,),
        ).fetchone()
        return self._decode_optional_row(row)

    def _select_by_idempotency_key(
        self,
        connection: sqlite3.Connection,
        idempotency_key: str,
    ) -> StoredJob | None:
        row = connection.execute(
            """
            SELECT
                job_id, idempotency_key, payload, state, worker_id,
                lease_token, expires_at_ms, result, failure_code, failure_message
            FROM jobs
            WHERE idempotency_key = ?
            """,
            (idempotency_key,),
        ).fetchone()
        return self._decode_optional_row(row)

    def _new_job_id(self, connection: sqlite3.Connection) -> str:
        while True:
            job_id = str(uuid.uuid4())
            existing = connection.execute(
                "SELECT 1 FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if existing is None:
                return job_id

    def _new_lease_token(self, connection: sqlite3.Connection) -> str:
        while True:
            lease_token = secrets.token_urlsafe(32)
            try:
                connection.execute(
                    "INSERT INTO lease_tokens (lease_token) VALUES (?)",
                    (lease_token,),
                )
                return lease_token
            except sqlite3.IntegrityError:
                continue

    @staticmethod
    def _is_current_lease(job: StoredJob, lease_token: str, now_ms: int) -> bool:
        return (
            job.state == "leased"
            and job.lease_token == lease_token
            and job.expires_at_ms is not None
            and now_ms < job.expires_at_ms
        )

    @staticmethod
    def _decode_optional_row(row: object) -> StoredJob | None:
        if row is None:
            return None
        return Database._decode_row(row)

    @staticmethod
    def _decode_row(row: object) -> StoredJob:
        if not isinstance(row, tuple) or len(row) != 10:
            raise DatabaseInvariantError("unexpected SQLite row shape")
        values: tuple[object, ...] = tuple(row)

        job_id = Database._required_string(values[0], "job_id")
        idempotency_key = Database._required_string(values[1], "idempotency_key")
        payload = Database._required_string(values[2], "payload")
        raw_state = Database._required_string(values[3], "state")
        state = Database._decode_state(raw_state)
        worker_id = Database._optional_string(values[4], "worker_id")
        lease_token = Database._optional_string(values[5], "lease_token")
        expires_at_ms = Database._optional_int(values[6], "expires_at_ms")
        result = Database._optional_string(values[7], "result")
        failure_code = Database._optional_string(values[8], "failure_code")
        failure_message = Database._optional_string(values[9], "failure_message")

        return StoredJob(
            job_id=job_id,
            idempotency_key=idempotency_key,
            payload=payload,
            state=state,
            worker_id=worker_id,
            lease_token=lease_token,
            expires_at_ms=expires_at_ms,
            result=result,
            failure_code=failure_code,
            failure_message=failure_message,
        )

    @staticmethod
    def _decode_state(raw_state: str) -> JobState:
        if raw_state == "pending":
            return "pending"
        if raw_state == "leased":
            return "leased"
        if raw_state == "succeeded":
            return "succeeded"
        if raw_state == "failed":
            return "failed"
        raise DatabaseInvariantError("unexpected job state")

    @staticmethod
    def _required_string(value: object, name: str) -> str:
        if not isinstance(value, str):
            raise DatabaseInvariantError(f"SQLite column {name} was not text")
        return value

    @staticmethod
    def _optional_string(value: object, name: str) -> str | None:
        if value is None:
            return None
        return Database._required_string(value, name)

    @staticmethod
    def _optional_int(value: object, name: str) -> int | None:
        if value is None:
            return None
        if not isinstance(value, int) or isinstance(value, bool):
            raise DatabaseInvariantError(f"SQLite column {name} was not an integer")
        return value


class DatabaseInvariantError(RuntimeError):
    pass


class IdempotencyConflict(RuntimeError):
    pass


class LeaseJobService:
    def __init__(self, database: Database, clock: LogicalClock) -> None:
        self._database = database
        self._clock = clock

    def initialize(self) -> None:
        self._database.initialize()

    def get_clock(self) -> Clock:
        return Clock(now_ms=self._clock.now_ms())

    def set_clock(self, requested_ms: int) -> tuple[bool, Clock]:
        accepted, current_ms = self._clock.set_ms(requested_ms)
        return accepted, Clock(now_ms=current_ms)

    def submit(self, request: SubmitJobRequest) -> tuple[int, Job]:
        now_ms = self._clock.now_ms()
        try:
            submission = self._database.submit(request.idempotency_key, request.payload)
        except IdempotencyConflict:
            raise
        status_code = 201 if submission.created else 200
        return status_code, self._public_job(submission.job, now_ms)

    def get_job(self, job_id: str) -> Job | None:
        now_ms = self._clock.now_ms()
        stored_job = self._database.get_job(job_id)
        if stored_job is None:
            return None
        return self._public_job(stored_job, now_ms)

    def acquire(self, request: AcquireLeaseRequest) -> LeaseGrant | None:
        now_ms = self._clock.now_ms()
        acquisition = self._database.acquire(request.worker_id, request.ttl_ms, now_ms)
        if acquisition is None:
            return None
        return LeaseGrant(
            job=self._public_job(acquisition.job, now_ms),
            lease_token=acquisition.lease_token,
        )

    def heartbeat(
        self,
        job_id: str,
        request: HeartbeatRequest,
    ) -> PublicOperationOutcome:
        now_ms = self._clock.now_ms()
        outcome = self._database.heartbeat(
            job_id,
            request.lease_token,
            request.ttl_ms,
            now_ms,
        )
        return self._public_outcome(outcome, now_ms)

    def complete(
        self,
        job_id: str,
        request: CompleteJobRequest,
    ) -> PublicOperationOutcome:
        now_ms = self._clock.now_ms()
        outcome = self._database.complete(
            job_id,
            request.lease_token,
            request.result,
            now_ms,
        )
        return self._public_outcome(outcome, now_ms)

    def fail(
        self,
        job_id: str,
        request: FailJobRequest,
    ) -> PublicOperationOutcome:
        now_ms = self._clock.now_ms()
        outcome = self._database.fail(
            job_id,
            request.lease_token,
            request.failure.code,
            request.failure.message,
            now_ms,
        )
        return self._public_outcome(outcome, now_ms)

    @staticmethod
    def _public_outcome(
        outcome: OperationOutcome,
        now_ms: int,
    ) -> PublicOperationOutcome:
        if outcome.job is None:
            return PublicOperationOutcome(status=outcome.status, job=None)
        return PublicOperationOutcome(
            status=outcome.status,
            job=LeaseJobService._public_job(outcome.job, now_ms),
        )

    @staticmethod
    def _public_job(stored_job: StoredJob, now_ms: int) -> Job:
        if stored_job.state == "pending":
            return Job(
                job_id=stored_job.job_id,
                idempotency_key=stored_job.idempotency_key,
                payload=stored_job.payload,
                state="pending",
                lease=None,
                result=None,
                failure=None,
            )

        if stored_job.state == "leased":
            if (
                stored_job.worker_id is None
                or stored_job.expires_at_ms is None
                or stored_job.lease_token is None
            ):
                raise DatabaseInvariantError("leased job is missing lease fields")
            if now_ms >= stored_job.expires_at_ms:
                return Job(
                    job_id=stored_job.job_id,
                    idempotency_key=stored_job.idempotency_key,
                    payload=stored_job.payload,
                    state="pending",
                    lease=None,
                    result=None,
                    failure=None,
                )
            return Job(
                job_id=stored_job.job_id,
                idempotency_key=stored_job.idempotency_key,
                payload=stored_job.payload,
                state="leased",
                lease=LeaseInfo(
                    worker_id=stored_job.worker_id,
                    expires_at_ms=stored_job.expires_at_ms,
                ),
                result=None,
                failure=None,
            )

        if stored_job.state == "succeeded":
            if stored_job.result is None:
                raise DatabaseInvariantError("succeeded job is missing result")
            return Job(
                job_id=stored_job.job_id,
                idempotency_key=stored_job.idempotency_key,
                payload=stored_job.payload,
                state="succeeded",
                lease=None,
                result=stored_job.result,
                failure=None,
            )

        if stored_job.failure_code is None or stored_job.failure_message is None:
            raise DatabaseInvariantError("failed job is missing failure fields")
        return Job(
            job_id=stored_job.job_id,
            idempotency_key=stored_job.idempotency_key,
            payload=stored_job.payload,
            state="failed",
            lease=None,
            result=None,
            failure=Failure(
                code=stored_job.failure_code,
                message=stored_job.failure_message,
            ),
        )


def _error_response(status_code: int, code: ErrorCode, message: str) -> JSONResponse:
    envelope = ErrorEnvelope(error=ErrorDetail(code=code, message=message))
    return JSONResponse(status_code=status_code, content=envelope.model_dump(mode="json"))


def _needs_json_body(request: Request) -> bool:
    path = request.url.path
    if request.method == "PUT" and path == "/_evaluator/clock":
        return True
    if request.method != "POST":
        return False
    if path in {"/v1/jobs", "/v1/leases"}:
        return True
    return re.fullmatch(r"/v1/jobs/[^/]+/(heartbeat|complete|fail)", path) is not None


def _reject_nonstandard_json_constant(_value: str) -> object:
    raise ValueError("non-standard JSON constant")


def _has_valid_json_syntax(body: bytes) -> bool:
    try:
        parsed: object = json.loads(
            body,
            parse_constant=_reject_nonstandard_json_constant,
        )
    except (ValueError, UnicodeDecodeError):
        return False
    return parsed is not None or body != b""


def _has_json_error(exception: RequestValidationError) -> bool:
    for detail in exception.errors():
        if isinstance(detail, Mapping):
            error_type: object = detail.get("type")
            if error_type == "json_invalid":
                return True
    return False


class JsonRequestMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        scope_type: object = scope.get("type")
        if scope_type != "http":
            await self._app(scope, receive, send)
            return

        request = Request(scope, receive)
        if not _needs_json_body(request):
            await self._app(scope, receive, send)
            return

        content_type = request.headers.get("content-type")
        media_type = "" if content_type is None else content_type.split(";", 1)[0].strip()
        if media_type.lower() != "application/json":
            response = _error_response(
                415,
                "unsupported_media_type",
                "request content type must be application/json",
            )
            await response(scope, receive, send)
            return

        body = await self._read_body(receive)
        if body is None or not _has_valid_json_syntax(body):
            response = _error_response(
                400,
                "invalid_json",
                "request body is not valid JSON",
            )
            await response(scope, receive, send)
            return

        replayed = False

        async def replay_receive() -> Message:
            nonlocal replayed
            if not replayed:
                replayed = True
                return {
                    "type": "http.request",
                    "body": body,
                    "more_body": False,
                }
            return await receive()

        await self._app(scope, replay_receive, send)

    @staticmethod
    async def _read_body(receive: Receive) -> bytes | None:
        chunks: list[bytes] = []
        while True:
            message = await receive()
            message_type: object = message.get("type")
            if message_type == "http.disconnect":
                return None
            if message_type != "http.request":
                return None
            raw_body: object = message.get("body", b"")
            if not isinstance(raw_body, bytes):
                return None
            chunks.append(raw_body)
            more_body: object = message.get("more_body", False)
            if not isinstance(more_body, bool):
                return None
            if not more_body:
                return b"".join(chunks)


def _canonical_job_id(job_id: str) -> str:
    return str(uuid.UUID(job_id))


def create_app(service: LeaseJobService) -> FastAPI:
    app = FastAPI(title="Q1/L1 Lease Job Service", version="1.0.0")

    @app.on_event("startup")
    def initialize_database() -> None:
        service.initialize()

    app.add_middleware(JsonRequestMiddleware)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request,
        exception: RequestValidationError,
    ) -> JSONResponse:
        if _has_json_error(exception):
            return _error_response(
                400,
                "invalid_json",
                "request body is not valid JSON",
            )
        return _error_response(
            422,
            "validation_error",
            "request does not conform to the declared schema",
        )

    @app.get("/healthz", response_model=Health)
    async def healthz() -> Health:
        return Health(status="ok", contract_version="1.0.0")

    @app.get("/_evaluator/clock", response_model=Clock)
    async def get_clock() -> Clock:
        return service.get_clock()

    @app.put("/_evaluator/clock", response_model=Clock)
    async def set_clock(clock: Clock) -> Clock | JSONResponse:
        accepted, current = service.set_clock(clock.now_ms)
        if not accepted:
            return _error_response(
                409,
                "clock_rewind",
                "logical clock cannot move backwards",
            )
        return current

    @app.post("/v1/jobs", response_model=Job, status_code=201)
    async def submit_job(
        request: SubmitJobRequest,
        response: Response,
    ) -> Job | JSONResponse:
        try:
            status_code, job = service.submit(request)
        except IdempotencyConflict:
            return _error_response(
                409,
                "idempotency_conflict",
                "idempotency key is already associated with another payload",
            )
        response.status_code = status_code
        return job

    @app.get("/v1/jobs/{job_id}", response_model=Job)
    async def get_job(job_id: JobIdPath) -> Job | JSONResponse:
        job = service.get_job(_canonical_job_id(job_id))
        if job is None:
            return _error_response(404, "job_not_found", "job was not found")
        return job

    @app.post("/v1/leases", response_model=LeaseGrant)
    async def acquire_lease(
        request: AcquireLeaseRequest,
    ) -> LeaseGrant | Response:
        lease = service.acquire(request)
        if lease is None:
            return Response(status_code=204)
        return lease

    @app.post("/v1/jobs/{job_id}/heartbeat", response_model=Job)
    async def heartbeat_lease(
        job_id: JobIdPath,
        request: HeartbeatRequest,
    ) -> Job | JSONResponse:
        outcome = service.heartbeat(_canonical_job_id(job_id), request)
        if outcome.status == "not_found":
            return _error_response(404, "job_not_found", "job was not found")
        if outcome.status == "not_current" or outcome.job is None:
            return _error_response(409, "lease_not_current", "lease token is not current")
        return outcome.job

    @app.post("/v1/jobs/{job_id}/complete", response_model=Job)
    async def complete_job(
        job_id: JobIdPath,
        request: CompleteJobRequest,
    ) -> Job | JSONResponse:
        outcome = service.complete(_canonical_job_id(job_id), request)
        if outcome.status == "not_found":
            return _error_response(404, "job_not_found", "job was not found")
        if outcome.status == "not_current" or outcome.job is None:
            return _error_response(409, "lease_not_current", "lease token is not current")
        return outcome.job

    @app.post("/v1/jobs/{job_id}/fail", response_model=Job)
    async def fail_job(
        job_id: JobIdPath,
        request: FailJobRequest,
    ) -> Job | JSONResponse:
        outcome = service.fail(_canonical_job_id(job_id), request)
        if outcome.status == "not_found":
            return _error_response(404, "job_not_found", "job was not found")
        if outcome.status == "not_current" or outcome.job is None:
            return _error_response(409, "lease_not_current", "lease token is not current")
        return outcome.job

    return app


def _read_decimal_environment(name: str, minimum: int, maximum: int) -> int:
    value = os.environ.get(name)
    if value is None or re.fullmatch(r"[0-9]+", value) is None:
        raise RuntimeError(f"{name} must be a decimal integer")
    parsed = int(value)
    if parsed < minimum or parsed > maximum:
        raise RuntimeError(f"{name} is outside its permitted range")
    return parsed


def _read_runtime_config() -> RuntimeConfig:
    host = os.environ.get("Q1_L1_HOST")
    if host is None or host == "":
        raise RuntimeError("Q1_L1_HOST is required")
    database_path = os.environ.get("Q1_L1_DATABASE_PATH")
    if database_path is None or not os.path.isabs(database_path):
        raise RuntimeError("Q1_L1_DATABASE_PATH must be an absolute path")
    return RuntimeConfig(
        host=host,
        port=_read_decimal_environment("Q1_L1_PORT", 1, 65_535),
        database_path=database_path,
        clock_initial_ms=_read_decimal_environment(
            "Q1_L1_CLOCK_INITIAL_MS",
            0,
            MAX_INT64,
        ),
    )


def main() -> None:
    config = _read_runtime_config()
    service = LeaseJobService(
        database=Database(config.database_path),
        clock=LogicalClock(config.clock_initial_ms),
    )
    app = create_app(service)
    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        timeout_graceful_shutdown=1,
    )


if __name__ == "__main__":
    main()
