"""Launch one candidate service inside the frozen e1 mount boundary."""

from __future__ import annotations

import json
import os
import re
import signal
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")
_sandbox_child_pid: int | None = None
_termination_requested = False


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


def _assert_no_external_route() -> None:
    probe = socket.socket()
    probe.settimeout(0.1)
    try:
        if probe.connect_ex(("1.1.1.1", 80)) == 0:
            raise RuntimeError("isolated service wrapper unexpectedly has external network access")
    finally:
        probe.close()


def _sandbox_command(candidate_root: Path, module: str, info_fd: int) -> list[str]:
    database_path = Path(_require_environment("CT_DATABASE_PATH"))
    database_directory = database_path.parent
    database_directory.chmod(0o777)

    inner_database = f"/state/{database_path.name}"
    environment = {
        "CT_HOST": _require_environment("CT_HOST"),
        "CT_PORT": _require_environment("CT_PORT"),
        "CT_DATABASE_PATH": inner_database,
        "CT_CLOCK_INITIAL_MS": _require_environment("CT_CLOCK_INITIAL_MS"),
        "HOME": "/tmp",
        "PATH": "/work/.venv/bin:/usr/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
    }
    command = [
        "bwrap",
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
        str(database_directory),
        "/state",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
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
    for name, value in environment.items():
        command.extend(("--setenv", name, value))
    command.extend(("/work/.venv/bin/python", "-m", module))
    return command


def run() -> int:
    global _sandbox_child_pid

    if os.geteuid() != 0 or os.environ.get("CT_OUTER_NETNS") != "1":
        raise RuntimeError("isolated service wrapper must run as root inside the outer network namespace")
    _assert_no_external_route()

    candidate_root = Path(_require_environment("CT_CANDIDATE_ROOT")).resolve()
    if not candidate_root.is_dir() or candidate_root.is_relative_to(ROOT):
        raise RuntimeError("candidate root must exist outside the sealed evaluator repository")
    if not (candidate_root / ".venv" / "bin" / "python").is_file():
        raise RuntimeError("candidate root lacks its preprovisioned locked virtual environment")
    module = _require_environment("CT_CANDIDATE_MODULE")
    if MODULE_PATTERN.fullmatch(module) is None:
        raise RuntimeError("candidate module is not a dotted Python module name")

    info_read, info_write = os.pipe()
    process = subprocess.Popen(
        _sandbox_command(candidate_root, module, info_write),
        pass_fds=(info_write,),
        start_new_session=True,
    )
    os.close(info_write)
    with os.fdopen(info_read, encoding="utf-8") as info_stream:
        sandbox_info: Any = json.load(info_stream)
    if not isinstance(sandbox_info, dict) or not isinstance(sandbox_info.get("child-pid"), int):
        process.kill()
        raise RuntimeError(f"bubblewrap did not report the candidate PID: {sandbox_info!r}")
    _sandbox_child_pid = sandbox_info["child-pid"]
    if _termination_requested:
        _handle_sigterm(signal.SIGTERM, None)
    return process.wait()


def main() -> int:
    signal.signal(signal.SIGTERM, _handle_sigterm)
    try:
        return run()
    except Exception as exc:
        print(f"isolated service wrapper failed: {exc}", file=sys.stderr)
        return 125


if __name__ == "__main__":
    raise SystemExit(main())
