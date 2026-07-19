"""Foreground service lifecycle control with bounded teardown."""

from __future__ import annotations

import os
import shlex
import signal
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Lock, Thread
from typing import BinaryIO, Mapping
from urllib.parse import urlparse

from .http import HTTPClient, TransportFailure


class ControllerFailure(AssertionError):
    """The service did not obey the evaluator process boundary."""


MAX_SERVICE_LOG_BYTES = 65_536


@dataclass(frozen=True)
class ShutdownResult:
    graceful_requested: bool
    forced_kill: bool
    return_code: int | None
    elapsed_seconds: float


class ServiceController:
    def __init__(
        self,
        *,
        base_url: str,
        command: str,
        clock_initial_ms: int,
        startup_timeout: float = 8.0,
        shutdown_timeout: float = 1.5,
        suite_deadline: float | None = None,
        extra_env: Mapping[str, str] | None = None,
    ) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme != "http" or parsed.hostname is None or parsed.port is None:
            raise ValueError("base URL must be an explicit http://host:port URL")
        if parsed.hostname not in {"127.0.0.1", "localhost"}:
            raise ValueError("base URL must use the local loopback host")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("base URL must not contain credentials, a query, or a fragment")
        if parsed.path not in {"", "/"}:
            raise ValueError("base URL must not contain a path prefix")
        argv = shlex.split(command)
        if not argv:
            raise ValueError("service command must not be empty")
        self.base_url = base_url.rstrip("/")
        self.host = parsed.hostname
        self.port = parsed.port
        self.argv = argv
        self.startup_timeout = startup_timeout
        self.shutdown_timeout = shutdown_timeout
        self.suite_deadline = suite_deadline
        self._temporary = tempfile.TemporaryDirectory(prefix="ct-e1-evaluator-")
        self.run_directory = Path(self._temporary.name)
        self.database_path = self.run_directory / "service.sqlite3"
        self._log_tail = bytearray()
        self._log_lock = Lock()
        self._log_thread: Thread | None = None
        self._process: subprocess.Popen[bytes] | None = None
        self._closed = False
        self.shutdown_history: list[ShutdownResult] = []
        env = os.environ.copy()
        env.update(
            {
                "CT_HOST": parsed.hostname,
                "CT_PORT": str(parsed.port),
                "CT_DATABASE_PATH": str(self.database_path),
                "CT_CLOCK_INITIAL_MS": str(clock_initial_ms),
            }
        )
        if extra_env:
            env.update(extra_env)
        self.environment = env
        self.cwd = Path(__file__).resolve().parents[1]

    @property
    def process(self) -> subprocess.Popen[bytes] | None:
        return self._process

    def _listener_is_open(self) -> bool:
        try:
            with socket.create_connection((self.host, self.port), timeout=0.05):
                return True
        except OSError:
            return False

    def _bounded_timeout(self, configured: float) -> float:
        if self.suite_deadline is None:
            return configured
        return max(0.01, min(configured, self.suite_deadline - time.monotonic()))

    def _wait_for_listener_close(self, timeout: float = 0.25) -> bool:
        deadline = time.monotonic() + self._bounded_timeout(timeout)
        while time.monotonic() < deadline:
            if not self._listener_is_open():
                return True
            time.sleep(0.01)
        return not self._listener_is_open()

    def _capture_output(self, stream: BinaryIO) -> None:
        try:
            while chunk := stream.read(8_192):
                with self._log_lock:
                    self._log_tail.extend(chunk)
                    if len(self._log_tail) > MAX_SERVICE_LOG_BYTES:
                        del self._log_tail[:-MAX_SERVICE_LOG_BYTES]
        except (OSError, ValueError):
            pass
        finally:
            stream.close()

    def _finish_log_capture(self, process: subprocess.Popen[bytes]) -> None:
        thread = self._log_thread
        stream = process.stdout
        if thread is not None:
            thread.join(timeout=0.05)
        if thread is not None and thread.is_alive() and stream is not None:
            stream.close()
            thread.join(timeout=0.05)
        self._log_thread = None

    def start(self) -> None:
        if self._closed:
            raise ControllerFailure("controller is already closed")
        if self._process is not None and self._process.poll() is None:
            raise ControllerFailure("service is already running")
        if self._listener_is_open():
            raise ControllerFailure("base URL already has a listener before service start")
        self._process = subprocess.Popen(
            self.argv,
            cwd=self.cwd,
            env=self.environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
            start_new_session=True,
        )
        if self._process.stdout is None:  # pragma: no cover - guaranteed by PIPE
            raise ControllerFailure("service output pipe was not created")
        self._log_thread = Thread(
            target=self._capture_output,
            args=(self._process.stdout,),
            name="ct-service-log",
            daemon=True,
        )
        self._log_thread.start()
        deadline = time.monotonic() + self.startup_timeout
        if self.suite_deadline is not None:
            deadline = min(deadline, self.suite_deadline)
        client = HTTPClient(self.base_url, request_timeout=0.25, suite_deadline=deadline)
        last_error = "service was not reachable"
        while time.monotonic() < deadline:
            if self._process.poll() is not None:
                self._finish_log_capture(self._process)
                raise ControllerFailure(
                    f"service exited during startup with {self._process.returncode}; "
                    f"log tail: {self.log_tail()!r}"
                )
            try:
                # Readiness establishes that the endpoint appeared after launch.
                # Listener closure after stop supplies the paired lifecycle check;
                # protocol/schema adjudication belongs to the acceptance layer.
                response = client.request("GET", "/healthz")
                if response.status == 200:
                    return
            except (TransportFailure, AssertionError) as exc:
                last_error = str(exc)
            time.sleep(0.03)
        self.stop(graceful=False)
        raise ControllerFailure(
            f"service did not become ready within {self.startup_timeout:.1f}s: {last_error}; "
            f"log tail: {self.log_tail()!r}"
        )

    def stop(self, *, graceful: bool) -> ShutdownResult:
        process = self._process
        started = time.monotonic()
        if process is None:
            return ShutdownResult(graceful, False, None, 0.0)
        forced = False
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM if graceful else signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                process.wait(
                    timeout=self._bounded_timeout(self.shutdown_timeout if graceful else 0.75)
                )
            except subprocess.TimeoutExpired:
                forced = True
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=self._bounded_timeout(0.75))
                except subprocess.TimeoutExpired as exc:
                    raise ControllerFailure("service process group survived SIGKILL") from exc
        result = ShutdownResult(
            graceful_requested=graceful,
            forced_kill=forced,
            return_code=process.returncode,
            elapsed_seconds=time.monotonic() - started,
        )
        self._finish_log_capture(process)
        self.shutdown_history.append(result)
        self._process = None
        if not self._wait_for_listener_close():
            raise ControllerFailure("service listener remained reachable after process shutdown")
        return result

    def restart(self, *, graceful: bool) -> ShutdownResult:
        result = self.stop(graceful=graceful)
        self.start()
        return result

    def set_restart_clock(self, now_ms: int) -> None:
        """Set the injected clock value used by the next process generation."""

        if now_ms < 0 or isinstance(now_ms, bool):
            raise ValueError("restart clock must be a nonnegative integer")
        self.environment["CT_CLOCK_INITIAL_MS"] = str(now_ms)

    def log_tail(self, limit: int = 8_192) -> str:
        with self._log_lock:
            data = bytes(self._log_tail[-limit:])
        return data.decode("utf-8", errors="replace")

    def close(self) -> str:
        if self._closed:
            return ""
        stop_error: Exception | None = None
        try:
            if self._process is not None:
                self.stop(graceful=True)
        except Exception as exc:
            stop_error = exc
        finally:
            tail = self.log_tail()
            self._temporary.cleanup()
            self._closed = True
        if stop_error is not None:
            raise stop_error
        return tail
