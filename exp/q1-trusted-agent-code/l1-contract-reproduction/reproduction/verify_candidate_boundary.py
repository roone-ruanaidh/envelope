"""Validate a provisioned Q1/L1 candidate boundary and write a safe report."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PROBE = {
    "external_command_network": "blocked",
    "home_codex_control": "unreadable_and_unwritable",
    "host_workspace": "absent",
    "outside_workspace": "unreadable_and_unwritable",
    "privilege_escalation": "blocked",
    "protected_candidate_paths": "read_only",
    "workspace": "writable",
}
CONTROL_AUTHORITY_FILES = (
    "agent-completion.schema.json",
    "bootstrap-candidate-lima.sh",
    "candidate-apt-packages.txt",
    "candidate-codex-config.toml",
    "candidate-codex-requirements.toml",
    "candidate-lima.yaml",
    "candidate_snapshot.py",
    "candidate_transfer.py",
    "candidate_boundary_probe.py",
    "prepare-candidate-lima.sh",
    "verify_candidate_boundary.py",
)
CONTRACT_FILES = (
    "mypy.v1.ini",
    "openapi.v1.json",
    "python-arm-requirements.v1.txt",
    "semantics.v1.md",
)
AUTHORITY_FILES = (
    *CONTROL_AUTHORITY_FILES,
    *(f"public/contract/{name}" for name in CONTRACT_FILES),
)
INSTALLED_AUTHORITIES = {
    "candidate_boundary_probe.py": "candidate_boundary_probe.py",
    "/etc/codex/config.toml": "candidate-codex-config.toml",
    "/etc/codex/q1-l1-agent-completion.schema.json": "agent-completion.schema.json",
    "/etc/codex/requirements.toml": "candidate-codex-requirements.toml",
    "/usr/local/lib/q1-l1/candidate_snapshot.py": "candidate_snapshot.py",
    "/usr/local/lib/q1-l1/candidate_transfer.py": "candidate_transfer.py",
    **{
        f"public/contract/{name}": f"public/contract/{name}"
        for name in CONTRACT_FILES
    },
}
HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
INSTALLED_HASH_COMMAND = (
    'sha256sum "$HOME/candidate/.boundary_probe.py" '
    "/etc/codex/config.toml /etc/codex/q1-l1-agent-completion.schema.json "
    "/etc/codex/requirements.toml "
    "/usr/local/lib/q1-l1/candidate_snapshot.py "
    "/usr/local/lib/q1-l1/candidate_transfer.py "
    + " ".join(
        f'"$HOME/candidate/public/contract/{name}"' for name in CONTRACT_FILES
    )
)
VENV_PROVENANCE_COMMAND = (
    '"$HOME/candidate/.venv/bin/python" -c \'import hashlib,importlib.metadata,json,'
    'platform,sys; print(json.dumps({"packages":sorted((d.metadata["Name"],d.version) '
    'for d in importlib.metadata.distributions()),"python_sha256":hashlib.sha256('
    'open(sys.executable,"rb").read()).hexdigest(),"python_version":platform.python_version()},'
    'sort_keys=True))\''
)
PROBE_COMMAND = (
    'cd "$HOME/candidate" && exec codex sandbox --include-managed-config '
    "--permissions-profile q1_l1 -- python3 .boundary_probe.py"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _authority_hashes(root: Path = ROOT) -> dict[str, str]:
    reproduction = root / "reproduction"
    return {
        name: _sha256(root / name if name.startswith("public/") else reproduction / name)
        for name in AUTHORITY_FILES
    }


def _lima_authority(root: Path = ROOT) -> dict[str, Any]:
    text = (root / "reproduction" / "candidate-lima.yaml").read_text(encoding="utf-8")
    digest = re.findall(r"(?m)^\s+digest:\s+(sha256:[0-9a-f]{64})\s*$", text)
    location = re.findall(r"(?m)^\s+- location:\s+(\S+)\s*$", text)
    if len(digest) != 1 or len(location) != 1 or not re.search(r"(?m)^mounts:\s*\[\]\s*$", text):
        raise ValueError("candidate Lima authority is not the expected no-mount pinned image")
    return {
        "configured_image_digest": digest[0],
        "configured_image_location": location[0],
        "configured_mounts": [],
    }


def _run_lima(instance: str, command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["limactl", "shell", "--tty=false", instance, "sh", "-lc", command],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _installed_key(path: str) -> str | None:
    if path in INSTALLED_AUTHORITIES:
        return path
    if path.endswith("/candidate/.boundary_probe.py"):
        return "candidate_boundary_probe.py"
    for name in CONTRACT_FILES:
        key = f"public/contract/{name}"
        if path.endswith(f"/candidate/{key}"):
            return key
    return None


def _normalized_package_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _required_packages(root: Path = ROOT) -> dict[str, str]:
    required: dict[str, str] = {}
    for line in (root / "public" / "contract" / "python-arm-requirements.v1.txt").read_text(
        encoding="utf-8"
    ).splitlines():
        fields = line.split("==", 1)
        if len(fields) != 2 or not all(fields):
            raise ValueError("candidate requirement lock is invalid")
        name = _normalized_package_name(fields[0])
        if name in required:
            raise ValueError("candidate requirement lock contains duplicate packages")
        required[name] = fields[1]
    return required


def _venv_provenance(stdout: str, root: Path = ROOT) -> dict[str, Any] | None:
    try:
        value = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    if (
        not isinstance(value, dict)
        or set(value) != {"packages", "python_sha256", "python_version"}
        or value.get("python_version") != "3.14.4"
        or not isinstance(value.get("python_sha256"), str)
        or HASH_PATTERN.fullmatch(value["python_sha256"]) is None
        or not isinstance(value.get("packages"), list)
    ):
        return None
    packages: dict[str, str] = {}
    for item in value["packages"]:
        if (
            not isinstance(item, list)
            or len(item) != 2
            or not all(isinstance(part, str) and part for part in item)
        ):
            return None
        name = _normalized_package_name(item[0])
        if name in packages:
            return None
        packages[name] = item[1]
    required = _required_packages(root)
    if any(packages.get(name) != version for name, version in required.items()):
        return None
    if set(packages) != set(required) | {"pip"}:
        return None
    return {
        "packages": dict(sorted(packages.items())),
        "python_sha256": value["python_sha256"],
        "python_version": value["python_version"],
    }


def _installed_hashes(stdout: str) -> dict[str, str] | None:
    observed: dict[str, str] = {}
    lines = stdout.splitlines()
    if len(lines) != len(INSTALLED_AUTHORITIES):
        return None
    for line in lines:
        fields = line.split(maxsplit=1)
        if len(fields) != 2 or HASH_PATTERN.fullmatch(fields[0]) is None:
            return None
        key = _installed_key(fields[1])
        if key is None or key in observed:
            return None
        observed[key] = fields[0]
    if set(observed) != set(INSTALLED_AUTHORITIES):
        return None
    return {
        authority: observed[installed]
        for installed, authority in INSTALLED_AUTHORITIES.items()
    }


def _probe_result(stdout: str) -> tuple[dict[str, str] | None, str | None]:
    try:
        value = json.loads(stdout)
    except json.JSONDecodeError:
        return None, "probe_output_invalid"
    if not isinstance(value, dict) or set(value) != set(EXPECTED_PROBE):
        return None, "probe_schema_invalid"
    if any(not isinstance(item, str) for item in value.values()):
        return None, "probe_schema_invalid"
    if value != EXPECTED_PROBE:
        return None, "probe_result_mismatch"
    return EXPECTED_PROBE.copy(), None


def _report(
    authority_hashes: dict[str, str],
    *,
    lima_authority: dict[str, Any] | None,
    failure: str | None,
    installed_hashes: dict[str, str] | None,
    candidate_runtime: dict[str, Any] | None,
    probe: dict[str, str] | None,
) -> dict[str, Any]:
    return {
        "failure": failure,
        "passed": failure is None,
        "probe": probe,
        "provenance": {
            "authority_sha256": authority_hashes,
            "candidate_runtime": candidate_runtime,
            "codex_cli_required": "codex-cli 0.142.5",
            "lima": lima_authority,
            "installed_sha256": installed_hashes,
            "permissions_profile": "q1_l1",
        },
        "schema_version": 1,
    }


def verify(instance: str, root: Path = ROOT) -> dict[str, Any]:
    authority = _authority_hashes(root)
    lima_authority = _lima_authority(root)
    installed_result = _run_lima(instance, INSTALLED_HASH_COMMAND)
    if installed_result.returncode != 0:
        return _report(
            authority,
            lima_authority=lima_authority,
            failure="installed_provenance_command_failed",
            installed_hashes=None,
            candidate_runtime=None,
            probe=None,
        )
    installed = _installed_hashes(installed_result.stdout)
    if installed is None:
        return _report(
            authority,
            lima_authority=lima_authority,
            failure="installed_provenance_invalid",
            installed_hashes=None,
            candidate_runtime=None,
            probe=None,
        )
    if any(installed[name] != authority[name] for name in installed):
        return _report(
            authority,
            lima_authority=lima_authority,
            failure="installed_authority_mismatch",
            installed_hashes=installed,
            candidate_runtime=None,
            probe=None,
        )

    runtime_result = _run_lima(instance, VENV_PROVENANCE_COMMAND)
    runtime = (
        _venv_provenance(runtime_result.stdout, root)
        if runtime_result.returncode == 0
        else None
    )
    if runtime is None:
        return _report(
            authority,
            lima_authority=lima_authority,
            failure="candidate_runtime_provenance_invalid",
            installed_hashes=installed,
            candidate_runtime=None,
            probe=None,
        )

    probe_result = _run_lima(instance, PROBE_COMMAND)
    probe, failure = _probe_result(probe_result.stdout)
    if probe_result.returncode != 0:
        failure = "probe_command_failed"
        probe = None
    return _report(
        authority,
        lima_authority=lima_authority,
        failure=failure,
        installed_hashes=installed,
        candidate_runtime=runtime,
        probe=probe,
    )


def _write_report(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    parent_metadata = path.parent.lstat()
    if stat.S_ISLNK(parent_metadata.st_mode) or not stat.S_ISDIR(parent_metadata.st_mode):
        raise OSError("report parent is not a real directory")
    encoded = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    temporary_name = f".{path.name}.{uuid.uuid4().hex}.tmp"
    directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    descriptor: int | None = None
    try:
        descriptor = os.open(
            temporary_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory_fd,
        )
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.close(descriptor)
        descriptor = None
        os.rename(
            temporary_name,
            path.name,
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
        )
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            os.unlink(temporary_name, dir_fd=directory_fd)
        except FileNotFoundError:
            pass
        os.close(directory_fd)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", required=True)
    parser.add_argument("--json-report", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report = verify(args.instance)
    except (OSError, ValueError):
        try:
            authority = _authority_hashes()
        except OSError:
            authority = {}
        report = _report(
            authority,
            lima_authority=None,
            failure="boundary_validation_unavailable",
            installed_hashes=None,
            candidate_runtime=None,
            probe=None,
        )
    _write_report(args.json_report, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
