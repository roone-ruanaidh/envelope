"""Run L1 behavioral acceptance in the isolated Linux boundary."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from .acceptance import run_acceptance


ROOT = Path(__file__).resolve().parents[1]


def _inside_network_namespace(args: argparse.Namespace) -> int:
    subprocess.run(["ip", "link", "set", "lo", "up"], check=True)
    candidate_root = args.candidate_root.resolve()
    os.environ.update(
        {
            "CT_OUTER_NETNS": "1",
            "CT_CANDIDATE_ROOT": str(candidate_root),
            "CT_CANDIDATE_MODULE": args.candidate_module,
        }
    )
    report = run_acceptance(
        base_url=args.base_url,
        service_command="python3 -m evaluator.isolated_service",
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


def _enter_network_namespace(args: argparse.Namespace) -> int:
    command = [
        "sudo",
        "unshare",
        "--net",
        "--fork",
        sys.executable,
        "-m",
        "evaluator.rerun",
        "--inside-netns",
        "--candidate-root",
        str(args.candidate_root.resolve()),
        "--candidate-module",
        args.candidate_module,
        "--base-url",
        args.base_url,
        "--report",
        str(args.report.resolve()),
    ]
    return subprocess.run(command, cwd=ROOT, check=False).returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--candidate-module", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:18766")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--inside-netns", action="store_true", help=argparse.SUPPRESS)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return _inside_network_namespace(args) if args.inside_netns else _enter_network_namespace(args)
    except (OSError, RuntimeError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(json.dumps({"passed": False, "fatal_error": str(exc)}, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
