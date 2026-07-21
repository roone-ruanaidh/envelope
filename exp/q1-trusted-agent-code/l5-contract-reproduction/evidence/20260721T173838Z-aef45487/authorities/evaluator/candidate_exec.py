"""Run candidate argv while preserving exit 125 for the outer isolation wrapper."""

from __future__ import annotations

import errno
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Sequence


_candidate: subprocess.Popen[bytes] | None = None
ENTRY_SOCKET_ENV = "Q1_L1_CANDIDATE_ENTRY_SOCKET"
ENTRY_TOKEN = b"q1-l1-candidate-entered-v1"
FOREGROUND_VIOLATION_EXIT = 126
CPU_MAX = "400000 100000"
MEMORY_MAX_BYTES = 4 * 1024**3
MEMORY_SWAP_MAX_BYTES = 0
MEMORY_OOM_GROUP = 1
PIDS_MAX = 256
WRITABLE_STATE_BYTES = 1024**3
CGROUP_ROOT = Path("/sys/fs/cgroup")


class ResourceEnvelopeError(RuntimeError):
    """The trusted candidate resource boundary could not be enforced."""


def _write_control(path: Path, value: str) -> None:
    with path.open("w", encoding="ascii") as stream:
        stream.write(value)


def _key_values(path: Path) -> dict[str, int]:
    values: dict[str, int] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        key, value = line.split()
        values[key] = int(value)
    return values


class CandidateResourceEnvelope:
    """A fresh cgroup-v2 boundary for one Bubblewrap generation."""

    def __init__(self) -> None:
        self.path: Path | None = None

    def __enter__(self) -> CandidateResourceEnvelope:
        if os.geteuid() != 0:
            raise ResourceEnvelopeError("candidate resource envelope requires root")
        controllers = set(
            (CGROUP_ROOT / "cgroup.controllers").read_text(encoding="ascii").split()
        )
        if not {"cpu", "memory", "pids"}.issubset(controllers):
            raise ResourceEnvelopeError("required cgroup-v2 controllers are unavailable")
        path = CGROUP_ROOT / f"q1-l1-candidate-{os.getpid()}-{time.monotonic_ns()}"
        path.mkdir(mode=0o700)
        self.path = path
        try:
            _write_control(path / "cpu.max", CPU_MAX)
            _write_control(path / "memory.max", str(MEMORY_MAX_BYTES))
            _write_control(path / "memory.swap.max", str(MEMORY_SWAP_MAX_BYTES))
            _write_control(path / "memory.oom.group", str(MEMORY_OOM_GROUP))
            _write_control(path / "pids.max", str(PIDS_MAX))
            expected = {
                "cpu.max": CPU_MAX,
                "memory.max": str(MEMORY_MAX_BYTES),
                "memory.swap.max": str(MEMORY_SWAP_MAX_BYTES),
                "memory.oom.group": str(MEMORY_OOM_GROUP),
                "pids.max": str(PIDS_MAX),
            }
            observed = {
                name: (path / name).read_text(encoding="ascii").strip()
                for name in expected
            }
            if observed != expected:
                raise ResourceEnvelopeError(
                    f"candidate cgroup limits did not read back exactly: {observed!r}"
                )
        except Exception:
            path.rmdir()
            self.path = None
            raise
        return self

    def enter_child(self) -> None:
        if self.path is None:
            raise ResourceEnvelopeError("candidate cgroup was not initialized")
        _write_control(self.path / "cgroup.procs", str(os.getpid()))

    def _remove(self) -> list[str]:
        path = self.path
        self.path = None
        if path is None:
            return []
        reasons = self._breaches_for(path)
        try:
            populated = _key_values(path / "cgroup.events").get("populated", 1)
        except (OSError, ValueError) as exc:
            reasons.append(f"candidate cgroup population could not be read: {exc}")
            populated = 1
        if populated:
            reasons.append("candidate tasks survived Bubblewrap teardown")
            try:
                _write_control(path / "cgroup.kill", "1")
            except OSError as exc:
                reasons.append(f"candidate cgroup could not be killed: {exc}")
            deadline = time.monotonic() + 1.0
            while time.monotonic() < deadline:
                try:
                    if _key_values(path / "cgroup.events").get("populated", 1) == 0:
                        break
                except (OSError, ValueError):
                    break
                time.sleep(0.01)
        try:
            path.rmdir()
        except OSError as exc:
            reasons.append(f"candidate cgroup could not be removed: {exc}")
        return reasons

    @staticmethod
    def _breaches_for(path: Path) -> list[str]:
        reasons: list[str] = []
        try:
            cpu = _key_values(path / "cpu.stat")
            memory = _key_values(path / "memory.events.local")
            pids = _key_values(path / "pids.events.local")
        except (OSError, ValueError) as exc:
            return [f"candidate resource counters could not be read: {exc}"]
        if cpu.get("nr_throttled", 0) > 0:
            reasons.append("4-CPU quota was reached")
        if any(memory.get(key, 0) > 0 for key in ("max", "oom", "oom_kill", "oom_group_kill")):
            reasons.append("4-GiB memory limit was reached")
        if pids.get("max", 0) > 0:
            reasons.append("256-task limit was reached")
        return reasons

    def __exit__(self, _type: object, _value: object, _traceback: object) -> None:
        reasons = self._remove()
        if reasons:
            raise ResourceEnvelopeError("; ".join(reasons))


class WritableStateEnvelope:
    """A private, no-exec filesystem capped at one GiB."""

    def __init__(self, root: Path, *, persistent: bool) -> None:
        self.root = root
        self.persistent = persistent
        self.mountpoint = root / ".q1-l1-state" if persistent else root
        self.state = self.mountpoint / "state"
        self.temporary = self.mountpoint / "tmp"
        self._mounted = False

    def __enter__(self) -> WritableStateEnvelope:
        if os.geteuid() != 0:
            raise ResourceEnvelopeError("writable-state envelope requires root")
        os.unshare(os.CLONE_NEWNS)
        subprocess.run(["/usr/bin/mount", "--make-rprivate", "/"], check=True)
        if self.persistent:
            self._mount_persistent()
        else:
            subprocess.run(
                [
                    "/usr/bin/mount",
                    "-t",
                    "tmpfs",
                    "-o",
                    f"size={WRITABLE_STATE_BYTES},mode=0700,nodev,nosuid,noexec",
                    "tmpfs",
                    str(self.mountpoint),
                ],
                check=True,
            )
            self._mounted = True
        self.state.mkdir(mode=0o1777, exist_ok=True)
        self.temporary.mkdir(mode=0o1777, exist_ok=True)
        self.state.chmod(0o1777)
        self.temporary.chmod(0o1777)
        capacity = os.statvfs(self.mountpoint).f_blocks * os.statvfs(self.mountpoint).f_frsize
        if capacity > WRITABLE_STATE_BYTES:
            raise ResourceEnvelopeError(
                f"writable-state capacity exceeds one GiB: {capacity} bytes"
            )
        return self

    def _mount_persistent(self) -> None:
        image = self.root / ".q1-l1-state.ext4"
        try:
            metadata = image.lstat()
        except FileNotFoundError:
            directory_metadata = self.root.stat()
            descriptor = os.open(
                image,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
                0o600,
            )
            try:
                os.ftruncate(descriptor, WRITABLE_STATE_BYTES)
                os.fchown(descriptor, directory_metadata.st_uid, directory_metadata.st_gid)
            finally:
                os.close(descriptor)
            subprocess.run(
                ["/usr/sbin/mkfs.ext4", "-q", "-F", "-m", "0", str(image)],
                check=True,
            )
            metadata = image.lstat()
        if not image.is_file() or metadata.st_size != WRITABLE_STATE_BYTES:
            raise ResourceEnvelopeError("persistent writable-state image is invalid")
        self.mountpoint.mkdir(mode=0o700, exist_ok=True)
        if self.mountpoint.is_symlink() or not self.mountpoint.is_dir():
            raise ResourceEnvelopeError("persistent writable-state mountpoint is invalid")
        subprocess.run(
            [
                "/usr/bin/mount",
                "-t",
                "ext4",
                "-o",
                "loop,nodev,nosuid,noexec,noatime",
                str(image),
                str(self.mountpoint),
            ],
            check=True,
        )
        self._mounted = True

    def __exit__(self, _type: object, _value: object, _traceback: object) -> None:
        reasons: list[str] = []
        if self._mounted:
            try:
                stats = os.statvfs(self.mountpoint)
                if stats.f_bavail == 0 or stats.f_favail == 0:
                    reasons.append("1-GiB writable-state capacity was exhausted")
            except OSError as exc:
                reasons.append(f"writable-state capacity could not be read: {exc}")
            completed = subprocess.run(
                ["/usr/bin/umount", str(self.mountpoint)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            if completed.returncode != 0:
                reasons.append(
                    f"writable-state filesystem could not be unmounted: {completed.stderr.strip()}"
                )
            self._mounted = False
        if reasons:
            raise ResourceEnvelopeError("; ".join(reasons))


def _forward(signum: int, _frame: object) -> None:
    if _candidate is None:
        return
    try:
        os.kill(_candidate.pid, signum)
    except ProcessLookupError:
        pass


def _surviving_candidate_processes() -> bool:
    """Detect descendants left behind when the declared foreground process exits."""

    # The production Bubblewrap command makes this trusted launcher PID 1. Unit
    # callers exercise ``run`` directly; ``main`` rejects that shape in production.
    if os.getpid() != 1:
        return False
    while True:
        try:
            waited, _status = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            break
        if waited == 0:
            break
    return any(
        entry.name.isdigit() and int(entry.name) != 1
        for entry in Path("/proc").iterdir()
    )


def run(argv: Sequence[str]) -> int:
    global _candidate

    if not argv or not argv[0] or any("\0" in argument for argument in argv):
        print("candidate command must be a nonempty NUL-free argv", file=sys.stderr)
        return 127
    entry_socket = os.environ.pop(ENTRY_SOCKET_ENV, None)
    if entry_socket is None:
        print("candidate launcher has no trusted startup socket", file=sys.stderr)
        return 127
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as client:
            client.sendto(ENTRY_TOKEN, entry_socket)
    except OSError as exc:
        print(f"candidate launcher could not signal trusted startup: {exc}", file=sys.stderr)
        return 127
    try:
        _candidate = subprocess.Popen(list(argv))
    except OSError as exc:
        print(f"candidate command could not start: {exc}", file=sys.stderr)
        return (
            125
            if exc.errno in {errno.EAGAIN, errno.EMFILE, errno.ENFILE, errno.ENOMEM}
            else 127
        )
    return_code = _candidate.wait()
    try:
        descendants_survived = _surviving_candidate_processes()
    except OSError:
        print("candidate process inventory could not be verified", file=sys.stderr)
        return 125
    if descendants_survived:
        print("declared foreground command left a surviving process", file=sys.stderr)
        return FOREGROUND_VIOLATION_EXIT
    return 1 if return_code == 125 else return_code


def main(argv: Sequence[str] | None = None) -> int:
    command = list(sys.argv[1:] if argv is None else argv)
    if command[:1] == ["--"]:
        command = command[1:]
    if os.getpid() != 1:
        print("candidate launcher is not PID 1 in its process namespace", file=sys.stderr)
        return 125
    signal.signal(signal.SIGTERM, _forward)
    signal.signal(signal.SIGINT, _forward)
    signal.signal(signal.SIGHUP, _forward)
    return run(command)


if __name__ == "__main__":
    raise SystemExit(main())
