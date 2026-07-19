"""Probe the candidate-authoring filesystem and command-network boundary."""

from __future__ import annotations

import json
import socket
from pathlib import Path


workspace = Path.cwd().resolve()
home = Path.home().resolve()

assert workspace == home / "candidate"
assert not Path("/Users/engineer/ws").exists()
assert not Path(
    "/Users/engineer/ws/ev/exp/q1-trusted-agent-code/l1-contract-reproduction/evaluator"
).exists()

expected_public = {
    "mypy.v1.ini",
    "openapi.v1.json",
    "python-arm-requirements.v1.txt",
    "semantics.v1.md",
}
assert {path.name for path in (workspace / "public" / "contract").iterdir()} == expected_public

workspace_probe = workspace / ".workspace-write-probe"
workspace_probe.write_text("ok\n", encoding="utf-8")
workspace_probe.unlink()

for protected in (
    workspace / "public" / "contract" / "openapi.v1.json",
    workspace / ".venv" / "pyvenv.cfg",
    home / "outside-control" / "secret.txt",
):
    try:
        protected.write_text("boundary failure\n", encoding="utf-8")
    except OSError:
        pass
    else:
        raise AssertionError(f"sandbox permitted protected write: {protected}")

try:
    (home / "outside-control" / "secret.txt").read_text(encoding="utf-8")
except OSError:
    pass
else:
    raise AssertionError("sandbox permitted read outside the candidate workspace")

try:
    external = socket.socket()
    external.settimeout(0.25)
    assert external.connect_ex(("1.1.1.1", 80)) != 0
    external.close()
except OSError:
    # Linux Bubblewrap may deny socket creation before a connection is tried.
    pass

print(
    json.dumps(
        {
            "external_command_network": "blocked",
            "host_workspace": "absent",
            "outside_workspace": "unreadable_and_unwritable",
            "protected_candidate_paths": "read_only",
            "workspace": "writable",
        },
        sort_keys=True,
    )
)
