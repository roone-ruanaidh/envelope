"""Run Q1/L1 behavioral acceptance in the isolated Linux boundary."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import signal
import subprocess
import sys
from pathlib import Path
from typing import Sequence, cast

from .acceptance import run_acceptance


ROOT = Path(__file__).resolve().parents[1]
COMPLETION_KEYS = {"service_command", "status"}
CONTROL_DOCUMENT_MAX_BYTES = 1024 * 1024
ARGV_MAX_ENTRIES = 128
ARGV_MAX_ENTRY_BYTES = 8 * 1024
ARGV_MAX_AGGREGATE_BYTES = 64 * 1024
TRUSTED_MODULE_RUNNER = (
    'import runpy,sys;sys.path.insert(0,".");'
    'module=sys.argv.pop(1);runpy.run_module(module,run_name="__main__")'
)


def _parse_service_command(value: object) -> list[str]:
    if not isinstance(value, list) or not value or len(value) > ARGV_MAX_ENTRIES:
        raise ValueError("service_command must be a nonempty JSON array")
    if not all(isinstance(argument, str) and "\0" not in argument for argument in value):
        raise ValueError("every service_command argument must be a NUL-free string")
    if not value[0]:
        raise ValueError("service_command executable must not be empty")
    aggregate = 0
    for argument in value:
        try:
            encoded = argument.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError("service_command arguments must be valid UTF-8") from exc
        if len(encoded) > ARGV_MAX_ENTRY_BYTES:
            raise ValueError("service_command argument exceeds its byte limit")
        aggregate += len(encoded) + 1
    if aggregate > ARGV_MAX_AGGREGATE_BYTES:
        raise ValueError("service_command exceeds its aggregate byte limit")
    return cast(list[str], value)


def load_completion(path: Path) -> list[str]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > CONTROL_DOCUMENT_MAX_BYTES:
        raise ValueError("agent completion is not a bounded regular file")
    encoded = path.read_bytes()
    if len(encoded) > CONTROL_DOCUMENT_MAX_BYTES:
        raise ValueError("agent completion exceeds its byte limit")
    value = json.loads(encoded.decode("utf-8"))
    if not isinstance(value, dict) or set(value) != COMPLETION_KEYS:
        raise ValueError("agent completion must contain exactly status and service_command")
    if value["status"] != "declared_complete":
        raise ValueError("agent did not declare completion")
    return _parse_service_command(value["service_command"])


def _validate_candidate_root(candidate_root: Path) -> Path:
    candidate_root = candidate_root.resolve()
    if not candidate_root.is_dir():
        raise ValueError("candidate root must exist")
    if candidate_root == ROOT or candidate_root.is_relative_to(ROOT) or ROOT.is_relative_to(
        candidate_root
    ):
        raise ValueError("candidate root and evaluator source tree must be disjoint")
    if not (candidate_root / ".venv" / "bin" / "python").is_file():
        raise ValueError("candidate root lacks its clean locked virtual environment")
    return candidate_root


def _inside_network_namespace(args: argparse.Namespace) -> int:
    subprocess.run(["/usr/sbin/ip", "link", "set", "lo", "up"], check=True)
    candidate_root = _validate_candidate_root(args.candidate_root)
    if args.candidate_argv_json is None:
        raise ValueError("internal candidate argv transport is missing")
    service_command = _parse_service_command(json.loads(args.candidate_argv_json))
    os.environ.update(
        {
            "Q1_L1_OUTER_NETNS": "1",
            "Q1_L1_CANDIDATE_ROOT": str(candidate_root),
            "Q1_L1_CANDIDATE_ARGV_JSON": json.dumps(service_command, separators=(",", ":")),
        }
    )
    report = run_acceptance(
        base_url=args.base_url,
        service_command=" ".join(
            shlex.quote(argument)
            for argument in (
                sys.executable,
                "-B",
                "-I",
                "-c",
                TRUSTED_MODULE_RUNNER,
                "evaluator.isolated_service",
            )
        ),
        force_stop_signal=signal.SIGUSR1,
        isolation_wrapper=True,
    )
    report["candidate_service_command"] = service_command
    report["failure_class"] = (
        None
        if report["passed"]
        else "isolation_failure"
        if report.get("infrastructure_failure")
        else "candidate_failure"
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


def _enter_network_namespace(args: argparse.Namespace) -> int:
    candidate_root = _validate_candidate_root(args.candidate_root)
    if args.candidate_completion is None:
        raise ValueError("--candidate-completion is required")
    service_command = load_completion(args.candidate_completion)
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
            raise ValueError("configured rerun TMPDIR is not a safe directory")
        prefix.extend(("/usr/bin/env", f"TMPDIR={resolved_temporary}"))
    command = [
        *prefix,
        "/usr/bin/unshare",
        "--net",
        "--fork",
        sys.executable,
        "-B",
        "-I",
        "-c",
        TRUSTED_MODULE_RUNNER,
        "evaluator.rerun",
        "--inside-netns",
        "--candidate-root",
        str(candidate_root),
        "--candidate-argv-json",
        json.dumps(service_command, separators=(",", ":")),
        "--base-url",
        args.base_url,
        "--report",
        str(args.report.resolve()),
    ]
    return subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        env={
            "LANG": "C",
            "LC_ALL": "C",
            "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
        },
    ).returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--candidate-completion", type=Path)
    parser.add_argument("--base-url", default="http://127.0.0.1:18766")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--inside-netns", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--candidate-argv-json", help=argparse.SUPPRESS)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return _inside_network_namespace(args) if args.inside_netns else _enter_network_namespace(args)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(json.dumps({"passed": False, "fatal_error": str(exc)}, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
