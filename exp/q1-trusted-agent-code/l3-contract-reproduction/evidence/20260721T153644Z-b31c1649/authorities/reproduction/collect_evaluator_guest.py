"""Actively collect the public-safe guest half of the q1-l1-evaluator fingerprint.

Run this inside the already-running evaluator as root. The collector never reads
``evaluator-authority.json`` and never installs, upgrades, starts, or repairs the
evaluator. It derives runtime state, exercises the required isolation mechanisms in
private temporary scopes, verifies cleanup, and writes one bounded JSON fragment.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import selectors
import signal
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parent
PACKAGE_NAMES_PATH = ROOT / "apt-packages.txt"
CGROUP_ROOT = Path("/sys/fs/cgroup")
PYTHON_PATH = Path("/usr/bin/python3.14")
PYTHON_STDLIB = Path("/usr/lib/python3.14")
SYSTEMD_CONFIG_ROOT = Path("/etc/systemd/system")
STATE_BYTES = 1024**3
CPU_MAX = "400000 100000"
MEMORY_MAX_BYTES = 4 * 1024**3
PIDS_MAX = 256
MAX_OUTPUT_BYTES = 1024 * 1024
MAX_COMMAND_OUTPUT_BYTES = 1024 * 1024
MAX_HASHED_FILE_BYTES = 256 * 1024**2
MAX_TREE_FILE_BYTES = 512 * 1024**2
MAX_TREE_ENTRIES = 100_000
COMMAND_TIMEOUT_SECONDS = 120
LOOP_AUTOCLEAR_DEADLINE_SECONDS = 2.0
LOOP_ABSENCE_DEADLINE_SECONDS = 1.0
LOOP_POLL_SECONDS = 0.05
LOOP_QUERY_TIMEOUT_SECONDS = 0.5
LOOP_DETACH_TIMEOUT_SECONDS = 1.0
ENVIRONMENT = {
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
}
PACKAGE_NAME = re.compile(r"^[a-z0-9][a-z0-9+.-]*$")
PACKAGE_VALUE = re.compile(r"^[A-Za-z0-9.+:~_-]+$")
RUNTIME_VALUE = re.compile(r"^[A-Za-z0-9 .+,:_()-]+$")
CONTROLLER_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
TOOL_SYMLINK_TARGET = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
Q1_L1_TMPDIR = re.compile(
    r"^/tmp/q1-l1-run-[A-Za-z0-9][A-Za-z0-9._-]*/tmp$"
)
REQUIRED_FILESYSTEMS = frozenset({"cgroup2", "ext4", "overlay", "tmpfs"})
REQUIRED_MOUNT_OPTIONS = frozenset({"nodev", "noexec", "nosuid"})
AUTOMATIC_PACKAGE_UPDATE_UNITS = (
    "apt-daily-upgrade.service",
    "apt-daily-upgrade.timer",
    "apt-daily.service",
    "apt-daily.timer",
    "unattended-upgrades.service",
)
TOOL_COMMANDS: dict[str, tuple[Path, tuple[str, ...], str | None]] = {
    "bubblewrap": (
        Path("/usr/bin/bwrap"),
        ("/usr/bin/bwrap", "--version"),
        "bubblewrap ",
    ),
    "losetup": (
        Path("/usr/sbin/losetup"),
        ("/usr/sbin/losetup", "--version"),
        "losetup from util-linux ",
    ),
    "mkfs_ext4": (
        Path("/usr/sbin/mkfs.ext4"),
        ("/usr/sbin/mkfs.ext4", "-V"),
        "mke2fs ",
    ),
    "mount": (
        Path("/usr/bin/mount"),
        ("/usr/bin/mount", "--version"),
        "mount from util-linux ",
    ),
    "python": (PYTHON_PATH, (), None),
    "umount": (
        Path("/usr/bin/umount"),
        ("/usr/bin/umount", "--version"),
        "umount from util-linux ",
    ),
    "unshare": (
        Path("/usr/bin/unshare"),
        ("/usr/bin/unshare", "--version"),
        "unshare from util-linux ",
    ),
}
SYMLINK_TOOLS = frozenset({"mkfs_ext4"})


class CollectionError(RuntimeError):
    """The guest fingerprint could not be derived safely and completely."""


def _validated_tmpdir() -> Path:
    raw = os.environ.get("TMPDIR")
    if raw is None or Q1_L1_TMPDIR.fullmatch(raw) is None:
        raise CollectionError("collector TMPDIR is outside the run envelope")
    path = Path(raw)
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise CollectionError("collector TMPDIR is unavailable") from exc
    if not stat.S_ISDIR(metadata.st_mode) or path.is_symlink():
        raise CollectionError("collector TMPDIR is not a real directory")
    return path


def _command_environment() -> dict[str, str]:
    return {**ENVIRONMENT, "TMPDIR": str(_validated_tmpdir())}


def _read_bounded(path: Path, limit: int = MAX_COMMAND_OUTPUT_BYTES) -> bytes:
    with path.open("rb") as stream:
        payload = stream.read(limit + 1)
    if len(payload) > limit:
        raise CollectionError("bounded input exceeded")
    return payload


def _command(
    argv: Sequence[str], *, timeout_seconds: float | None = None
) -> subprocess.CompletedProcess[bytes]:
    timeout_seconds = COMMAND_TIMEOUT_SECONDS if timeout_seconds is None else timeout_seconds
    if timeout_seconds <= 0:
        raise CollectionError("guest probe command timeout is invalid")
    process: subprocess.Popen[bytes] | None = None
    selector = selectors.DefaultSelector()
    stdout = bytearray()
    stderr = bytearray()
    try:
        process = subprocess.Popen(
            list(argv),
            env=_command_environment(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        if process.stdout is None or process.stderr is None:
            raise CollectionError("guest probe command pipes were unavailable")
        streams = (("stdout", process.stdout), ("stderr", process.stderr))
        for name, stream in streams:
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        deadline = time.monotonic() + timeout_seconds
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise CollectionError("guest probe command timed out")
            for key, _events in selector.select(min(remaining, 0.25)):
                try:
                    chunk = os.read(key.fileobj.fileno(), 64 * 1024)
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                target = stdout if key.data == "stdout" else stderr
                target.extend(chunk)
                if len(stdout) + len(stderr) > MAX_COMMAND_OUTPUT_BYTES:
                    raise CollectionError("guest probe command output exceeded limit")
        return_code = process.wait(timeout=5)
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            pass
        else:
            _kill_command_group(process)
            raise CollectionError("guest probe command left a descendant")
    except CollectionError:
        if process is not None:
            _kill_command_group(process)
        raise
    except (OSError, subprocess.SubprocessError) as exc:
        if process is not None:
            _kill_command_group(process)
        raise CollectionError("guest probe command could not complete") from exc
    finally:
        selector.close()
        if process is not None:
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()
    completed = subprocess.CompletedProcess(list(argv), return_code, bytes(stdout), bytes(stderr))
    if return_code != 0:
        raise CollectionError("guest probe command failed")
    return completed


def _kill_command_group(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired as exc:
        raise CollectionError("guest probe process group could not be reaped") from exc


def _safe_text(payload: bytes, *, prefix: str | None = None) -> str:
    try:
        value = payload.decode("ascii").strip()
    except UnicodeDecodeError as exc:
        raise CollectionError("guest probe returned non-ASCII metadata") from exc
    if (
        not value
        or len(value) > 512
        or RUNTIME_VALUE.fullmatch(value) is None
        or (prefix is not None and not value.startswith(prefix))
    ):
        raise CollectionError("guest probe returned unsafe metadata")
    return value


def _version_line(argv: Sequence[str], prefix: str) -> str:
    completed = _command(argv)
    lines = [
        line
        for line in (*completed.stdout.splitlines(), *completed.stderr.splitlines())
        if line.strip()
    ]
    for line in lines:
        try:
            value = _safe_text(line, prefix=prefix)
        except CollectionError:
            continue
        return value
    raise CollectionError("tool version line was unavailable")


def _sha256_regular(path: Path, expected: os.stat_result | None = None) -> str:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise CollectionError("runtime file could not be opened safely") from exc
    digest = hashlib.sha256()
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_HASHED_FILE_BYTES:
            raise CollectionError("runtime file is not a bounded regular file")
        if expected is not None and _stable_stat(before) != _stable_stat(expected):
            raise CollectionError("runtime file changed before hashing")
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        after = os.fstat(descriptor)
        if _stable_stat(before) != _stable_stat(after):
            raise CollectionError("runtime file changed while hashing")
    finally:
        os.close(descriptor)
    return digest.hexdigest()


def _stable_stat(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_size,
        value.st_mtime_ns,
    )


def _tool_identity(path: Path, *, allow_symlink: bool) -> dict[str, str]:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise CollectionError("runtime tool identity could not be inspected") from exc
    record = {"path": str(path)}
    if stat.S_ISREG(metadata.st_mode):
        record["sha256"] = _sha256_regular(path, metadata)
        try:
            after = path.lstat()
        except OSError as exc:
            raise CollectionError("runtime tool changed during hashing") from exc
        if _stable_stat(metadata) != _stable_stat(after):
            raise CollectionError("runtime tool changed during hashing")
        return record
    if not allow_symlink or not stat.S_ISLNK(metadata.st_mode):
        raise CollectionError("runtime tool identity is not an approved regular file")
    try:
        target = os.readlink(path)
    except OSError as exc:
        raise CollectionError("runtime tool symlink could not be read") from exc
    if (
        Path(target).is_absolute()
        or Path(target).name != target
        or TOOL_SYMLINK_TARGET.fullmatch(target) is None
    ):
        raise CollectionError("runtime tool symlink target is not canonical")
    resolved = path.parent / target
    try:
        resolved_metadata = resolved.lstat()
    except OSError as exc:
        raise CollectionError("runtime tool target could not be inspected") from exc
    record.update(
        {
            "path_kind": "symlink",
            "resolved_path": str(resolved),
            "sha256": _sha256_regular(resolved, resolved_metadata),
            "symlink_target": target,
        }
    )
    try:
        after = path.lstat()
        final_target = os.readlink(path)
        final_resolved = resolved.lstat()
    except OSError as exc:
        raise CollectionError("runtime tool symlink changed during hashing") from exc
    if (
        _stable_stat(metadata) != _stable_stat(after)
        or _stable_stat(resolved_metadata) != _stable_stat(final_resolved)
        or target != final_target
    ):
        raise CollectionError("runtime tool symlink changed during hashing")
    return record


def _package_names() -> list[str]:
    try:
        text = _read_bounded(PACKAGE_NAMES_PATH).decode("ascii")
    except UnicodeDecodeError as exc:
        raise CollectionError("package-name authority is not ASCII") from exc
    names: list[str] = []
    for line in text.splitlines():
        if line.count("=") != 1:
            raise CollectionError("package-name authority is not canonical")
        name, _ignored_expected_version = line.split("=", 1)
        if PACKAGE_NAME.fullmatch(name) is None or name in names:
            raise CollectionError("package-name authority is not canonical")
        names.append(name)
    if not names or names != sorted(names):
        raise CollectionError("package-name authority is not sorted")
    return names


def _installed_packages() -> tuple[dict[str, Any], dict[str, str]]:
    record_format = "${binary:Package}\\t${Version}\\t${Architecture}\\t${db:Status-Abbrev}\\n"
    completed = _command(
        (
            "/usr/bin/dpkg-query",
            "-W",
            "-f=${binary:Package}\t${Version}\t${Architecture}\t${db:Status-Abbrev}\n",
        )
    )
    if not completed.stdout.endswith(b"\n") or b"\r" in completed.stdout:
        raise CollectionError("installed-package inventory is not canonical")
    lines = completed.stdout.splitlines()
    if not lines or len(lines) > MAX_TREE_ENTRIES or len(lines) != len(set(lines)):
        raise CollectionError("installed-package inventory is not bounded and unique")
    for line in lines:
        fields = line.split(b"\t")
        if len(fields) != 4 or any(not field for field in fields[:3]):
            raise CollectionError("installed-package inventory record is invalid")
        try:
            decoded = [field.decode("ascii") for field in fields]
        except UnicodeDecodeError as exc:
            raise CollectionError("installed-package inventory is not ASCII") from exc
        if (
            PACKAGE_VALUE.fullmatch(decoded[0]) is None
            or PACKAGE_VALUE.fullmatch(decoded[1]) is None
            or PACKAGE_VALUE.fullmatch(decoded[2]) is None
            or len(decoded[3]) != 3
            or any(ord(character) < 0x20 or ord(character) > 0x7E for character in decoded[3])
        ):
            raise CollectionError("installed-package inventory record is unsafe")
    normalized = b"\n".join(sorted(lines)) + b"\n"
    inventory = {
        "count": len(lines),
        "record_format": record_format,
        "sha256": hashlib.sha256(normalized).hexdigest(),
        "sort": "lexicographic record bytes with one final LF",
    }

    packages: dict[str, str] = {}
    for name in _package_names():
        installed = _command(
            (
                "/usr/bin/dpkg-query",
                "-W",
                "-f=${db:Status-Abbrev}\t${Version}",
                name,
            )
        ).stdout
        try:
            status, version = installed.decode("ascii").split("\t", 1)
        except (UnicodeDecodeError, ValueError) as exc:
            raise CollectionError("required package record is invalid") from exc
        if (
            status != "ii "
            or PACKAGE_VALUE.fullmatch(version) is None
            or len(version) > 256
        ):
            raise CollectionError("required package is not installed canonically")
        packages[name] = version
    return inventory, packages


def _python_runtime() -> tuple[dict[str, Any], Path]:
    program = (
        "import json,platform,sys,sysconfig;"
        "print(json.dumps({'build':list(platform.python_build()),"
        "'stdlib':sysconfig.get_path('stdlib'),"
        "'version':f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}'},"
        "sort_keys=True,separators=(',',':')))"
    )
    payload = _command((str(PYTHON_PATH), "-B", "-I", "-c", program)).stdout
    try:
        observed = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectionError("Python runtime metadata is invalid") from exc
    if not isinstance(observed, dict) or set(observed) != {"build", "stdlib", "version"}:
        raise CollectionError("Python runtime metadata is incomplete")
    build = observed["build"]
    if (
        not isinstance(build, list)
        or len(build) != 2
        or any(not isinstance(item, str) or RUNTIME_VALUE.fullmatch(item) is None for item in build)
        or not isinstance(observed["version"], str)
        or re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", observed["version"]) is None
        or observed["stdlib"] != str(PYTHON_STDLIB)
    ):
        raise CollectionError("Python runtime metadata is unsafe")
    return {"build": build, "version": observed["version"]}, PYTHON_STDLIB


def _automatic_package_updates() -> dict[str, Any]:
    masked_units: list[str] = []
    for unit in AUTOMATIC_PACKAGE_UPDATE_UNITS:
        path = SYSTEMD_CONFIG_ROOT / unit
        try:
            metadata = path.lstat()
            target = os.readlink(path)
        except OSError as exc:
            raise CollectionError("automatic package updates are not masked") from exc
        if not stat.S_ISLNK(metadata.st_mode) or target != "/dev/null":
            raise CollectionError("automatic package updates are not masked")
        masked_units.append(unit)
    return {"masked_units": masked_units}


def _bounded_tree_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    try:
        for path in root.rglob("*"):
            paths.append(path)
            if len(paths) > MAX_TREE_ENTRIES:
                raise CollectionError("Python standard-library tree exceeds entry limit")
    except OSError as exc:
        raise CollectionError("Python standard-library tree could not be enumerated") from exc
    if not paths:
        raise CollectionError("Python standard-library tree is empty")
    paths.sort(key=lambda path: os.fsencode(path.relative_to(root)))
    return paths


def _stdlib_tree(root: Path) -> dict[str, Any]:
    paths = _bounded_tree_paths(root)
    relatives = [os.fsencode(path.relative_to(root)) for path in paths]
    if len(relatives) != len(set(relatives)) or any(
        b"\0" in item or b"\n" in item for item in relatives
    ):
        raise CollectionError("Python standard-library paths are not canonical")

    digest = hashlib.sha256()
    regular_bytes = 0
    for path, relative in zip(paths, relatives):
        try:
            metadata = path.lstat()
        except OSError as exc:
            raise CollectionError("Python standard-library entry could not be inspected") from exc
        if stat.S_ISDIR(metadata.st_mode):
            kind = b"d"
            payload = b""
        elif stat.S_ISREG(metadata.st_mode):
            kind = b"f"
            regular_bytes += metadata.st_size
            if regular_bytes > MAX_TREE_FILE_BYTES:
                raise CollectionError("Python standard-library tree exceeds byte limit")
            payload = _sha256_regular(path, metadata).encode("ascii")
        elif stat.S_ISLNK(metadata.st_mode):
            kind = b"l"
            try:
                payload = os.fsencode(os.readlink(path))
                after = path.lstat()
            except OSError as exc:
                raise CollectionError("Python standard-library symlink changed") from exc
            if _stable_stat(metadata) != _stable_stat(after):
                raise CollectionError("Python standard-library symlink changed")
        else:
            kind = b"o"
            payload = b""
        digest.update(
            kind
            + b"\0"
            + oct(stat.S_IMODE(metadata.st_mode)).encode("ascii")
            + b"\0"
            + relative
            + b"\0"
            + payload
            + b"\n"
        )

    final_relatives = [
        os.fsencode(path.relative_to(root)) for path in _bounded_tree_paths(root)
    ]
    if relatives != final_relatives:
        raise CollectionError("Python standard-library tree changed")
    return {
        "algorithm": "collect_evaluator_guest.py:stdlib-tree-v1",
        "count": len(paths),
        "directory_other_payload": "empty bytes",
        "exclusions": [],
        "file_content_hash": "sha256",
        "mode_encoding": "Python oct(stat.S_IMODE(mode)) as ASCII, including 0o prefix",
        "record_format": "type\\0mode\\0relative-path\\0(file-sha256|symlink-target)\\n",
        "root": str(root),
        "root_record_included": False,
        "sha256": digest.hexdigest(),
        "sort": "relative names by os.fsencode",
        "symlink_target_encoding": "raw os.fsencode bytes",
        "types": ["d", "f", "l", "o"],
    }


def _tools() -> dict[str, dict[str, str]]:
    tools: dict[str, dict[str, str]] = {}
    for name, (path, version_argv, prefix) in TOOL_COMMANDS.items():
        record = _tool_identity(path, allow_symlink=name in SYMLINK_TOOLS)
        if version_argv and prefix is not None:
            record["version"] = _version_line(version_argv, prefix)
        tools[name] = record
    return tools


def _mount_record(path: Path) -> tuple[str, set[str], list[str]] | None:
    encoded = os.fsencode(path)
    for line in _read_bounded(Path("/proc/self/mountinfo")).splitlines():
        fields = line.split()
        try:
            separator = fields.index(b"-")
        except ValueError:
            raise CollectionError("mount table is invalid")
        if len(fields) <= separator + 2 or fields[4] != encoded:
            continue
        try:
            filesystem = fields[separator + 1].decode("ascii")
            options = set(fields[5].decode("ascii").split(","))
            optional = [field.decode("ascii") for field in fields[6:separator]]
        except UnicodeDecodeError as exc:
            raise CollectionError("mount table contains unsafe metadata") from exc
        return filesystem, options, optional
    return None


def _cgroup_probe() -> tuple[dict[str, Any], dict[str, Any]]:
    record = _mount_record(CGROUP_ROOT)
    if record is None or record[0] != "cgroup2":
        raise CollectionError("cgroup v2 is not mounted at the required root")
    try:
        controllers = sorted(
            _read_bounded(CGROUP_ROOT / "cgroup.controllers").decode("ascii").split()
        )
    except UnicodeDecodeError as exc:
        raise CollectionError("cgroup controllers are not ASCII") from exc
    if (
        not controllers
        or len(controllers) > 64
        or any(CONTROLLER_NAME.fullmatch(name) is None for name in controllers)
        or not {"cpu", "memory", "pids"}.issubset(controllers)
    ):
        raise CollectionError("required cgroup controllers are unavailable")

    probe = CGROUP_ROOT / f"q1-l1-authority-{os.getpid()}-{secrets.token_hex(8)}"
    created = False
    try:
        probe.mkdir(mode=0o700)
        created = True
        expected = {
            "cpu.max": CPU_MAX,
            "memory.max": str(MEMORY_MAX_BYTES),
            "memory.oom.group": "1",
            "memory.swap.max": "0",
            "pids.max": str(PIDS_MAX),
        }
        for name, value in expected.items():
            (probe / name).write_text(value, encoding="ascii")
        observed = {
            name: (probe / name).read_text(encoding="ascii").strip()
            for name in expected
        }
        if observed != expected:
            raise CollectionError("cgroup controls did not read back exactly")
    finally:
        if created:
            try:
                events = (probe / "cgroup.events").read_text(encoding="ascii")
                if "populated 0" not in events.splitlines():
                    raise CollectionError("temporary cgroup unexpectedly contains tasks")
                probe.rmdir()
            except OSError as exc:
                raise CollectionError("temporary cgroup cleanup failed") from exc
            if probe.exists():
                raise CollectionError("temporary cgroup cleanup was not verified")
    return (
        {
            "controllers": controllers,
            "direct_child_control": True,
            "mounted": True,
        },
        {
            "cpu_max": observed["cpu.max"],
            "memory_max_bytes": int(observed["memory.max"]),
            "memory_oom_group": observed["memory.oom.group"] == "1",
            "memory_swap_max_bytes": int(observed["memory.swap.max"]),
            "pids_max": int(observed["pids.max"]),
        },
    )


def _user_namespace_probe() -> dict[str, Any]:
    try:
        unprivileged = int(
            _read_bounded(Path("/proc/sys/kernel/unprivileged_userns_clone"))
        )
        maximum = int(_read_bounded(Path("/proc/sys/user/max_user_namespaces")))
    except ValueError as exc:
        raise CollectionError("user-namespace controls are invalid") from exc
    if unprivileged not in {0, 1} or maximum < 0 or maximum > 2**63 - 1:
        raise CollectionError("user-namespace controls are out of range")
    _command(
        (
            "/usr/bin/unshare",
            "--user",
            "--map-root-user",
            "--fork",
            "/usr/bin/true",
        )
    )
    return {
        "creation_probe": True,
        "maximum": maximum,
        "unprivileged_clone": unprivileged == 1,
    }


def _filesystems() -> list[str]:
    available: set[str] = set()
    for line in _read_bounded(Path("/proc/filesystems")).splitlines():
        fields = line.split()
        if not fields:
            continue
        try:
            available.add(fields[-1].decode("ascii"))
        except UnicodeDecodeError as exc:
            raise CollectionError("filesystem table is not ASCII") from exc
    if not REQUIRED_FILESYSTEMS.issubset(available):
        raise CollectionError("required filesystems are unavailable")
    return sorted(REQUIRED_FILESYSTEMS)


def _unmount(path: Path) -> None:
    if _mount_record(path) is not None:
        _command(("/usr/bin/umount", str(path)))
    if _mount_record(path) is not None:
        raise CollectionError("temporary filesystem remained mounted")


def _loop_devices(image: Path, *, timeout_seconds: float) -> list[str]:
    output = _command(
        ("/usr/sbin/losetup", "-j", str(image)),
        timeout_seconds=timeout_seconds,
    ).stdout
    devices: list[str] = []
    for line in output.splitlines():
        prefix = line.split(b":", 1)[0]
        try:
            device = prefix.decode("ascii")
        except UnicodeDecodeError as exc:
            raise CollectionError("loop-device metadata is unsafe") from exc
        if re.fullmatch(r"/dev/loop[0-9]+", device) is None:
            raise CollectionError("loop-device metadata is invalid")
        devices.append(device)
    return devices


def _wait_for_loop_absence(image: Path, *, deadline_seconds: float) -> list[str]:
    deadline = time.monotonic() + deadline_seconds
    while True:
        remaining = deadline - time.monotonic()
        query_timeout = min(LOOP_QUERY_TIMEOUT_SECONDS, max(remaining, 0.001))
        devices = _loop_devices(image, timeout_seconds=query_timeout)
        if not devices:
            return []
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return devices
        time.sleep(min(LOOP_POLL_SECONDS, remaining))


def _cleanup_mount_probe(
    tmpfs_mount: Path,
    ext4_mount: Path,
    image: Path,
    *,
    owned_parent: Path,
) -> None:
    root = image.parent
    if (
        root.parent != owned_parent
        or not root.name.startswith("q1-l1-authority-")
        or tmpfs_mount != root / "tmpfs"
        or ext4_mount != root / "ext4"
        or image != root / "state.ext4"
    ):
        raise CollectionError("temporary writable-state paths are not owned")
    unmount_errors: list[CollectionError] = []
    for mountpoint in (ext4_mount, tmpfs_mount):
        try:
            _unmount(mountpoint)
        except CollectionError as exc:
            unmount_errors.append(exc)
    if unmount_errors:
        raise CollectionError(
            "temporary writable-state unmount failed; owned orphan retained"
        ) from unmount_errors[0]
    try:
        devices = _wait_for_loop_absence(
            image, deadline_seconds=LOOP_AUTOCLEAR_DEADLINE_SECONDS
        )
        if devices:
            if len(devices) != 1:
                raise CollectionError("owned image has multiple loop devices")
            _command(
                ("/usr/sbin/losetup", "--detach", devices[0]),
                timeout_seconds=LOOP_DETACH_TIMEOUT_SECONDS,
            )
        if _wait_for_loop_absence(
            image, deadline_seconds=LOOP_ABSENCE_DEADLINE_SECONDS
        ):
            raise CollectionError(
                "temporary loop device survived cleanup; owned orphan retained"
            )
    except CollectionError as exc:
        raise CollectionError(
            "temporary loop cleanup failed; owned orphan retained"
        ) from exc
    try:
        image.unlink(missing_ok=True)
        ext4_mount.rmdir()
        tmpfs_mount.rmdir()
        root.rmdir()
    except OSError as exc:
        raise CollectionError(
            "temporary path cleanup failed; owned orphan retained"
        ) from exc
    if root.exists():
        raise CollectionError("temporary writable-state cleanup was not verified")


def _writable_state_probe() -> dict[str, Any]:
    if os.geteuid() != 0:
        raise CollectionError("guest capability probes require root")
    clone_newns = getattr(os, "CLONE_NEWNS", None)
    unshare = getattr(os, "unshare", None)
    if clone_newns is None or unshare is None:
        raise CollectionError("mount-namespace API is unavailable")
    before_namespace = os.stat("/proc/self/ns/mnt").st_ino
    try:
        unshare(clone_newns)
    except OSError as exc:
        raise CollectionError("private mount namespace could not be created") from exc
    after_namespace = os.stat("/proc/self/ns/mnt").st_ino
    if before_namespace == after_namespace:
        raise CollectionError("private mount namespace was not verified")
    _command(("/usr/bin/mount", "--make-rprivate", "/"))
    root_mount = _mount_record(Path("/"))
    if root_mount is None or any(
        item.startswith(("shared:", "master:", "propagate_from:"))
        for item in root_mount[2]
    ):
        raise CollectionError("private mount propagation was not verified")

    ephemeral_filesystem = ""
    persistent_filesystem = ""
    observed_options: set[str] | None = None
    owned_parent = _validated_tmpdir()
    temporary_root = Path(
        tempfile.mkdtemp(
            prefix="q1-l1-authority-",
            dir=owned_parent,
        )
    )
    tmpfs_mount = temporary_root / "tmpfs"
    ext4_mount = temporary_root / "ext4"
    image = temporary_root / "state.ext4"
    tmpfs_mount.mkdir(mode=0o700)
    ext4_mount.mkdir(mode=0o700)
    try:
        _command(
            (
                "/usr/bin/mount",
                "-t",
                "tmpfs",
                "-o",
                f"size={STATE_BYTES},mode=0700,nodev,nosuid,noexec",
                "tmpfs",
                str(tmpfs_mount),
            )
        )
        tmpfs_record = _mount_record(tmpfs_mount)
        if tmpfs_record is None:
            raise CollectionError("temporary tmpfs mount was not observed")
        ephemeral_filesystem = tmpfs_record[0]
        observed_options = REQUIRED_MOUNT_OPTIONS & tmpfs_record[1]
        stats = os.statvfs(tmpfs_mount)
        if stats.f_blocks * stats.f_frsize > STATE_BYTES:
            raise CollectionError("temporary tmpfs exceeds the approved capacity")
        _unmount(tmpfs_mount)

        descriptor = os.open(
            image,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
            0o600,
        )
        try:
            os.ftruncate(descriptor, STATE_BYTES)
        finally:
            os.close(descriptor)
        _command(("/usr/sbin/mkfs.ext4", "-q", "-F", "-m", "0", str(image)))
        if image.stat().st_size != STATE_BYTES:
            raise CollectionError("temporary ext4 image has the wrong capacity")
        _command(
            (
                "/usr/bin/mount",
                "-t",
                "ext4",
                "-o",
                "loop,nodev,nosuid,noexec,noatime",
                str(image),
                str(ext4_mount),
            )
        )
        ext4_record = _mount_record(ext4_mount)
        if ext4_record is None:
            raise CollectionError("temporary ext4 mount was not observed")
        persistent_filesystem = ext4_record[0]
        observed_options &= ext4_record[1]
        stats = os.statvfs(ext4_mount)
        if stats.f_blocks * stats.f_frsize > STATE_BYTES:
            raise CollectionError("temporary ext4 exceeds the approved capacity")
        _unmount(ext4_mount)
    finally:
        _cleanup_mount_probe(
            tmpfs_mount,
            ext4_mount,
            image,
            owned_parent=owned_parent,
        )

    if observed_options != REQUIRED_MOUNT_OPTIONS:
        raise CollectionError("writable-state mount options were not enforced")
    if ephemeral_filesystem != "tmpfs" or persistent_filesystem != "ext4":
        raise CollectionError("writable-state filesystems were not enforced")
    return {
        "ephemeral_filesystem": ephemeral_filesystem,
        "loop_mount": True,
        "mount_namespace": True,
        "mount_options": sorted(observed_options),
        "persistent_filesystem": persistent_filesystem,
        "private_mount_propagation": True,
        "size_bytes": STATE_BYTES,
    }


def collect() -> dict[str, Any]:
    if os.geteuid() != 0:
        raise CollectionError("guest fingerprint collection requires root")
    if not _safe_interpreter():
        raise CollectionError("guest fingerprint collector requires Python -B -I")
    _validated_tmpdir()
    inventory, packages = _installed_packages()
    automatic_package_updates = _automatic_package_updates()
    python, stdlib_root = _python_runtime()
    python["stdlib_tree"] = _stdlib_tree(stdlib_root)
    tools = _tools()
    uname = os.uname()
    if (
        RUNTIME_VALUE.fullmatch(uname.release) is None
        or RUNTIME_VALUE.fullmatch(uname.machine) is None
    ):
        raise CollectionError("kernel metadata is unsafe")
    cgroup, resources = _cgroup_probe()
    user_namespaces = _user_namespace_probe()
    filesystems = _filesystems()
    writable_state = _writable_state_probe()
    final_inventory, final_packages = _installed_packages()
    final_tools = _tools()
    if (inventory, packages) != (final_inventory, final_packages) or tools != final_tools:
        raise CollectionError("guest runtime changed during collection")
    return {
        "installed_package_inventory": inventory,
        "isolation": {
            "cgroup_v2": cgroup,
            "filesystems": filesystems,
            "resource_envelope": resources,
            "user_namespaces": user_namespaces,
            "writable_state": writable_state,
        },
        "packages": packages,
        "runtime": {
            "automatic_package_updates": automatic_package_updates,
            "kernel": {"machine": uname.machine, "release": uname.release},
            "python": python,
        },
        "tools": tools,
    }


def _safe_interpreter() -> bool:
    return bool(sys.flags.isolated and sys.dont_write_bytecode)


def main() -> int:
    try:
        observation = collect()
        rendered = json.dumps(observation, indent=2, sort_keys=True) + "\n"
        if len(rendered.encode("utf-8")) > MAX_OUTPUT_BYTES:
            raise CollectionError("normalized guest observation exceeds one MiB")
    except Exception:
        print('{"error":"evaluator_guest_collection_failed"}', file=sys.stderr)
        return 2
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
