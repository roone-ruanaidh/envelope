"""Select Q1/L4 and delegate to the frozen lease-workload runner."""

from __future__ import annotations

import importlib.util
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
QUALIFICATION_ROOT = LOOP_ROOT / "build" / "candidate-boundary-qualification"


def _load_workload_runner():
    spec = importlib.util.spec_from_file_location("q1_lease_workload_runner", WORKLOAD_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("frozen workload runner cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main(argv: Sequence[str] | None = None) -> int:
    runner = _load_workload_runner()
    runner.configure_loop(
        runner.LoopContext(
            loop_id="Q1/L4",
            root=LOOP_ROOT,
            intervention="qualified_candidate_boundary",
            launcher=Path(__file__).resolve(),
            prior_loop_id="Q1/L3",
            prior_run_id="20260721T153644Z-b31c1649",
            prior_result_commit="42b4c48880bc98358dbad84e3b71e7d06b416211",
            candidate_qualification_root=QUALIFICATION_ROOT,
        )
    )
    return runner.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
