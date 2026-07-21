"""Probe the candidate-authoring filesystem and command-network boundary."""

from __future__ import annotations

import json
import os
import socket
import subprocess
from pathlib import Path
from typing import Callable


workspace = Path.cwd().resolve()
home = Path.home().resolve()

assert workspace == home / "candidate"
# The reviewed Lima authority has no host mounts.  A guest-side assertion keeps
# that proof independent of a private host username or repository location.
assert not Path("/Users").exists()

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


def must_be_blocked(label: str, operation: Callable[[], object]) -> None:
    try:
        operation()
    except OSError:
        return
    raise AssertionError(f"sandbox permitted protected mutation: {label}")

for protected in (
    workspace / "AGENTS.md",
    workspace / ".git" / "config",
    workspace / ".codex" / "config.toml",
    workspace / "public" / "contract" / "openapi.v1.json",
    workspace / ".venv" / "pyvenv.cfg",
    home / "outside-control" / "secret.txt",
    home / ".codex" / "auth-boundary-sentinel",
):
    try:
        protected.write_text("boundary failure\n", encoding="utf-8")
    except OSError:
        pass
    else:
        raise AssertionError(f"sandbox permitted protected write: {protected}")

# Read-only path rules must protect directory entries as well as file content.
# Each operation uses a distinct authority so a broken boundary fails at the
# first mutation without masking a later probe.
must_be_blocked(
    "unlink public contract file",
    lambda: (workspace / "public" / "contract" / "semantics.v1.md").unlink(),
)
must_be_blocked(
    "rename Git authority directory",
    lambda: (workspace / ".git").rename(workspace / ".escaped-git"),
)
must_be_blocked(
    "rename public contract directory",
    lambda: (workspace / "public" / "contract").rename(workspace / ".escaped-contract"),
)
must_be_blocked(
    "rename virtual environment",
    lambda: (workspace / ".venv").rename(workspace / ".escaped-venv"),
)
must_be_blocked(
    "create Codex control directory",
    lambda: (workspace / ".codex").mkdir(),
)
must_be_blocked(
    "unlink authentication sentinel",
    lambda: (home / ".codex" / "auth-boundary-sentinel").unlink(),
)

replacement = workspace / ".replacement-source"
replacement.write_text("boundary failure\n", encoding="utf-8")
try:
    must_be_blocked(
        "replace public contract file",
        lambda: os.replace(
            replacement,
            workspace / "public" / "contract" / "mypy.v1.ini",
        ),
    )
finally:
    replacement.unlink(missing_ok=True)

try:
    (home / "outside-control" / "secret.txt").read_text(encoding="utf-8")
except OSError:
    pass
else:
    raise AssertionError("sandbox permitted read outside the candidate workspace")

try:
    (home / ".codex" / "auth-boundary-sentinel").read_text(encoding="utf-8")
except OSError:
    pass
else:
    raise AssertionError("sandbox permitted read from the Codex authentication directory")

try:
    privilege_probe = subprocess.run(
        ["sudo", "-n", "true"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
except OSError:
    pass
else:
    assert privilege_probe.returncode != 0, "sandbox permitted sudo privilege escalation"

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
            "home_codex_control": "unreadable_and_unwritable",
            "host_workspace": "absent",
            "outside_workspace": "unreadable_and_unwritable",
            "protected_candidate_paths": "read_only",
            "workspace": "writable",
            "privilege_escalation": "blocked",
        },
        sort_keys=True,
    )
)
