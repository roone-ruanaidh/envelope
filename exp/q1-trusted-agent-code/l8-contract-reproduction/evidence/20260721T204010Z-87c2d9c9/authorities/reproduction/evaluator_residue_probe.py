"""Report bounded Q1/L1 residue counts from inside the evaluator guest."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Sequence


RESOURCE_ROOT_PREFIXES = (
    "/tmp/q1-l1-authority-",
    "/tmp/q1-l1-evaluator-",
    "/tmp/q1-l1-isolated-command-",
    "/tmp/q1-l1-isolation-validation-",
    "/tmp/q1-l1-run-",
)
ENCODED_RESOURCE_ROOT_PREFIXES = tuple(
    os.fsencode(prefix) for prefix in RESOURCE_ROOT_PREFIXES
)
CGROUP_PREFIXES = ("q1-l1-authority-", "q1-l1-candidate-")
RUN_ROOT_PATTERN = re.compile(
    r"^/tmp/q1-l1-run-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$"
)
PROCESS_TOKENS = (
    b"/q1-l1-candidate-exec.py",
    b"Q1_L1_CANDIDATE_ENTRY_SOCKET=",
    b"Q1_L1_CANDIDATE_ROOT=",
    b"Q1_L1_DATABASE_PATH=",
    b"Q1_L1_OUTER_NETNS=",
)
REPORT_KEYS = ("cgroups", "loops", "mounts", "processes", "roots")
MAX_PROCESSES = 32_768
MAX_MOUNT_NAMESPACES = 4_096
MAX_PROCESS_BYTES = 1024 * 1024
MAX_MOUNTINFO_BYTES = 4 * 1024 * 1024
MAX_DIRECTORY_ENTRIES = 100_000


def _bounded_bytes(path: Path, maximum: int) -> bytes:
    with path.open("rb") as stream:
        value = stream.read(maximum + 1)
    if len(value) > maximum:
        raise RuntimeError("residue inspection input exceeded its bound")
    return value


def _ancestors() -> set[int]:
    ancestors: set[int] = set()
    current = os.getpid()
    while current > 0 and current not in ancestors:
        ancestors.add(current)
        try:
            status = _bounded_bytes(Path(f"/proc/{current}/status"), 64 * 1024)
            parent = next(
                line for line in status.splitlines() if line.startswith(b"PPid:")
            )
            current = int(parent.split()[1])
        except (FileNotFoundError, ProcessLookupError, StopIteration, ValueError):
            break
    return ancestors


def _payload_matches(
    command: bytes,
    environment: bytes,
    cwd: bytes,
    root: bytes,
    *,
    run_root: bytes | None,
) -> bool:
    values = (command, environment, cwd, root)
    return any(_resource_path_matches(value) for value in values) or (
        run_root is not None and any(run_root in value for value in values)
    ) or any(token in value for token in PROCESS_TOKENS for value in values)


def _resource_path_matches(value: bytes) -> bool:
    return any(prefix in value for prefix in ENCODED_RESOURCE_ROOT_PREFIXES)


def _mountinfo_matches(value: bytes, *, run_root: bytes | None) -> bool:
    return _resource_path_matches(value) or (
        run_root is not None and run_root in value
    )


def _count_prefixed_entries(
    root: Path, prefixes: tuple[str, ...], *, recursive: bool
) -> int:
    traversed = 0
    matched = 0
    if recursive:
        def walk_error(exc: OSError) -> None:
            raise RuntimeError("residue filesystem inventory failed") from exc

        for _directory, directories, files in os.walk(
            root,
            followlinks=False,
            onerror=walk_error,
        ):
            traversed += len(directories) + len(files)
            if traversed > MAX_DIRECTORY_ENTRIES:
                raise RuntimeError("residue filesystem inventory exceeded its bound")
            matched += sum(
                any(name.startswith(prefix) for prefix in prefixes)
                for name in (*directories, *files)
            )
    else:
        with os.scandir(root) as entries:
            for entry in entries:
                traversed += 1
                if traversed > MAX_DIRECTORY_ENTRIES:
                    raise RuntimeError("residue filesystem inventory exceeded its bound")
                if any(entry.name.startswith(prefix) for prefix in prefixes):
                    matched += 1
    return matched


def _readlink_bytes(path: Path) -> bytes:
    value = os.fsencode(os.readlink(path))
    if len(value) > MAX_PROCESS_BYTES:
        raise RuntimeError("residue inspection link exceeded its bound")
    return value


def inspect(run_root: str | None = None) -> dict[str, int]:
    if run_root is not None and RUN_ROOT_PATTERN.fullmatch(run_root) is None:
        raise ValueError("invalid evaluator run root")
    encoded_root = os.fsencode(run_root) if run_root is not None else None
    ancestors = _ancestors()
    process_entries = [
        entry
        for entry in Path("/proc").iterdir()
        if entry.name.isdigit() and int(entry.name) not in ancestors
    ]
    if len(process_entries) > MAX_PROCESSES:
        raise RuntimeError("residue process inventory exceeded its bound")

    process_matches = 0
    self_mount_namespace = _readlink_bytes(Path("/proc/self/ns/mnt"))
    self_mountinfo = _bounded_bytes(Path("/proc/self/mountinfo"), MAX_MOUNTINFO_BYTES)
    mount_matches = int(_mountinfo_matches(self_mountinfo, run_root=encoded_root))
    inspected_mount_namespaces: set[bytes] = {self_mount_namespace}
    for entry in process_entries:
        try:
            command = _bounded_bytes(entry / "cmdline", MAX_PROCESS_BYTES)
            environment = _bounded_bytes(entry / "environ", MAX_PROCESS_BYTES)
            cwd = _readlink_bytes(entry / "cwd")
            root = _readlink_bytes(entry / "root")
            mount_namespace = _readlink_bytes(entry / "ns" / "mnt")
        except (FileNotFoundError, ProcessLookupError):
            continue
        if _payload_matches(
            command,
            environment,
            cwd,
            root,
            run_root=encoded_root,
        ):
            process_matches += 1
        if mount_namespace not in inspected_mount_namespaces:
            if len(inspected_mount_namespaces) >= MAX_MOUNT_NAMESPACES:
                raise RuntimeError("residue mount-namespace inventory exceeded its bound")
            try:
                mountinfo = _bounded_bytes(entry / "mountinfo", MAX_MOUNTINFO_BYTES)
            except (FileNotFoundError, ProcessLookupError):
                continue
            inspected_mount_namespaces.add(mount_namespace)
            if _mountinfo_matches(mountinfo, run_root=encoded_root):
                mount_matches += 1

    roots = _count_prefixed_entries(
        Path("/tmp"),
        tuple(prefix.removeprefix("/tmp/") for prefix in RESOURCE_ROOT_PREFIXES),
        recursive=False,
    )
    cgroups = _count_prefixed_entries(
        Path("/sys/fs/cgroup"),
        CGROUP_PREFIXES,
        recursive=True,
    )
    loops = 0
    for backing in Path("/sys/block").glob("loop*/loop/backing_file"):
        try:
            value = _bounded_bytes(backing, MAX_PROCESS_BYTES)
        except (FileNotFoundError, ProcessLookupError):
            continue
        if _resource_path_matches(value) or (
            encoded_root is not None and encoded_root in value
        ):
            loops += 1
    return {
        "cgroups": cgroups,
        "loops": loops,
        "mounts": mount_matches,
        "processes": process_matches,
        "roots": roots,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root")
    args = parser.parse_args(argv)
    try:
        if os.geteuid() != 0:
            raise RuntimeError("evaluator residue inspection requires root")
        counts = inspect(args.run_root)
        report = {
            "counts": counts,
            "passed": not any(counts.values()),
            "version": 1,
        }
    except (OSError, RuntimeError, ValueError):
        print('{"inspection":"unavailable","passed":false,"version":1}')
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
