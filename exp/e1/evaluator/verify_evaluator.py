"""Validate the evaluator against its behavioral reference and fault bank."""

from __future__ import annotations

import argparse
import json
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from . import CONTRACT_VERSION, EVALUATOR_VERSION
from .acceptance import run_acceptance


DEFAULT_FIXTURE_COMMAND = "python3 -m evaluator.fixtures.service"

EXPECTED_MUTANTS: dict[str, tuple[str, str, str]] = {
    "schema_extra": ("protocol", "protocol_and_schema", "undeclared properties"),
    "drip_response": (
        "protocol",
        "protocol_and_schema",
        "absolute request deadline",
    ),
    "non_idempotent": ("idempotency", "idempotent_submission", "expected HTTP 200, got 201"),
    "racy_idempotency": ("idempotency", "concurrent_idempotent_replay", "concurrent replay created"),
    "stale_replay": ("idempotency", "idempotent_submission", "cached pending representation"),
    "wall_clock_expiry": (
        "temporal",
        "frozen_clock_and_ttl_boundary",
        "wall time expired a lease",
    ),
    "exclusive_expiry": ("temporal", "frozen_clock_and_ttl_boundary", "claim exactly at expiry"),
    "renewal_from_expiry": ("temporal", "renewal_from_current_time", "current clock time"),
    "stale_authority": ("authority", "stale_and_cross_job_authority", "stale-holder heartbeat"),
    "double_claim": ("concurrency", "concurrent_single_claim", "one pending job produced"),
    "volatile": ("persistence", "graceful_and_abrupt_persistence", "after graceful restart"),
    "abrupt_volatile": ("persistence", "graceful_and_abrupt_persistence", "after abrupt restart"),
    "persistent_clock": ("persistence", "graceful_and_abrupt_persistence", "restore the injected clock"),
    "signal_exit": ("persistence", "graceful_and_abrupt_persistence", "did not exit cleanly"),
    "ignore_sigterm": ("persistence", "graceful_and_abrupt_persistence", "did not exit cleanly"),
}


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _summarize_acceptance(report: dict[str, Any]) -> dict[str, Any]:
    failures = [test for test in report.get("tests", []) if not test.get("passed", False)]
    return {
        "passed": report.get("passed", False),
        "duration_ms": report.get("duration_ms"),
        "startup_error": report.get("startup_error"),
        "failed_tests": failures,
        "failed_layers": sorted({test["layer"] for test in failures}),
        "layers": report.get("layers", {}),
        "shutdowns": report.get("shutdowns", []),
        "service_log_tail": report.get("service_log_tail", "")[-2_048:],
    }


def _run_fixture(command: str, mode: str, *, fail_fast: bool) -> dict[str, Any]:
    port = _free_loopback_port()
    report = run_acceptance(
        base_url=f"http://127.0.0.1:{port}",
        service_command=command,
        fail_fast=fail_fast,
        extra_env={"CT_FIXTURE_MODE": mode},
    )
    return _summarize_acceptance(report)


def verify_bank(command: str, reference_repeats: int) -> dict[str, Any]:
    references: list[dict[str, Any]] = []
    for _index in range(reference_repeats):
        references.append(_run_fixture(command, "reference", fail_fast=False))

    mutants: dict[str, dict[str, Any]] = {}
    for mode, (expected_layer, expected_test, expected_detail) in EXPECTED_MUTANTS.items():
        observed = _run_fixture(command, mode, fail_fast=True)
        failures = observed["failed_tests"]
        correctly_rejected = (
            not observed["passed"]
            and observed["startup_error"] is None
            and len(failures) == 1
            and failures[0]["layer"] == expected_layer
            and failures[0]["name"] == expected_test
            and expected_detail in (failures[0].get("detail") or "")
        )
        mutants[mode] = {
            "expected_disposition": "reject",
            "expected_layer": expected_layer,
            "expected_test": expected_test,
            "expected_detail": expected_detail,
            "correctly_rejected": correctly_rejected,
            "acceptance": observed,
        }

    reference_ok = all(run["passed"] for run in references)
    mutants_ok = all(item["correctly_rejected"] for item in mutants.values())
    return {
        "evaluator_version": EVALUATOR_VERSION,
        "contract_version": CONTRACT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fixture_command": command,
        "passed": reference_ok and mutants_ok,
        "reference": {
            "expected_disposition": "accept",
            "repeat_count": reference_repeats,
            "all_accepted": reference_ok,
            "runs": references,
        },
        "mutants": mutants,
        "summary": {
            "reference_runs_accepted": sum(run["passed"] for run in references),
            "reference_runs_total": reference_repeats,
            "mutants_rejected_as_expected": sum(
                item["correctly_rejected"] for item in mutants.values()
            ),
            "mutants_total": len(mutants),
        },
    }


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--service-command",
        default=DEFAULT_FIXTURE_COMMAND,
        help="foreground fixture command (default: %(default)s)",
    )
    parser.add_argument(
        "--reference-repeats",
        type=int,
        default=2,
        help="number of independent conforming-fixture runs (default: %(default)s)",
    )
    parser.add_argument("--json-report", type=Path, help="also write the bank report to this path")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.reference_repeats < 1:
        print("--reference-repeats must be at least one", file=sys.stderr)
        return 2
    report = verify_bank(args.service_command, args.reference_repeats)
    if args.json_report is not None:
        _write_report(args.json_report, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
