"""Run one non-service candidate gate command inside the Q1/L1 isolation boundary."""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Sequence

from .candidate_exec import (
    CandidateResourceEnvelope,
    ENTRY_TOKEN,
    WritableStateEnvelope,
)


ROOT = Path(__file__).resolve().parents[1]
OUTER_COMPLETION_MARKER = "q1-l1-isolated-command-completed-v1"
TRUSTED_MODULE_RUNNER = (
    'import runpy,sys;sys.path.insert(0,".");'
    'module=sys.argv.pop(1);runpy.run_module(module,run_name="__main__")'
)


def _validate_root(candidate_root: Path) -> Path:
    candidate_root = candidate_root.resolve()
    if (
        not candidate_root.is_dir()
        or candidate_root == ROOT
        or candidate_root.is_relative_to(ROOT)
        or ROOT.is_relative_to(candidate_root)
    ):
        raise RuntimeError("candidate root and evaluator source tree must be disjoint")
    if not (candidate_root / ".venv" / "bin" / "python").is_file():
        raise RuntimeError("candidate root lacks its clean locked virtual environment")
    return candidate_root


def _assert_no_external_route() -> None:
    probe = socket.socket()
    probe.settimeout(0.1)
    try:
        if probe.connect_ex(("1.1.1.1", 80)) == 0:
            raise RuntimeError("isolated command wrapper unexpectedly has external network access")
    finally:
        probe.close()


def _inside(candidate_root: Path, command: list[str]) -> int:
    if os.geteuid() != 0 or os.environ.get("Q1_L1_OUTER_NETNS") != "1":
        raise RuntimeError("isolated command wrapper must run as root inside the outer netns")
    print("q1-l1-isolated-command-entered", file=sys.stderr, flush=True)
    subprocess.run(["/usr/sbin/ip", "link", "set", "lo", "up"], check=True)
    _assert_no_external_route()
    candidate_root = _validate_root(candidate_root)
    with tempfile.TemporaryDirectory(prefix="q1-l1-isolated-command-") as temporary:
        control_directory = Path(temporary)
        with WritableStateEnvelope(control_directory, persistent=False) as writable:
            entry_path = writable.state / "entry.sock"
            entry_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            entry_socket.bind(str(entry_path))
            entry_path.chmod(0o777)
            entry_socket.setblocking(False)
            sandbox = [
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
                str(writable.state),
                "/q1-l1-state",
                "--proc",
                "/proc",
                "--dev",
                "/dev",
                "--bind",
                str(writable.temporary),
                "/tmp",
                "--unshare-user",
                "--unshare-pid",
                "--unshare-ipc",
                "--unshare-uts",
                "--unshare-cgroup-try",
                "--disable-userns",
                "--die-with-parent",
                "--as-pid-1",
                "--uid",
                "65534",
                "--gid",
                "65534",
                "--chdir",
                "/work",
                "--clearenv",
                "--setenv",
                "Q1_L1_CANDIDATE_ENTRY_SOCKET",
                "/q1-l1-state/entry.sock",
                "--setenv",
                "HOME",
                "/tmp",
                "--setenv",
                "MYPY_CACHE_DIR",
                "/tmp/mypy-cache",
                "--setenv",
                "PATH",
                "/work/.venv/bin:/usr/bin",
                "--setenv",
                "PYTHONDONTWRITEBYTECODE",
                "1",
                "--setenv",
                "PYTHONNOUSERSITE",
                "1",
                "--setenv",
                "PYTHONSAFEPATH",
                "1",
                "--ro-bind",
                str(ROOT / "evaluator" / "candidate_exec.py"),
                "/q1-l1-candidate-exec.py",
                "--",
                "/usr/bin/python3",
                "/q1-l1-candidate-exec.py",
                "--",
                *command,
            ]
            try:
                with CandidateResourceEnvelope() as resources:
                    completed = subprocess.run(
                        sandbox,
                        check=False,
                        preexec_fn=resources.enter_child,
                    )
                    try:
                        entered = entry_socket.recv(len(ENTRY_TOKEN) + 1) == ENTRY_TOKEN
                    except BlockingIOError:
                        entered = False
            finally:
                entry_socket.close()
                entry_path.unlink(missing_ok=True)
    return completed.returncode if entered and completed.returncode != 125 else 125


def _enter(candidate_root: Path, command: list[str]) -> int:
    environment = {
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
    }
    environment["Q1_L1_OUTER_NETNS"] = "1"
    prefix = ["/usr/bin/sudo"]
    temporary_root = os.environ.get("TMPDIR")
    if temporary_root:
        resolved_temporary = Path(temporary_root).resolve()
        if (
            not resolved_temporary.is_dir()
            or resolved_temporary == candidate_root
            or resolved_temporary.is_relative_to(candidate_root)
            or resolved_temporary == ROOT
            or resolved_temporary.is_relative_to(ROOT)
        ):
            raise RuntimeError("configured isolated-command TMPDIR is not a safe directory")
        prefix.extend(("/usr/bin/env", f"TMPDIR={resolved_temporary}"))
    process = subprocess.Popen(
        [
            *prefix,
            "/usr/bin/unshare",
            "--net",
            "--fork",
            "/usr/bin/env",
            "Q1_L1_OUTER_NETNS=1",
            sys.executable,
            "-B",
            "-I",
            "-c",
            TRUSTED_MODULE_RUNNER,
            "evaluator.isolated_command",
            "--inside-netns",
            "--candidate-root",
            str(candidate_root.resolve()),
            "--",
            *command,
        ],
        cwd=ROOT,
        env=environment,
        stderr=subprocess.PIPE,
    )
    if process.stderr is None:  # pragma: no cover - guaranteed by PIPE
        process.kill()
        return 125
    marker = b"q1-l1-isolated-command-entered\n"
    prefix = process.stderr.read(len(marker))
    entered = prefix == marker
    if not entered:
        sys.stderr.buffer.write(prefix)
        sys.stderr.buffer.flush()
    while chunk := process.stderr.read(8192):
        sys.stderr.buffer.write(chunk)
        sys.stderr.buffer.flush()
    return_code = process.wait()
    return return_code if entered else 125


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--inside-netns", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command or not command[0] or any("\0" in argument for argument in command):
        print("isolated candidate command must be a nonempty NUL-free argv", file=sys.stderr)
        return 2
    try:
        candidate_root = _validate_root(args.candidate_root)
        if args.inside_netns:
            return _inside(candidate_root, command)
        return_code = _enter(candidate_root, command)
        print(OUTER_COMPLETION_MARKER, file=sys.stderr, flush=True)
        return return_code
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"isolated command wrapper failed: {exc}", file=sys.stderr)
        return 125


if __name__ == "__main__":
    raise SystemExit(main())
