"""Select Q1/L2 and delegate to the frozen lease-workload runner."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


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


def main() -> int:
    runner = _load_workload_runner()
    runner.configure_loop(
        runner.LoopContext(
            loop_id="Q1/L2",
            root=LOOP_ROOT,
            intervention="hermetic_dispatch_test_state",
            launcher=Path(__file__).resolve(),
            prior_loop_id="Q1/L1",
            prior_run_id="20260721T062629Z-b09fbc7b",
            prior_result_commit="c069bc0a19b410562b30b78885efd3618fb41ec9",
        )
    )
    return runner.main()


if __name__ == "__main__":
    raise SystemExit(main())
