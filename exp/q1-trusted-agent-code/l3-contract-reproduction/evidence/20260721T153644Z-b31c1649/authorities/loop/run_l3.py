"""Select Q1/L3 and delegate to the frozen lease-workload runner."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Sequence


LOOP_ROOT = Path(__file__).resolve().parents[1]
WORKLOAD_RUNNER = (
    LOOP_ROOT.parent
    / "l1-contract-reproduction"
    / "reproduction"
    / "run_l1.py"
)
QUALIFICATION_ROOT = LOOP_ROOT / "build" / "candidate-creation-qualification"


def _load_workload_runner():
    spec = importlib.util.spec_from_file_location("q1_lease_workload_runner", WORKLOAD_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("frozen workload runner cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _qualification_commit(argv: Sequence[str]) -> str:
    parser = argparse.ArgumentParser(
        description="Qualify one candidate disk creation without starting the VM."
    )
    parser.add_argument("command", choices=("qualify",))
    parser.add_argument("--contract-commit", required=True)
    return parser.parse_args(argv).contract_commit


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    runner = _load_workload_runner()
    runner.configure_loop(
        runner.LoopContext(
            loop_id="Q1/L3",
            root=LOOP_ROOT,
            intervention="parent_bounded_stream_capture",
            launcher=Path(__file__).resolve(),
            prior_loop_id="Q1/L2",
            prior_run_id="20260721T071826Z-10ec801b",
            prior_result_commit="de0d74a7effaa065cdd400519af17cf0fc859e61",
            candidate_qualification_root=QUALIFICATION_ROOT,
        )
    )
    if arguments and arguments[0] == "qualify":
        try:
            return runner.qualify_candidate_creation(
                _qualification_commit(arguments),
                QUALIFICATION_ROOT,
            )
        except (OSError, ValueError, RuntimeError) as exc:
            print(json.dumps({"error": str(exc)}, sort_keys=True), file=sys.stderr)
            return 2
    return runner.main(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
