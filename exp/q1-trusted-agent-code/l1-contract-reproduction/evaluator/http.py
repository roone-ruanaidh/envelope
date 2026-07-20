"""Bounded HTTP client and response conformance checks."""

from __future__ import annotations

import json
import socket
import time
from dataclasses import dataclass
from http.client import HTTPConnection, HTTPException, HTTPResponse
from threading import Event, Thread
from typing import Any, Mapping
from urllib.parse import quote, urlsplit

from .schema import SchemaViolation, canonical_response_schemas, validate_json


# Larger than the worst-case escaped Job/LeaseGrant permitted by the public
# string bounds, while still bounding a broken service response.
MAX_RESPONSE_BYTES = 4_194_304


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key {key!r}")
        result[key] = value
    return result


def _reject_nonstandard_constant(value: str) -> None:
    raise ValueError(f"nonstandard JSON constant {value}")


class TransportFailure(AssertionError):
    """A request could not complete within the evaluator boundary."""


@dataclass(frozen=True)
class Response:
    status: int
    headers: Mapping[str, str]
    body: bytes
    json: Any | None

    def error_code(self) -> str | None:
        if not isinstance(self.json, dict):
            return None
        error = self.json.get("error")
        return error.get("code") if isinstance(error, dict) else None


class HTTPClient:
    def __init__(
        self,
        base_url: str,
        *,
        request_timeout: float = 3.0,
        suite_deadline: float | None = None,
    ) -> None:
        parsed = urlsplit(base_url)
        if (
            parsed.scheme != "http"
            or parsed.hostname is None
            or parsed.port is None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
            or parsed.username
            or parsed.password
        ):
            raise ValueError("base URL must be an explicit origin-only http://host:port URL")
        self.base_url = base_url.rstrip("/")
        self.host = parsed.hostname
        self.port = parsed.port
        self.request_timeout = request_timeout
        self.suite_deadline = suite_deadline

    def _deadline(self) -> float:
        now = time.monotonic()
        deadline = now + self.request_timeout
        if self.suite_deadline is not None:
            deadline = min(deadline, self.suite_deadline)
        if deadline <= now:
            raise TransportFailure("acceptance-suite deadline exceeded before request")
        return deadline

    @staticmethod
    def _abort_at_deadline(
        connection: HTTPConnection,
        socket_holder: list[socket.socket | None],
        response_holder: list[HTTPResponse | None],
        deadline: float,
        done: Event,
        expired: Event,
    ) -> None:
        if done.wait(max(0.0, deadline - time.monotonic())):
            return
        expired.set()
        active_socket = socket_holder[0] or connection.sock
        if active_socket is not None:
            try:
                active_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            active_socket.close()
        response = response_holder[0]
        if response is not None:
            response.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any | None = None,
        raw_body: bytes | None = None,
        content_type: str | None = "application/json",
        operation: str | None = None,
    ) -> Response:
        if json_body is not None and raw_body is not None:
            raise ValueError("json_body and raw_body are mutually exclusive")
        body = raw_body
        if json_body is not None:
            body = json.dumps(json_body, separators=(",", ":")).encode("utf-8")
        headers = {"Accept": "application/json"}
        if body is not None and content_type is not None:
            headers["Content-Type"] = content_type
        deadline = self._deadline()
        connection = HTTPConnection(
            self.host,
            self.port,
            timeout=max(0.01, deadline - time.monotonic()),
        )
        done = Event()
        expired = Event()
        socket_holder: list[socket.socket | None] = [None]
        response_holder: list[HTTPResponse | None] = [None]
        watchdog = Thread(
            target=self._abort_at_deadline,
            args=(connection, socket_holder, response_holder, deadline, done, expired),
            name="q1-l1-http-deadline",
            daemon=True,
        )
        watchdog.start()
        try:
            connection.request(method, "/" + path.lstrip("/"), body=body, headers=headers)
            socket_holder[0] = connection.sock
            raw_response = connection.getresponse()
            response_holder[0] = raw_response
            response = self._read_response(
                raw_response.status,
                raw_response.headers,
                raw_response,
            )
        except (HTTPException, TimeoutError, OSError) as exc:
            if expired.is_set():
                raise TransportFailure(
                    f"{method} {path} exceeded its absolute request deadline"
                ) from exc
            raise TransportFailure(f"{method} {path} failed: {exc}") from exc
        except SchemaViolation as exc:
            if expired.is_set():
                raise TransportFailure(
                    f"{method} {path} exceeded its absolute request deadline"
                ) from exc
            raise
        finally:
            done.set()
            connection.close()
            watchdog.join(timeout=0.05)
        if expired.is_set():
            raise TransportFailure(f"{method} {path} exceeded its absolute request deadline")
        if operation is not None:
            self.validate_response(operation, response)
        return response

    @staticmethod
    def _read_response(status: int, headers: Any, stream: Any) -> Response:
        body = stream.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise SchemaViolation(f"response exceeds {MAX_RESPONSE_BYTES} bytes")
        header_map = {str(key).lower(): str(value) for key, value in headers.items()}
        parsed: Any | None = None
        if body:
            try:
                parsed = json.loads(
                    body.decode("utf-8"),
                    object_pairs_hook=_reject_duplicate_keys,
                    parse_constant=_reject_nonstandard_constant,
                )
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                raise SchemaViolation(f"HTTP {status} body is not valid UTF-8 JSON") from exc
        return Response(status=status, headers=header_map, body=body, json=parsed)

    @staticmethod
    def validate_response(operation: str, response: Response) -> None:
        canonical_schemas = canonical_response_schemas(operation)
        if response.status not in canonical_schemas:
            raise SchemaViolation(
                f"{operation}: undeclared HTTP status {response.status}; "
                f"expected {sorted(canonical_schemas)}"
            )
        if response.status == 204:
            if response.body:
                raise SchemaViolation(f"{operation}: HTTP 204 must have an empty body")
            return
        media_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if media_type != "application/json":
            raise SchemaViolation(
                f"{operation}: expected Content-Type application/json, got {media_type or '<missing>'}"
            )
        if response.json is None:
            raise SchemaViolation(f"{operation}: HTTP {response.status} requires a JSON body")
        schema = canonical_schemas[response.status]
        if schema is None:
            raise RuntimeError(f"{operation}: canonical schema missing for HTTP {response.status}")
        validate_json(response.json, schema)

    def health(self) -> Response:
        return self.request("GET", "/healthz", operation="health")

    def get_clock(self) -> Response:
        return self.request("GET", "/_evaluator/clock", operation="clock_get")

    def put_clock(self, now_ms: Any) -> Response:
        return self.request(
            "PUT", "/_evaluator/clock", json_body={"now_ms": now_ms}, operation="clock_put"
        )

    def submit(self, idempotency_key: str, payload: str) -> Response:
        return self.request(
            "POST",
            "/v1/jobs",
            json_body={"idempotency_key": idempotency_key, "payload": payload},
            operation="submit",
        )

    def get_job(self, job_id: str) -> Response:
        return self.request(
            "GET", f"/v1/jobs/{quote(job_id, safe='')}", operation="get_job"
        )

    def claim(self, worker_id: str, ttl_ms: Any) -> Response:
        return self.request(
            "POST",
            "/v1/leases",
            json_body={"worker_id": worker_id, "ttl_ms": ttl_ms},
            operation="claim",
        )

    def heartbeat(self, job_id: str, lease_token: str, ttl_ms: Any) -> Response:
        return self.request(
            "POST",
            f"/v1/jobs/{quote(job_id, safe='')}/heartbeat",
            json_body={"lease_token": lease_token, "ttl_ms": ttl_ms},
            operation="heartbeat",
        )

    def complete(self, job_id: str, lease_token: str, result: str) -> Response:
        return self.request(
            "POST",
            f"/v1/jobs/{quote(job_id, safe='')}/complete",
            json_body={"lease_token": lease_token, "result": result},
            operation="complete",
        )

    def fail(self, job_id: str, lease_token: str, code: str, message: str) -> Response:
        return self.request(
            "POST",
            f"/v1/jobs/{quote(job_id, safe='')}/fail",
            json_body={
                "lease_token": lease_token,
                "failure": {"code": code, "message": message},
            },
            operation="fail",
        )
