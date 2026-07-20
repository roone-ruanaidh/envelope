"""Launch one candidate service inside the Q1/L1 isolation boundary."""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any

from .candidate_exec import (
    CandidateResourceEnvelope,
    ENTRY_TOKEN,
    WritableStateEnvelope,
)


ROOT = Path(__file__).resolve().parents[1]
ARGV_MAX_ENTRIES = 128
ARGV_MAX_ENTRY_BYTES = 8 * 1024
ARGV_MAX_AGGREGATE_BYTES = 64 * 1024
_sandbox_child_pid: int | None = None
_termination_requested = False
_force_kill_requested = False


def _require_environment(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"missing required isolated-service environment variable {name}")
    return value


def _handle_sigterm(_signum: int, _frame: object) -> None:
    global _termination_requested
    _termination_requested = True
    if _sandbox_child_pid is not None:
        try:
            os.kill(_sandbox_child_pid, signal.SIGTERM)
        except ProcessLookupError:
            pass


def _handle_force_kill(_signum: int, _frame: object) -> None:
    global _force_kill_requested
    _force_kill_requested = True
    if _sandbox_child_pid is not None:
        try:
            os.kill(_sandbox_child_pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def _assert_no_external_route() -> None:
    probe = socket.socket()
    probe.settimeout(0.1)
    try:
        if probe.connect_ex(("1.1.1.1", 80)) == 0:
            raise RuntimeError("isolated service wrapper unexpectedly has external network access")
    finally:
        probe.close()


def _candidate_command() -> list[str]:
    try:
        value = json.loads(_require_environment("Q1_L1_CANDIDATE_ARGV_JSON"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("candidate service command is not valid JSON") from exc
    if not isinstance(value, list) or not value or len(value) > ARGV_MAX_ENTRIES:
        raise RuntimeError("candidate service command must be a nonempty JSON array")
    if not all(isinstance(argument, str) and "\0" not in argument for argument in value):
        raise RuntimeError("candidate service command arguments must be NUL-free strings")
    if not value[0]:
        raise RuntimeError("candidate service executable must not be empty")
    aggregate = 0
    for argument in value:
        try:
            encoded = argument.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise RuntimeError("candidate service command must be valid UTF-8") from exc
        if len(encoded) > ARGV_MAX_ENTRY_BYTES:
            raise RuntimeError("candidate service command argument exceeds its byte limit")
        aggregate += len(encoded) + 1
    if aggregate > ARGV_MAX_AGGREGATE_BYTES:
        raise RuntimeError("candidate service command exceeds its aggregate byte limit")
    return value


def _sandbox_command(
    candidate_root: Path,
    command_argv: list[str],
    info_fd: int,
    *,
    state_directory: Path | None = None,
    temporary_directory: Path | None = None,
) -> list[str]:
    database_path = Path(_require_environment("Q1_L1_DATABASE_PATH"))
    state_directory = state_directory or database_path.parent

    inner_database = f"/state/{database_path.name}"
    environment = {
        "Q1_L1_HOST": _require_environment("Q1_L1_HOST"),
        "Q1_L1_PORT": _require_environment("Q1_L1_PORT"),
        "Q1_L1_DATABASE_PATH": inner_database,
        "Q1_L1_CLOCK_INITIAL_MS": _require_environment("Q1_L1_CLOCK_INITIAL_MS"),
        "HOME": "/tmp",
        "Q1_L1_CANDIDATE_ENTRY_SOCKET": "/state/.q1-l1-entry.sock",
        "PATH": "/work/.venv/bin:/usr/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
    }
    command = [
        "/usr/bin/bwrap",
        "--ro-bind",
        "/usr",
        "/usr",
        "--ro-bind",
        "/lib",
        "/lib",
        "--ro-bind",
        str(candidate_root),
        "/work",
        "--bind",
        str(state_directory),
        "/state",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--unshare-user",
        "--unshare-pid",
        "--unshare-ipc",
        "--unshare-uts",
        "--unshare-cgroup-try",
        "--disable-userns",
        "--die-with-parent",
        "--as-pid-1",
        "--info-fd",
        str(info_fd),
        "--uid",
        "65534",
        "--gid",
        "65534",
        "--chdir",
        "/work",
        "--clearenv",
    ]
    command.extend(
        ("--tmpfs", "/tmp")
        if temporary_directory is None
        else ("--bind", str(temporary_directory), "/tmp")
    )
    for name, value in environment.items():
        command.extend(("--setenv", name, value))
    command.extend(
        (
            "--ro-bind",
            str(ROOT / "evaluator" / "candidate_exec.py"),
            "/q1-l1-candidate-exec.py",
            "--",
            "/usr/bin/python3",
            "/q1-l1-candidate-exec.py",
            "--",
            *command_argv,
        )
    )
    return command


def run() -> int:
    global _sandbox_child_pid

    if os.geteuid() != 0 or os.environ.get("Q1_L1_OUTER_NETNS") != "1":
        raise RuntimeError("isolated service wrapper must run as root inside the outer network namespace")
    _assert_no_external_route()

    candidate_root = Path(_require_environment("Q1_L1_CANDIDATE_ROOT")).resolve()
    if (
        not candidate_root.is_dir()
        or candidate_root == ROOT
        or candidate_root.is_relative_to(ROOT)
        or ROOT.is_relative_to(candidate_root)
    ):
        raise RuntimeError("candidate root and evaluator source tree must be disjoint")
    if not (candidate_root / ".venv" / "bin" / "python").is_file():
        raise RuntimeError("candidate root lacks its preprovisioned locked virtual environment")
    command_argv = _candidate_command()
    database_directory = Path(_require_environment("Q1_L1_DATABASE_PATH")).parent
    with WritableStateEnvelope(database_directory, persistent=True) as writable:
        entry_path = writable.state / ".q1-l1-entry.sock"
        entry_path.unlink(missing_ok=True)
        entry_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        entry_socket.bind(str(entry_path))
        entry_path.chmod(0o777)
        entry_socket.setblocking(False)

        info_read, info_write = os.pipe()
        try:
            with CandidateResourceEnvelope() as resources:
                process = subprocess.Popen(
                    _sandbox_command(
                        candidate_root,
                        command_argv,
                        info_write,
                        state_directory=writable.state,
                        temporary_directory=writable.temporary,
                    ),
                    pass_fds=(info_write,),
                    start_new_session=True,
                    preexec_fn=resources.enter_child,
                )
                os.close(info_write)
                with os.fdopen(info_read, encoding="utf-8") as info_stream:
                    sandbox_info: Any = json.load(info_stream)
                if not isinstance(sandbox_info, dict) or not isinstance(
                    sandbox_info.get("child-pid"), int
                ):
                    process.kill()
                    raise RuntimeError(
                        f"bubblewrap did not report the candidate PID: {sandbox_info!r}"
                    )
                _sandbox_child_pid = sandbox_info["child-pid"]
                if _termination_requested:
                    _handle_sigterm(signal.SIGTERM, None)
                if _force_kill_requested:
                    _handle_force_kill(signal.SIGUSR1, None)
                return_code = process.wait()
                try:
                    entered = entry_socket.recv(len(ENTRY_TOKEN) + 1) == ENTRY_TOKEN
                except BlockingIOError:
                    entered = False
        finally:
            try:
                os.close(info_write)
            except OSError:
                pass
            try:
                os.close(info_read)
            except OSError:
                pass
            entry_socket.close()
            entry_path.unlink(missing_ok=True)
    return return_code if entered and return_code != 125 else 125


def main() -> int:
    signal.signal(signal.SIGTERM, _handle_sigterm)
    signal.signal(signal.SIGUSR1, _handle_force_kill)
    try:
        return run()
    except Exception as exc:
        print(f"isolated service wrapper failed: {exc}", file=sys.stderr)
        return 125


if __name__ == "__main__":
    raise SystemExit(main())
