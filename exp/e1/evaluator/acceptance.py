"""Executable black-box acceptance suite for the Experiment 1 service.

The service is treated only as an HTTP endpoint plus the documented foreground
process protocol.  No candidate module, database, or implementation detail is
imported or inspected.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Barrier
from typing import Any, Callable, Sequence, cast
from uuid import uuid4

from . import CONTRACT_VERSION, EVALUATOR_VERSION
from .controller import ControllerFailure, ServiceController
from .http import HTTPClient, Response
from .schema import assert_contract_alignment


CLOCK_INITIAL_MS = 1_700_000_000_000
DEFAULT_REQUEST_TIMEOUT_SECONDS = 3.0
DEFAULT_STARTUP_TIMEOUT_SECONDS = 8.0
DEFAULT_SHUTDOWN_TIMEOUT_SECONDS = 1.5
DEFAULT_SUITE_TIMEOUT_SECONDS = 45.0


class AcceptanceFailure(AssertionError):
    """A declared service behavior was not observed."""


@dataclass(frozen=True)
class TestCase:
    name: str
    layer: str
    method_name: str


@dataclass
class TestResult:
    name: str
    layer: str
    passed: bool
    duration_ms: int
    detail: str | None = None


TEST_CASES: tuple[TestCase, ...] = (
    TestCase("protocol_and_schema", "protocol", "test_protocol_and_schema"),
    TestCase("sequential_transitions", "state_model", "test_sequential_transitions"),
    TestCase("idempotent_submission", "idempotency", "test_idempotent_submission"),
    TestCase("concurrent_idempotent_replay", "idempotency", "test_concurrent_idempotent_replay"),
    TestCase("frozen_clock_and_ttl_boundary", "temporal", "test_frozen_clock_and_ttl_boundary"),
    TestCase("renewal_from_current_time", "temporal", "test_renewal_from_current_time"),
    TestCase("stale_and_cross_job_authority", "authority", "test_stale_and_cross_job_authority"),
    TestCase("concurrent_single_claim", "concurrency", "test_concurrent_single_claim"),
    TestCase("concurrent_expired_reclaim", "concurrency", "test_concurrent_expired_reclaim"),
    TestCase("concurrent_multi_job_claims", "concurrency", "test_concurrent_multi_job_claims"),
    TestCase("graceful_and_abrupt_persistence", "persistence", "test_persistence"),
    TestCase("bounded_cleanup", "cleanup", "test_cleanup"),
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AcceptanceFailure(message)


def _status(response: Response, expected: int, context: str) -> None:
    _require(
        response.status == expected,
        f"{context}: expected HTTP {expected}, got {response.status} with {response.json!r}",
    )


def _error(response: Response, status: int, code: str, context: str) -> None:
    _status(response, status, context)
    _require(
        response.error_code() == code,
        f"{context}: expected error code {code!r}, got {response.error_code()!r}",
    )


def _body(response: Response, context: str) -> dict[str, Any]:
    _require(isinstance(response.json, dict), f"{context}: expected JSON object")
    return cast(dict[str, Any], response.json)


class AcceptanceSuite:
    def __init__(
        self,
        controller: ServiceController,
        *,
        request_timeout: float,
        suite_deadline: float,
    ) -> None:
        self.controller = controller
        self.client = HTTPClient(
            controller.base_url,
            request_timeout=request_timeout,
            suite_deadline=suite_deadline,
        )
        self.suite_deadline = suite_deadline
        self._prefix = uuid4().hex
        self._sequence = 0

    def unique(self, label: str) -> str:
        self._sequence += 1
        return f"{self._prefix}-{self._sequence}-{label}"

    def now(self) -> int:
        response = self.client.get_clock()
        _status(response, 200, "read evaluator clock")
        value = _body(response, "read evaluator clock")["now_ms"]
        _require(isinstance(value, int) and not isinstance(value, bool), "clock must be an integer")
        return cast(int, value)

    def set_clock(self, now_ms: int) -> None:
        response = self.client.put_clock(now_ms)
        _status(response, 200, "advance evaluator clock")
        _require(_body(response, "advance evaluator clock")["now_ms"] == now_ms, "clock echo mismatch")

    def advance(self, delta_ms: int) -> int:
        _require(delta_ms >= 0, "evaluator attempted to rewind its own clock")
        target = self.now() + delta_ms
        self.set_clock(target)
        return target

    @staticmethod
    def assert_job_invariants(job: dict[str, Any], context: str) -> None:
        state = job["state"]
        if state == "pending":
            _require(job["lease"] is None, f"{context}: pending job exposes a lease")
            _require(job["result"] is None and job["failure"] is None, f"{context}: pending outcome set")
        elif state == "leased":
            _require(isinstance(job["lease"], dict), f"{context}: leased job has no lease")
            _require(job["result"] is None and job["failure"] is None, f"{context}: leased outcome set")
        elif state == "succeeded":
            _require(job["lease"] is None, f"{context}: succeeded job retained lease")
            _require(isinstance(job["result"], str), f"{context}: succeeded result missing")
            _require(job["failure"] is None, f"{context}: succeeded job has failure")
        elif state == "failed":
            _require(job["lease"] is None, f"{context}: failed job retained lease")
            _require(job["result"] is None, f"{context}: failed job has result")
            _require(isinstance(job["failure"], dict), f"{context}: failed outcome missing")
        else:  # The response schema should have caught this first.
            raise AcceptanceFailure(f"{context}: unknown state {state!r}")

    def submit_new(self, label: str, payload: str | None = None) -> dict[str, Any]:
        key = self.unique(label)
        response = self.client.submit(key, payload if payload is not None else f"payload:{label}")
        _status(response, 201, f"submit {label}")
        job = _body(response, f"submit {label}")
        self.assert_job_invariants(job, f"submit {label}")
        return job

    def claim_one(self, worker: str, ttl_ms: int) -> dict[str, Any]:
        response = self.client.claim(worker, ttl_ms)
        _status(response, 200, f"claim for {worker}")
        grant = _body(response, f"claim for {worker}")
        self.assert_job_invariants(grant["job"], f"claim for {worker}")
        return grant

    def complete_grant(self, grant: dict[str, Any], result: str = "done") -> dict[str, Any]:
        response = self.client.complete(grant["job"]["job_id"], grant["lease_token"], result)
        _status(response, 200, "complete leased job")
        job = _body(response, "complete leased job")
        self.assert_job_invariants(job, "complete leased job")
        return job

    def simultaneous(self, count: int, operation: Callable[[int], Response]) -> list[Response]:
        barrier = Barrier(count)

        def invoke(index: int) -> Response:
            barrier.wait(timeout=3.0)
            return operation(index)

        with ThreadPoolExecutor(max_workers=count, thread_name_prefix="ct-acceptance") as executor:
            futures = [executor.submit(invoke, index) for index in range(count)]
            return [future.result(timeout=5.0) for future in futures]

    def test_protocol_and_schema(self) -> None:
        health = self.client.health()
        _status(health, 200, "health")
        _require(
            _body(health, "health") == {"status": "ok", "contract_version": CONTRACT_VERSION},
            "health response does not identify contract 1.0.0",
        )
        initial = self.now()
        _require(initial == CLOCK_INITIAL_MS, f"initial clock expected {CLOCK_INITIAL_MS}, got {initial}")
        self.set_clock(initial)  # Equality is an allowed no-op.
        _error(self.client.put_clock(initial - 1), 409, "clock_rewind", "clock rewind")
        _require(self.now() == initial, "rejected rewind changed the clock")
        _error(self.client.put_clock(True), 422, "validation_error", "boolean clock")

        charset_clock = self.client.request(
            "PUT",
            "/_evaluator/clock",
            raw_body=json.dumps({"now_ms": initial}).encode("utf-8"),
            content_type="application/json; charset=utf-8",
            operation="clock_put",
        )
        _status(charset_clock, 200, "JSON media type with charset")

        nonstandard_json = self.client.request(
            "PUT",
            "/_evaluator/clock",
            raw_body=b'{"now_ms":NaN}',
            content_type="application/json",
            operation="clock_put",
        )
        _error(nonstandard_json, 400, "invalid_json", "nonstandard JSON number")

        missing_job_id = str(uuid4())
        body_operations: tuple[tuple[str, str, str, str, dict[str, Any]], ...] = (
            ("clock", "clock_put", "PUT", "/_evaluator/clock", {"now_ms": initial}),
            (
                "submit",
                "submit",
                "POST",
                "/v1/jobs",
                {"idempotency_key": self.unique("invalid"), "payload": "x"},
            ),
            (
                "claim",
                "claim",
                "POST",
                "/v1/leases",
                {"worker_id": "boundary-worker", "ttl_ms": 1},
            ),
            (
                "heartbeat",
                "heartbeat",
                "POST",
                f"/v1/jobs/{missing_job_id}/heartbeat",
                {"lease_token": "opaque", "ttl_ms": 1},
            ),
            (
                "complete",
                "complete",
                "POST",
                f"/v1/jobs/{missing_job_id}/complete",
                {"lease_token": "opaque", "result": "result"},
            ),
            (
                "fail",
                "fail",
                "POST",
                f"/v1/jobs/{missing_job_id}/fail",
                {
                    "lease_token": "opaque",
                    "failure": {"code": "code", "message": "message"},
                },
            ),
        )
        for label, operation, method, path, valid_body in body_operations:
            malformed = self.client.request(
                method,
                path,
                raw_body=b"{",
                content_type="application/json",
                operation=operation,
            )
            _error(malformed, 400, "invalid_json", f"malformed {label} JSON")
            wrong_media = self.client.request(
                method,
                path,
                raw_body=json.dumps(valid_body, separators=(",", ":")).encode("utf-8"),
                content_type="text/plain",
                operation=operation,
            )
            _error(wrong_media, 415, "unsupported_media_type", f"{label} media type")
            extra_field = self.client.request(
                method,
                path,
                json_body={**valid_body, "extra": 1},
                operation=operation,
            )
            _error(extra_field, 422, "validation_error", f"unknown {label} field")

        invalid_uuid = self.client.get_job("not-a-uuid")
        _error(invalid_uuid, 422, "validation_error", "invalid job UUID")
        noncanonical_uuid = self.client.get_job("{" + str(uuid4()) + "}")
        _error(noncanonical_uuid, 422, "validation_error", "noncanonical job UUID layout")
        missing_job = self.client.get_job(missing_job_id)
        _error(missing_job, 404, "job_not_found", "unknown job")
        for context, response in (
            ("unknown-job heartbeat", self.client.heartbeat(missing_job_id, "opaque", 1)),
            ("unknown-job completion", self.client.complete(missing_job_id, "opaque", "result")),
            ("unknown-job failure", self.client.fail(missing_job_id, "opaque", "code", "message")),
        ):
            _error(response, 404, "job_not_found", context)
        for ttl in (0, 60_001, True):
            invalid_ttl = self.client.claim("protocol-worker", ttl)
            _error(invalid_ttl, 422, "validation_error", f"invalid claim TTL {ttl!r}")
        for invalid_worker in ("", "w" * 129):
            response = self.client.claim(invalid_worker, 1)
            _error(response, 422, "validation_error", "worker_id length boundary")
        for invalid_key in ("", "k" * 129):
            response = self.client.submit(invalid_key, "x")
            _error(response, 422, "validation_error", "idempotency_key length boundary")
        oversized_payload = self.client.submit(self.unique("oversized-payload"), "p" * 65_537)
        _error(oversized_payload, 422, "validation_error", "payload maximum boundary")

        # Exercise the declared inclusive upper bounds as well as the rejected
        # values immediately outside them.
        bounded_submit = self.client.submit("k" * 128, "p" * 65_536)
        _status(bounded_submit, 201, "maximum-size submission")
        bounded_job = _body(bounded_submit, "maximum-size submission")
        bounded_grant = self.claim_one("w" * 128, 60_000)
        _require(
            bounded_grant["job"]["job_id"] == bounded_job["job_id"],
            "maximum-size submission claim mismatch",
        )
        for invalid_token in ("", "t" * 257):
            malformed_token = self.client.complete(bounded_job["job_id"], invalid_token, "x")
            _error(malformed_token, 422, "validation_error", "invalid lease-token length")
        oversized_result = self.client.complete(
            bounded_job["job_id"], bounded_grant["lease_token"], "r" * 65_537
        )
        _error(oversized_result, 422, "validation_error", "result maximum boundary")
        bounded_completion = self.client.complete(
            bounded_job["job_id"], bounded_grant["lease_token"], "r" * 65_536
        )
        _status(bounded_completion, 200, "maximum-size result")

        failure_bounds_job = self.submit_new("failure-bounds", "")
        failure_bounds_grant = self.claim_one("f", 60_000)
        _require(
            failure_bounds_grant["job"]["job_id"] == failure_bounds_job["job_id"],
            "failure bounds claim mismatch",
        )
        for code, message in (
            ("", "m"),
            ("c" * 65, "m"),
            ("c", ""),
            ("c", "m" * 4_097),
        ):
            invalid_failure = self.client.fail(
                failure_bounds_job["job_id"], failure_bounds_grant["lease_token"], code, message
            )
            _error(invalid_failure, 422, "validation_error", "failure string boundary")
        bounded_failure = self.client.fail(
            failure_bounds_job["job_id"],
            failure_bounds_grant["lease_token"],
            "c" * 64,
            "m" * 4_096,
        )
        _status(bounded_failure, 200, "maximum-size failure")

        key = self.unique("protocol-job")
        submitted_response = self.client.submit(key, "schema-observation")
        _status(submitted_response, 201, "protocol job submission")
        submitted = _body(submitted_response, "protocol job submission")
        _require(submitted["idempotency_key"] == key, "submitted idempotency key changed")
        _require(submitted["payload"] == "schema-observation", "submitted payload changed")
        _require(submitted["state"] == "pending", "new job is not pending")
        self.assert_job_invariants(submitted, "protocol job submission")
        uppercase_query = self.client.get_job(submitted["job_id"].upper())
        _status(uppercase_query, 200, "uppercase job UUID query")
        _require(uppercase_query.json == submitted, "job UUID lookup was case-sensitive")
        grant = self.claim_one("protocol-worker", 60_000)
        _require(grant["job"]["job_id"] == submitted["job_id"], "claim returned another job")
        self.complete_grant(grant, "protocol-cleanup")
        empty = self.client.claim("protocol-empty", 1)
        _status(empty, 204, "empty queue claim")

    def test_sequential_transitions(self) -> None:
        now = self.now()
        job = self.submit_new("sequential-success", "work-A")
        fetched = self.client.get_job(job["job_id"])
        _status(fetched, 200, "query pending job")
        _require(_body(fetched, "query pending job") == job, "pending query differs from submission")

        grant = self.claim_one("worker-sequential", 1_000)
        leased = grant["job"]
        _require(leased["job_id"] == job["job_id"], "sequential claim selected wrong job")
        _require(
            leased["lease"] == {"worker_id": "worker-sequential", "expires_at_ms": now + 1_000},
            "initial lease metadata mismatch",
        )

        self.advance(250)
        renewed_response = self.client.heartbeat(job["job_id"], grant["lease_token"], 700)
        _status(renewed_response, 200, "sequential heartbeat")
        renewed = _body(renewed_response, "sequential heartbeat")
        _require(renewed["lease"]["worker_id"] == "worker-sequential", "heartbeat changed worker")

        token = grant["lease_token"]
        altered_token = token + "x" if len(token) < 256 else ("x" if token[0] != "x" else "y") + token[1:]
        _error(
            self.client.complete(job["job_id"], altered_token, "wrong-token"),
            409,
            "lease_not_current",
            "altered opaque token",
        )

        completed_response = self.client.complete(job["job_id"], grant["lease_token"], "answer-A")
        _status(completed_response, 200, "sequential completion")
        completed = _body(completed_response, "sequential completion")
        _require(completed["state"] == "succeeded", "completed job is not succeeded")
        _require(completed["result"] == "answer-A", "completion result mismatch")
        self.assert_job_invariants(completed, "sequential completion")
        queried = self.client.get_job(job["job_id"])
        _status(queried, 200, "query succeeded job")
        _require(_body(queried, "query succeeded job") == completed, "terminal query mismatch")

        bogus = str(uuid4())
        _error(
            self.client.heartbeat(job["job_id"], bogus, 100),
            409,
            "lease_not_current",
            "terminal heartbeat rejection",
        )
        _error(
            self.client.complete(job["job_id"], grant["lease_token"], "again"),
            409,
            "lease_not_current",
            "duplicate completion",
        )
        _error(
            self.client.fail(job["job_id"], bogus, "late", "too late"),
            409,
            "lease_not_current",
            "terminal failure rejection",
        )

        failed_job = self.submit_new("sequential-failure", "work-B")
        failed_grant = self.claim_one("worker-failure", 500)
        _require(failed_grant["job"]["job_id"] == failed_job["job_id"], "failure claim mismatch")
        failure_response = self.client.fail(
            failed_job["job_id"], failed_grant["lease_token"], "worker_error", "declared failure"
        )
        _status(failure_response, 200, "fail leased job")
        failed = _body(failure_response, "fail leased job")
        _require(failed["state"] == "failed", "failed job state mismatch")
        _require(
            failed["failure"] == {"code": "worker_error", "message": "declared failure"},
            "failure body mismatch",
        )
        self.assert_job_invariants(failed, "fail leased job")

    def test_idempotent_submission(self) -> None:
        key = self.unique("sequential-idempotency")
        first_response = self.client.submit(key, "same-payload")
        _status(first_response, 201, "first idempotent submission")
        first = _body(first_response, "first idempotent submission")
        replay_response = self.client.submit(key, "same-payload")
        _status(replay_response, 200, "idempotent replay")
        _require(_body(replay_response, "idempotent replay") == first, "replay did not return same job")
        conflict = self.client.submit(key, "different-payload")
        _error(conflict, 409, "idempotency_conflict", "idempotency payload conflict")
        queried = self.client.get_job(first["job_id"])
        _status(queried, 200, "query after idempotency conflict")
        _require(_body(queried, "query after idempotency conflict") == first, "conflict mutated job")
        grant = self.claim_one("idempotency-cleanup", 60_000)
        _require(grant["job"]["job_id"] == first["job_id"], "idempotency cleanup claim mismatch")
        leased_replay = self.client.submit(key, "same-payload")
        _status(leased_replay, 200, "idempotent replay after claim")
        _require(leased_replay.json == grant["job"], "replay returned cached pending representation")
        terminal = self.complete_grant(grant)
        terminal_replay = self.client.submit(key, "same-payload")
        _status(terminal_replay, 200, "idempotent replay after completion")
        _require(terminal_replay.json == terminal, "replay returned cached nonterminal representation")

    def test_concurrent_idempotent_replay(self) -> None:
        key = self.unique("concurrent-idempotency")
        responses = self.simultaneous(8, lambda _index: self.client.submit(key, "same-concurrent-payload"))
        statuses = [response.status for response in responses]
        _require(statuses.count(201) == 1, f"concurrent replay created {statuses.count(201)} jobs")
        _require(statuses.count(200) == 7, f"concurrent replay statuses were {statuses!r}")
        bodies = [_body(response, "concurrent idempotent replay") for response in responses]
        job_ids = {body["job_id"] for body in bodies}
        _require(len(job_ids) == 1, f"concurrent replay returned multiple jobs: {sorted(job_ids)!r}")
        _require(all(body == bodies[0] for body in bodies), "concurrent replay representations differ")
        grant = self.claim_one("concurrent-idempotency-cleanup", 60_000)
        _require(grant["job"]["job_id"] in job_ids, "concurrent replay cleanup mismatch")
        self.complete_grant(grant)

    def test_frozen_clock_and_ttl_boundary(self) -> None:
        frozen = self.now()
        frozen_job = self.submit_new("frozen-clock")
        frozen_grant = self.claim_one("frozen-worker", 1)
        time.sleep(0.03)
        first_get = self.client.get_job(frozen_job["job_id"])
        second_get = self.client.get_job(frozen_job["job_id"])
        _status(first_get, 200, "first frozen query")
        _status(second_get, 200, "second frozen query")
        _require(
            first_get.json == second_get.json == frozen_grant["job"],
            "wall time expired a lease while the injected clock was frozen",
        )
        _require(self.now() == frozen, "wall time advanced injected clock")
        self.complete_grant(frozen_grant, "frozen-cleanup")

        boundary_job = self.submit_new("ttl-equality")
        boundary_grant = self.claim_one("boundary-old", 1_000)
        expiry = boundary_grant["job"]["lease"]["expires_at_ms"]
        self.advance(999)
        before = self.client.get_job(boundary_job["job_id"])
        _status(before, 200, "query one millisecond before expiry")
        _require(_body(before, "query before expiry")["state"] == "leased", "lease expired early")
        self.advance(1)
        reclaimed_response = self.client.claim("boundary-new", 500)
        _status(reclaimed_response, 200, "claim exactly at expiry")
        reclaimed = _body(reclaimed_response, "claim exactly at expiry")
        _require(reclaimed["job"]["job_id"] == boundary_job["job_id"], "expired job was not reclaimed")
        _require(reclaimed["lease_token"] != boundary_grant["lease_token"], "reclaim reused lease token")
        self.complete_grant(reclaimed, "boundary-cleanup")

        one_ms_key = self.unique("one-ms-ttl")
        one_ms_submit = self.client.submit(one_ms_key, "one-ms-payload")
        _status(one_ms_submit, 201, "one millisecond job submission")
        one_ms_job = _body(one_ms_submit, "one millisecond job submission")
        one_ms_grant = self.claim_one("one-ms-worker", 1)
        self.advance(1)
        _error(
            self.client.complete(one_ms_job["job_id"], one_ms_grant["lease_token"], "expired"),
            409,
            "lease_not_current",
            "completion exactly at expiry",
        )
        normalized = self.client.submit(one_ms_key, "one-ms-payload")
        _status(normalized, 200, "idempotent replay after lease expiry")
        normalized_job = _body(normalized, "idempotent replay after lease expiry")
        _require(normalized_job["state"] == "pending", "one millisecond lease did not expire at equality")
        _require(normalized_job["lease"] is None, "expired lease was not cleared")
        cleanup = self.claim_one("one-ms-cleanup", 60_000)
        self.complete_grant(cleanup)

    def test_renewal_from_current_time(self) -> None:
        job = self.submit_new("renewal-base")
        grant = self.claim_one("renewal-worker", 1_000)
        original_expiry = grant["job"]["lease"]["expires_at_ms"]
        heartbeat_time = self.advance(400)
        response = self.client.heartbeat(job["job_id"], grant["lease_token"], 300)
        _status(response, 200, "shortening heartbeat")
        renewed = _body(response, "shortening heartbeat")
        expected_expiry = heartbeat_time + 300
        _require(
            renewed["lease"]["expires_at_ms"] == expected_expiry,
            "renewal was not calculated from current clock time",
        )
        _require(expected_expiry < original_expiry, "test did not actually shorten the lease")
        _require(renewed["lease"]["worker_id"] == "renewal-worker", "renewal changed worker")
        self.advance(300)
        stale = self.client.heartbeat(job["job_id"], grant["lease_token"], 100)
        _error(stale, 409, "lease_not_current", "heartbeat exactly at renewed expiry")
        pending = self.client.get_job(job["job_id"])
        _status(pending, 200, "query after renewed expiry")
        pending_job = _body(pending, "query after renewed expiry")
        _require(pending_job["state"] == "pending", "renewed lease remained current at equality")
        cleanup = self.claim_one("renewal-cleanup", 100)
        self.complete_grant(cleanup)

    def test_stale_and_cross_job_authority(self) -> None:
        stale_job = self.submit_new("stale-holder")
        old_grant = self.claim_one("stale-old", 10)
        self.advance(10)
        new_grant = self.claim_one("stale-new", 1_000)
        _require(new_grant["job"]["job_id"] == stale_job["job_id"], "stale job not reclaimed")
        stale_operations: tuple[tuple[str, Callable[[], Response]], ...] = (
            (
                "heartbeat",
                lambda: self.client.heartbeat(stale_job["job_id"], old_grant["lease_token"], 100),
            ),
            (
                "complete",
                lambda: self.client.complete(stale_job["job_id"], old_grant["lease_token"], "stale"),
            ),
            (
                "fail",
                lambda: self.client.fail(
                    stale_job["job_id"], old_grant["lease_token"], "stale", "stale holder"
                ),
            ),
        )
        for name, operation in stale_operations:
            _error(operation(), 409, "lease_not_current", f"stale-holder {name}")
        still_current = self.client.get_job(stale_job["job_id"])
        _status(still_current, 200, "query after stale operations")
        _require(still_current.json == new_grant["job"], "stale holder mutated current lease")
        self.complete_grant(new_grant, "current-holder-wins")

        first = self.submit_new("cross-token-A")
        second = self.submit_new("cross-token-B")
        grant_one = self.claim_one("cross-worker-A", 1_000)
        grant_two = self.claim_one("cross-worker-B", 1_000)
        by_id = {
            grant_one["job"]["job_id"]: grant_one,
            grant_two["job"]["job_id"]: grant_two,
        }
        _require(set(by_id) == {first["job_id"], second["job_id"]}, "cross-token setup mismatch")
        target = by_id[second["job_id"]]
        foreign = by_id[first["job_id"]]
        cross_job_operations: tuple[tuple[str, Callable[[], Response]], ...] = (
            (
                "heartbeat",
                lambda: self.client.heartbeat(second["job_id"], foreign["lease_token"], 100),
            ),
            (
                "complete",
                lambda: self.client.complete(second["job_id"], foreign["lease_token"], "foreign"),
            ),
            (
                "fail",
                lambda: self.client.fail(
                    second["job_id"], foreign["lease_token"], "foreign", "wrong job"
                ),
            ),
        )
        for name, operation in cross_job_operations:
            _error(operation(), 409, "lease_not_current", f"cross-job {name}")
        target_after = self.client.get_job(second["job_id"])
        _status(target_after, 200, "query cross-token target")
        _require(target_after.json == target["job"], "foreign token mutated target job")
        self.complete_grant(foreign, "cross-A-cleanup")
        self.complete_grant(target, "cross-B-cleanup")

    def test_concurrent_single_claim(self) -> None:
        job = self.submit_new("single-concurrent-claim")
        responses = self.simultaneous(
            12, lambda index: self.client.claim(f"single-claim-worker-{index}", 1_000)
        )
        winners = [response for response in responses if response.status == 200]
        empty = [response for response in responses if response.status == 204]
        _require(len(winners) == 1, f"one pending job produced {len(winners)} concurrent lease grants")
        _require(len(empty) == 11, "losing concurrent claims did not return HTTP 204")
        grant = _body(winners[0], "concurrent single-claim winner")
        _require(grant["job"]["job_id"] == job["job_id"], "concurrent claim selected wrong job")
        self.complete_grant(grant, "single-claim-cleanup")

    def test_concurrent_expired_reclaim(self) -> None:
        job = self.submit_new("concurrent-reclaim")
        old = self.claim_one("reclaim-old", 5)
        self.advance(5)
        responses = self.simultaneous(
            12, lambda index: self.client.claim(f"reclaim-worker-{index}", 1_000)
        )
        winners = [response for response in responses if response.status == 200]
        empty = [response for response in responses if response.status == 204]
        _require(len(winners) == 1, f"expired job produced {len(winners)} concurrent reclaims")
        _require(len(empty) == 11, "losing concurrent reclaims did not return HTTP 204")
        grant = _body(winners[0], "concurrent reclaim winner")
        _require(grant["job"]["job_id"] == job["job_id"], "reclaim returned wrong job")
        _require(grant["lease_token"] != old["lease_token"], "concurrent reclaim reused stale token")
        self.complete_grant(grant, "reclaim-cleanup")

    def test_concurrent_multi_job_claims(self) -> None:
        jobs = [self.submit_new(f"multi-claim-{index}") for index in range(5)]
        expected_ids = {job["job_id"] for job in jobs}
        responses = self.simultaneous(
            10, lambda _index: self.client.claim("shared-multi-claim-worker", 1_000)
        )
        grants = [_body(response, "multi-job claim") for response in responses if response.status == 200]
        empty = [response for response in responses if response.status == 204]
        _require(len(grants) == 5, f"five jobs produced {len(grants)} grants")
        _require(len(empty) == 5, "extra multi-job claims did not return HTTP 204")
        granted_ids = [grant["job"]["job_id"] for grant in grants]
        _require(set(granted_ids) == expected_ids, "multi-job claims lost or invented a job")
        _require(len(granted_ids) == len(set(granted_ids)), "a job was leased more than once")
        tokens = [grant["lease_token"] for grant in grants]
        _require(len(tokens) == len(set(tokens)), "independent leases reused an authority token")
        for grant in grants:
            self.complete_grant(grant, "multi-claim-cleanup")

    def test_persistence(self) -> None:
        succeeded = self.submit_new("persistent-succeeded", "succeeded-payload")
        succeeded_grant = self.claim_one("persistent-succeeded-worker", 10_000)
        succeeded_response = self.client.complete(
            succeeded["job_id"], succeeded_grant["lease_token"], "persisted-result"
        )
        _status(succeeded_response, 200, "prepare persistent succeeded job")
        succeeded = _body(succeeded_response, "prepare persistent succeeded job")

        failed = self.submit_new("persistent-failed", "failed-payload")
        failed_grant = self.claim_one("persistent-failed-worker", 10_000)
        failed_response = self.client.fail(
            failed["job_id"], failed_grant["lease_token"], "persisted", "persisted failure"
        )
        _status(failed_response, 200, "prepare persistent failed job")
        failed = _body(failed_response, "prepare persistent failed job")

        leased = self.submit_new("persistent-leased", "leased-payload")
        leased_grant = self.claim_one("persistent-live-worker", 10_000)
        _require(leased_grant["job"]["job_id"] == leased["job_id"], "persistent lease mismatch")
        leased = leased_grant["job"]
        pending = self.submit_new("persistent-pending", "pending-payload")

        expected = {
            "pending": pending,
            "leased": leased,
            "succeeded": succeeded,
            "failed": failed,
        }

        def assert_snapshot(restart_kind: str) -> None:
            for state, job in expected.items():
                query = self.client.get_job(job["job_id"])
                _status(query, 200, f"query {state} after {restart_kind} restart")
                _require(
                    query.json == job,
                    f"{restart_kind} restart changed or lost {state} job",
                )
                replay = self.client.submit(job["idempotency_key"], job["payload"])
                _status(replay, 200, f"replay {state} after {restart_kind} restart")
                _require(
                    replay.json == job,
                    f"{restart_kind} restart lost {state} idempotency representation",
                )

        restart_clock = self.now() + 17
        self.controller.set_restart_clock(restart_clock)
        graceful = self.controller.restart(graceful=True)
        _require(
            graceful.graceful_requested
            and not graceful.forced_kill
            and graceful.return_code == 0,
            f"graceful restart did not exit cleanly: {graceful!r}",
        )
        _require(self.now() == restart_clock, "restart did not restore the injected clock")
        assert_snapshot("graceful")

        renewed_response = self.client.heartbeat(
            leased["job_id"], leased_grant["lease_token"], 10_000
        )
        _status(renewed_response, 200, "use lease authority after graceful restart")
        expected["leased"] = _body(
            renewed_response, "use lease authority after graceful restart"
        )

        self.controller.set_restart_clock(self.now())
        self.controller.restart(graceful=False)
        assert_snapshot("abrupt")
        completion = self.client.complete(
            leased["job_id"], leased_grant["lease_token"], "after-abrupt-restart"
        )
        _status(completion, 200, "use lease authority after abrupt restart")
        completed = _body(completion, "use lease authority after abrupt restart")
        _require(completed["state"] == "succeeded", "persisted lease could not complete")

    def test_cleanup(self) -> None:
        final = self.controller.stop(graceful=True)
        graceful_results = [
            result for result in self.controller.shutdown_history if result.graceful_requested
        ]
        _require(bool(graceful_results), "no graceful shutdown was exercised")
        _require(
            not any(result.forced_kill for result in graceful_results),
            "service ignored SIGTERM and required SIGKILL",
        )
        _require(
            all(result.return_code == 0 for result in graceful_results),
            f"graceful shutdown returned nonzero: {graceful_results!r}",
        )
        _require(not final.forced_kill, "final service shutdown exceeded its bound")


def _layer_summary(results: Sequence[TestResult]) -> dict[str, dict[str, Any]]:
    layers: dict[str, dict[str, Any]] = {}
    for result in results:
        layer = layers.setdefault(result.layer, {"passed": True, "tests": []})
        layer["tests"].append(result.name)
        if not result.passed:
            layer["passed"] = False
    return layers


def run_acceptance(
    *,
    base_url: str,
    service_command: str,
    fail_fast: bool = False,
    extra_env: dict[str, str] | None = None,
    suite_timeout: float = DEFAULT_SUITE_TIMEOUT_SECONDS,
    startup_timeout: float = DEFAULT_STARTUP_TIMEOUT_SECONDS,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT_SECONDS,
    shutdown_timeout: float = DEFAULT_SHUTDOWN_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    started_wall = datetime.now(timezone.utc)
    started = time.monotonic()
    deadline = started + suite_timeout
    controller = ServiceController(
        base_url=base_url,
        command=service_command,
        clock_initial_ms=CLOCK_INITIAL_MS,
        startup_timeout=startup_timeout,
        shutdown_timeout=shutdown_timeout,
        suite_deadline=deadline,
        extra_env=extra_env,
    )
    results: list[TestResult] = []
    startup_error: str | None = None
    log_tail = ""
    try:
        assert_contract_alignment()
        controller.start()
        suite = AcceptanceSuite(
            controller,
            request_timeout=request_timeout,
            suite_deadline=deadline,
        )
        for case in TEST_CASES:
            if time.monotonic() >= deadline:
                results.append(
                    TestResult(
                        name=case.name,
                        layer=case.layer,
                        passed=False,
                        duration_ms=0,
                        detail=f"suite deadline of {suite_timeout:.1f}s exceeded",
                    )
                )
                break
            test_started = time.monotonic()
            try:
                method = getattr(suite, case.method_name)
                method()
            except Exception as exc:  # Each failure belongs to its declared layer.
                detail = "".join(traceback.format_exception_only(type(exc), exc)).strip()
                results.append(
                    TestResult(
                        name=case.name,
                        layer=case.layer,
                        passed=False,
                        duration_ms=round((time.monotonic() - test_started) * 1_000),
                        detail=detail,
                    )
                )
                if fail_fast:
                    break
            else:
                results.append(
                    TestResult(
                        name=case.name,
                        layer=case.layer,
                        passed=True,
                        duration_ms=round((time.monotonic() - test_started) * 1_000),
                    )
                )
    except Exception as exc:
        startup_error = "".join(traceback.format_exception_only(type(exc), exc)).strip()
    finally:
        shutdowns_before_close = list(controller.shutdown_history)
        try:
            log_tail = controller.close()
        except Exception as exc:
            close_detail = "".join(traceback.format_exception_only(type(exc), exc)).strip()
            results.append(
                TestResult(
                    name="controller_finalizer",
                    layer="cleanup",
                    passed=False,
                    duration_ms=0,
                    detail=close_detail,
                )
            )
        shutdowns = list(controller.shutdown_history)
        if not shutdowns:
            shutdowns = shutdowns_before_close

    passed = startup_error is None and len(results) == len(TEST_CASES) and all(
        result.passed for result in results
    )
    report: dict[str, Any] = {
        "evaluator_version": EVALUATOR_VERSION,
        "contract_version": CONTRACT_VERSION,
        "started_at": started_wall.isoformat(),
        "base_url": base_url,
        "service_command": service_command,
        "passed": passed,
        "duration_ms": round((time.monotonic() - started) * 1_000),
        "limits": {
            "suite_timeout_seconds": suite_timeout,
            "startup_timeout_seconds": startup_timeout,
            "request_timeout_seconds": request_timeout,
            "shutdown_timeout_seconds": shutdown_timeout,
        },
        "startup_error": startup_error,
        "tests": [asdict(result) for result in results],
        "layers": _layer_summary(results),
        "shutdowns": [asdict(result) for result in shutdowns],
        "service_log_tail": log_tail[-8_192:],
    }
    return report


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="explicit local HTTP service URL")
    parser.add_argument(
        "--service-command",
        required=True,
        help="foreground service command, parsed as argv without a shell",
    )
    parser.add_argument("--fail-fast", action="store_true", help="stop after the first failed test")
    parser.add_argument("--json-report", type=Path, help="also write the JSON report to this path")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = run_acceptance(
            base_url=args.base_url,
            service_command=args.service_command,
            fail_fast=args.fail_fast,
        )
    except (ValueError, ControllerFailure) as exc:
        print(json.dumps({"passed": False, "fatal_error": str(exc)}, indent=2), file=sys.stdout)
        return 2
    if args.json_report is not None:
        _write_report(args.json_report, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
