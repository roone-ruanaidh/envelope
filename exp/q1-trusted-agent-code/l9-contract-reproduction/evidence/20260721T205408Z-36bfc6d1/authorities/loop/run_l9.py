"""Select Q1/L9 and delegate to the frozen lease-workload runner."""

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
            loop_id="Q1/L9",
            root=LOOP_ROOT,
            intervention="structured_output_root_object",
            launcher=Path(__file__).resolve(),
            prior_loop_id="Q1/L8",
            prior_run_id="20260721T204010Z-87c2d9c9",
            prior_result_commit="744a13986555adcd93adf0f59102ffada9f871e5",
        )
    )
    return runner.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
