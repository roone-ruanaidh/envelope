"""Quiesce candidate processes and export one immutable declared snapshot."""

from __future__ import annotations

import argparse
import json
import os
import signal
import stat
import time
from pathlib import Path
from typing import Any, Sequence

from candidate_transfer import TransferError, export_candidate


class SnapshotError(RuntimeError):
    """The candidate workspace could not be frozen safely."""


RUNTIME_CONTROL_PLACEHOLDERS = (".agents", ".codex", "AGENTS.md")


def _status_value(pid: int, field: str) -> str | None:
    try:
        lines = Path(f"/proc/{pid}/status").read_text(encoding="utf-8").splitlines()
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        return None
    prefix = field + ":"
    return next((line[len(prefix) :].strip() for line in lines if line.startswith(prefix)), None)


def _ancestors() -> set[int]:
    ancestors: set[int] = set()
    pid = os.getpid()
    while pid > 0 and pid not in ancestors:
        ancestors.add(pid)
        parent = _status_value(pid, "PPid")
        if parent is None:
            break
        try:
            pid = int(parent)
        except ValueError:
            break
    return ancestors


def _user_processes(uid: int, excluded: set[int]) -> set[int]:
    processes: set[int] = set()
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid in excluded:
            continue
        raw_uids = _status_value(pid, "Uid")
        if raw_uids is None:
            continue
        try:
            uids = {int(value) for value in raw_uids.split()}
        except ValueError:
            continue
        if uid in uids:
            processes.add(pid)
    return processes


def _signal_all(pids: set[int], signum: int) -> None:
    for pid in pids:
        try:
            os.kill(pid, signum)
        except ProcessLookupError:
            pass


def _quiesce(uid: int) -> list[int]:
    excluded = _ancestors()
    observed = _user_processes(uid, excluded)
    _signal_all(observed, signal.SIGTERM)
    deadline = time.monotonic() + 0.5
    remaining = observed
    while time.monotonic() < deadline:
        remaining = _user_processes(uid, excluded)
        observed.update(remaining)
        if not remaining:
            return sorted(observed)
        _signal_all(remaining, signal.SIGTERM)
        time.sleep(0.02)
    deadline = time.monotonic() + 0.5
    while time.monotonic() < deadline:
        remaining = _user_processes(uid, excluded)
        observed.update(remaining)
        if not remaining:
            return sorted(observed)
        _signal_all(remaining, signal.SIGKILL)
        time.sleep(0.02)
    raise SnapshotError(f"candidate user still owns live processes after quiescence: {sorted(remaining)}")


def _remove_empty_runtime_controls(root: Path, uid: int) -> None:
    for name in RUNTIME_CONTROL_PLACEHOLDERS:
        path = root / name
        try:
            observed = path.lstat()
        except FileNotFoundError:
            continue
        if observed.st_uid != uid:
            raise SnapshotError(f"runtime control placeholder has the wrong owner: {name}")
        if name == "AGENTS.md":
            if (
                not stat.S_ISREG(observed.st_mode)
                or observed.st_nlink != 1
                or observed.st_size != 0
            ):
                raise SnapshotError(f"runtime control placeholder is not empty: {name}")
            path.unlink()
            continue
        if not stat.S_ISDIR(observed.st_mode):
            raise SnapshotError(f"runtime control placeholder is not an empty directory: {name}")
        with os.scandir(path) as entries:
            if next(entries, None) is not None:
                raise SnapshotError(
                    f"runtime control placeholder is not an empty directory: {name}"
                )
        path.rmdir()


def _export_owned_candidate(
    root: Path,
    archive: Path,
    manifest: Path,
    *,
    uid: int,
) -> None:
    try:
        export_candidate(root, archive, manifest, owner_uid=uid)
    except Exception:
        archive.unlink(missing_ok=True)
        manifest.unlink(missing_ok=True)
        raise


def snapshot(root: Path, archive: Path, manifest: Path, report: Path) -> dict[str, Any]:
    if os.geteuid() != 0:
        raise SnapshotError("candidate snapshot controller must run as root")
    root = root.resolve()
    root_stat = root.stat()
    if not root.is_dir() or root_stat.st_uid == 0:
        raise SnapshotError("candidate root must be an unprivileged user-owned directory")
    outputs = (archive, manifest, report)
    if len({os.path.abspath(path) for path in outputs}) != len(outputs):
        raise SnapshotError("candidate snapshot outputs must be distinct")
    if any(os.path.lexists(path) for path in outputs):
        raise SnapshotError("candidate snapshot outputs must be new paths")
    terminated = _quiesce(root_stat.st_uid)
    _remove_empty_runtime_controls(root, root_stat.st_uid)
    _export_owned_candidate(
        root,
        archive,
        manifest,
        uid=root_stat.st_uid,
    )
    value = {
        "archive": str(archive),
        "candidate_uid": root_stat.st_uid,
        "manifest": str(manifest),
        "quiesced": True,
        "terminated_process_count": len(terminated),
    }
    encoded = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    report_fd = os.open(
        report,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o644,
    )
    try:
        os.fchmod(report_fd, 0o644)
        with os.fdopen(report_fd, "wb", closefd=False) as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(report_fd)
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        value = snapshot(args.root, args.archive, args.manifest, args.report)
    except (OSError, SnapshotError, TransferError) as exc:
        print(json.dumps({"error": str(exc), "passed": False}, sort_keys=True))
        return 1
    print(json.dumps({**value, "passed": True}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
