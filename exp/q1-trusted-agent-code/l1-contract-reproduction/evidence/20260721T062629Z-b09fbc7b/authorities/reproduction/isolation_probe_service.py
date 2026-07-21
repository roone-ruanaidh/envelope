"""Runtime assertions used only by the evaluator isolation preflight."""

from __future__ import annotations

import json
import os
import runpy
import socket
import sys
from pathlib import Path


def _write_blocked(path: Path) -> None:
    try:
        path.write_text("isolation failure\n", encoding="utf-8")
    except OSError:
        return
    path.unlink(missing_ok=True)
    raise RuntimeError(f"isolation unexpectedly allowed a persistent write: {path}")


def main() -> None:
    if len(sys.argv) != 2:
        raise RuntimeError("isolation probe requires the evaluator root argument")
    evaluator_root = Path(sys.argv[1])
    if evaluator_root.exists():
        raise RuntimeError("sealed evaluator source is visible inside the candidate sandbox")
    _write_blocked(Path("/work/isolation-write-probe"))
    _write_blocked(Path("/usr/isolation-write-probe"))

    temporary_probe = Path("/tmp/isolation-write-probe")
    temporary_probe.write_text("ephemeral\n", encoding="utf-8")
    temporary_probe.unlink()

    database = Path(os.environ["Q1_L1_DATABASE_PATH"])
    if database.parent != Path("/state"):
        raise RuntimeError("candidate database is not inside evaluator-owned state")
    state_probe = database.parent / "isolation-write-probe"
    state_probe.write_text("state\n", encoding="utf-8")
    state_probe.unlink()

    # The trusted launcher must have reported entry independently of any
    # candidate-visible pathname.  Deleting the bound pathname cannot retract
    # the datagram that was already delivered to the outer wrapper.
    Path("/state/.q1-l1-entry.sock").unlink(missing_ok=True)

    probe = socket.socket()
    probe.settimeout(0.1)
    try:
        if probe.connect_ex(("1.1.1.1", 80)) == 0:
            raise RuntimeError("candidate sandbox unexpectedly has an external route")
    except OSError:
        pass
    finally:
        probe.close()

    print(
        json.dumps(
            {
                "candidate_external_route": "blocked",
                "evaluator_source": "absent",
                "persistent_writes": "state_only",
                "work_mount": "read_only",
            },
            sort_keys=True,
        ),
        flush=True,
    )
    runpy.run_path("/work/service.py", run_name="__main__")


if __name__ == "__main__":
    main()
