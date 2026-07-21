"""Create and verify the exact candidate source transfer artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Sequence


MANIFEST_VERSION = 1
EXCLUDED_TOP_LEVEL = frozenset({".git", ".venv"})
MAX_TRANSFER_ENTRIES = 10_000
MAX_REGULAR_FILE_BYTES = 16 * 1024 * 1024
MAX_REGULAR_FILE_TOTAL_BYTES = 128 * 1024 * 1024
MAX_PATH_DEPTH = 32
MAX_PATH_BYTES = 1_024
MAX_MANIFEST_BYTES = 8 * 1024 * 1024
UNSAFE_PUBLIC_PATH_PATTERNS = (
    re.compile(
        r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?"
        r"-----END [A-Z0-9 ]*PRIVATE KEY-----",
        re.DOTALL,
    ),
    re.compile(r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"(?i:authorization\s*:\s*bearer\s+)[A-Za-z0-9._~+/=-]{12,}"),
)
FORBIDDEN_CONTROL_PARTS = frozenset({".agents", ".codex"})
FORBIDDEN_CONTROL_NAMES = frozenset({"AGENTS.md", "AGENTS.override.md"})


class TransferError(RuntimeError):
    """The candidate tree or transfer artifact is inadmissible."""


def _excluded(relative: PurePosixPath) -> bool:
    parts = relative.parts
    return bool(
        parts
        and (
            parts[0] in EXCLUDED_TOP_LEVEL
            or (len(parts) >= 2 and parts[0] == "public" and parts[1] == "contract")
        )
    )


def _assert_public_safe_path(relative: PurePosixPath) -> None:
    rendered = relative.as_posix()
    if any(pattern.search(rendered) for pattern in UNSAFE_PUBLIC_PATH_PATTERNS):
        raise TransferError("candidate source contains a credential-shaped path")


def _same_entry(before: os.stat_result, after: os.stat_result) -> bool:
    return (
        _same_entry_identity(before, after)
        and before.st_mode == after.st_mode
        and before.st_ctime_ns == after.st_ctime_ns
    )


def _same_entry_identity(before: os.stat_result, after: os.stat_result) -> bool:
    return (
        before.st_dev == after.st_dev
        and before.st_ino == after.st_ino
        and before.st_uid == after.st_uid
        and before.st_gid == after.st_gid
        and before.st_nlink == after.st_nlink
        and before.st_size == after.st_size
        and before.st_mtime_ns == after.st_mtime_ns
    )


def _open_owned_regular(
    directory_fd: int,
    name: str,
    relative: PurePosixPath,
    observed: os.stat_result,
) -> tuple[int, os.stat_result]:
    """Open an owned regular file while preserving even a mode with no read bits."""

    flags = os.O_RDONLY | os.O_NOFOLLOW
    original_mode = stat.S_IMODE(observed.st_mode)
    try:
        source_fd = os.open(name, flags, dir_fd=directory_fd)
    except PermissionError:
        pass
    except OSError as exc:
        raise TransferError(f"candidate file changed during transfer: {relative}") from exc
    else:
        opened = os.fstat(source_fd)
        if not stat.S_ISREG(opened.st_mode) or not _same_entry(observed, opened):
            os.close(source_fd)
            raise TransferError(f"candidate file changed during transfer: {relative}")
        return source_fd, opened

    readable_mode = original_mode | stat.S_IRUSR
    try:
        os.chmod(
            name,
            readable_mode,
            dir_fd=directory_fd,
            follow_symlinks=False,
        )
    except OSError as exc:
        raise TransferError(f"candidate file cannot be read for transfer: {relative}") from exc

    source_fd: int | None = None
    try:
        source_fd = os.open(name, flags, dir_fd=directory_fd)
        opened = os.fstat(source_fd)
        if (
            not stat.S_ISREG(opened.st_mode)
            or not _same_entry_identity(observed, opened)
            or stat.S_IMODE(opened.st_mode) != readable_mode
        ):
            raise TransferError(f"candidate file changed during transfer: {relative}")
        os.fchmod(source_fd, original_mode)
        restored = os.fstat(source_fd)
        if (
            not _same_entry_identity(observed, restored)
            or stat.S_IMODE(restored.st_mode) != original_mode
        ):
            raise TransferError(f"candidate file mode could not be restored: {relative}")
        return source_fd, restored
    except Exception:
        if source_fd is None:
            try:
                os.chmod(
                    name,
                    original_mode,
                    dir_fd=directory_fd,
                    follow_symlinks=False,
                )
            except OSError:
                pass
        else:
            try:
                os.fchmod(source_fd, original_mode)
            except OSError:
                pass
            os.close(source_fd)
        raise


def _validate_path_envelope(relative: PurePosixPath) -> None:
    if relative.name in FORBIDDEN_CONTROL_NAMES or any(
        part in FORBIDDEN_CONTROL_PARTS for part in relative.parts
    ):
        raise TransferError(f"candidate source contains a control path: {relative}")
    if len(relative.parts) > MAX_PATH_DEPTH:
        raise TransferError(f"candidate path exceeds maximum depth: {relative}")
    try:
        path_bytes = len(os.fsencode(relative.as_posix()))
    except UnicodeEncodeError as exc:
        raise TransferError(
            f"candidate path cannot be represented by the filesystem: {relative}"
        ) from exc
    if path_bytes > MAX_PATH_BYTES:
        raise TransferError(f"candidate path exceeds maximum byte length: {relative}")


def _manifest_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _assert_manifest_size(manifest: dict[str, Any]) -> None:
    if len(_manifest_bytes(manifest)) > MAX_MANIFEST_BYTES:
        raise TransferError("transfer manifest exceeds maximum byte length")


def _stage_candidate(
    root: Path,
    staging: Path,
    *,
    owner_uid: int | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    require_provisioner_owned_exclusions = owner_uid is not None
    staging.mkdir(mode=0o700)
    files: list[dict[str, Any]] = []
    entry_count = 0
    total_file_bytes = 0

    def visit(directory_fd: int, destination: Path, relative_directory: PurePosixPath) -> None:
        nonlocal entry_count, total_file_bytes
        observed: list[tuple[str, os.stat_result]] = []
        with os.scandir(directory_fd) as entries:
            for entry in entries:
                relative = relative_directory / entry.name
                if _excluded(relative):
                    if (
                        require_provisioner_owned_exclusions
                        and entry.stat(follow_symlinks=False).st_uid == owner_uid
                    ):
                        raise TransferError(
                            f"excluded candidate path must be provisioner-owned: {relative}"
                        )
                    continue
                entry_count += 1
                if entry_count > MAX_TRANSFER_ENTRIES:
                    raise TransferError("candidate source exceeds maximum entry count")
                _validate_path_envelope(relative)
                entry_stat = entry.stat(follow_symlinks=False)
                if entry_stat.st_uid != owner_uid:
                    raise TransferError(f"candidate source entry has the wrong owner: {relative}")
                if stat.S_ISREG(entry_stat.st_mode):
                    if entry_stat.st_size > MAX_REGULAR_FILE_BYTES:
                        raise TransferError(
                            f"candidate file exceeds maximum byte length: {relative}"
                        )
                    total_file_bytes += entry_stat.st_size
                    if total_file_bytes > MAX_REGULAR_FILE_TOTAL_BYTES:
                        raise TransferError("candidate source exceeds maximum regular-file bytes")
                observed.append((entry.name, entry_stat))
        observed.sort(key=lambda item: item[0])
        for name, entry_stat in observed:
            relative = relative_directory / name
            _assert_public_safe_path(relative)
            if stat.S_ISLNK(entry_stat.st_mode):
                raise TransferError(f"candidate source contains a symbolic link: {relative}")
            if stat.S_ISDIR(entry_stat.st_mode):
                try:
                    child_fd = os.open(
                        name,
                        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                        dir_fd=directory_fd,
                    )
                except OSError as exc:
                    raise TransferError(
                        f"candidate directory changed during transfer: {relative}"
                    ) from exc
                try:
                    if not _same_entry(entry_stat, os.fstat(child_fd)):
                        raise TransferError(
                            f"candidate directory changed during transfer: {relative}"
                        )
                    child_destination = destination / name
                    child_destination.mkdir(mode=0o700)
                    visit(child_fd, child_destination, relative)
                finally:
                    os.close(child_fd)
            elif stat.S_ISREG(entry_stat.st_mode):
                if entry_stat.st_nlink != 1:
                    raise TransferError(
                        f"candidate source contains a multiply-linked file: {relative}"
                    )
                source_fd, opened = _open_owned_regular(
                    directory_fd,
                    name,
                    relative,
                    entry_stat,
                )
                digest = hashlib.sha256()
                destination_path = destination / name
                try:
                    size = 0
                    with os.fdopen(source_fd, "rb", closefd=False) as source, destination_path.open(
                        "xb"
                    ) as output:
                        while chunk := source.read(1024 * 1024):
                            output.write(chunk)
                            digest.update(chunk)
                            size += len(chunk)
                    finished = os.fstat(source_fd)
                    if size != opened.st_size or not _same_entry(opened, finished):
                        raise TransferError(f"candidate file changed during transfer: {relative}")
                finally:
                    os.close(source_fd)
                files.append(
                    {
                        "mode": stat.S_IMODE(entry_stat.st_mode),
                        "path": relative.as_posix(),
                        "sha256": digest.hexdigest(),
                        "size": size,
                    }
                )
            else:
                raise TransferError(f"candidate source contains a special file: {relative}")

    try:
        root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError as exc:
        raise TransferError(f"candidate root is not a directory: {root}") from exc
    try:
        root_stat = os.fstat(root_fd)
        if owner_uid is None:
            owner_uid = root_stat.st_uid
        if (
            not isinstance(owner_uid, int)
            or isinstance(owner_uid, bool)
            or owner_uid < 0
            or root_stat.st_uid != owner_uid
        ):
            raise TransferError("candidate root has the wrong owner")
        visit(root_fd, staging, PurePosixPath())
    finally:
        os.close(root_fd)
    files.sort(key=lambda record: record["path"])
    manifest = {"files": files, "version": MANIFEST_VERSION}
    _assert_manifest_size(manifest)
    return manifest


def build_manifest(root: Path, *, owner_uid: int | None = None) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="q1-l1-candidate-manifest-") as temporary:
        return _stage_candidate(root, Path(temporary) / "staging", owner_uid=owner_uid)


def _write_new_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(_manifest_bytes(value))


def export_candidate(
    root: Path,
    archive: Path,
    manifest_path: Path,
    *,
    owner_uid: int | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    with tempfile.TemporaryDirectory(prefix="q1-l1-candidate-export-") as temporary:
        staging = Path(temporary) / "staging"
        manifest = _stage_candidate(root, staging, owner_uid=owner_uid)
        archive.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive, mode="x", format=tarfile.PAX_FORMAT) as bundle:
            for record in manifest["files"]:
                info = tarfile.TarInfo(record["path"])
                info.size = record["size"]
                info.mode = record["mode"]
                info.mtime = 0
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                with staging.joinpath(*PurePosixPath(record["path"]).parts).open("rb") as stream:
                    bundle.addfile(info, stream)
    _write_new_json(manifest_path, manifest)
    return manifest


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as stream:
            encoded = stream.read(MAX_MANIFEST_BYTES + 1)
        if len(encoded) > MAX_MANIFEST_BYTES:
            raise TransferError("transfer manifest exceeds maximum byte length")
        value = json.loads(encoded.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TransferError(f"cannot read transfer manifest: {exc}") from exc
    if not isinstance(value, dict) or set(value) != {"files", "version"}:
        raise TransferError("transfer manifest must contain exactly files and version")
    if value["version"] != MANIFEST_VERSION or not isinstance(value["files"], list):
        raise TransferError("unsupported transfer manifest")
    previous = ""
    represented_entries: set[str] = set()
    total_file_bytes = 0
    for item in value["files"]:
        if not isinstance(item, dict) or set(item) != {"mode", "path", "sha256", "size"}:
            raise TransferError("invalid transfer manifest file record")
        relative = PurePosixPath(item["path"]) if isinstance(item["path"], str) else None
        if (
            relative is None
            or relative.is_absolute()
            or not relative.parts
            or any(part in {"", ".", ".."} for part in relative.parts)
            or relative.as_posix() != item["path"]
            or _excluded(relative)
        ):
            raise TransferError(f"invalid transfer path: {item.get('path')!r}")
        _validate_path_envelope(relative)
        _assert_public_safe_path(relative)
        for depth in range(1, len(relative.parts) + 1):
            represented_entries.add(PurePosixPath(*relative.parts[:depth]).as_posix())
            if len(represented_entries) > MAX_TRANSFER_ENTRIES:
                raise TransferError("transfer manifest exceeds maximum entry count")
        if item["path"] <= previous:
            raise TransferError("transfer manifest paths must be unique and sorted")
        previous = item["path"]
        if (
            not isinstance(item["mode"], int)
            or isinstance(item["mode"], bool)
            or not 0 <= item["mode"] <= 0o7777
            or not isinstance(item["size"], int)
            or isinstance(item["size"], bool)
            or item["size"] < 0
            or not isinstance(item["sha256"], str)
            or len(item["sha256"]) != 64
            or any(character not in "0123456789abcdef" for character in item["sha256"])
        ):
            raise TransferError(f"invalid transfer metadata for {item['path']}")
        if item["size"] > MAX_REGULAR_FILE_BYTES:
            raise TransferError(f"transfer file exceeds maximum byte length: {item['path']}")
        total_file_bytes += item["size"]
        if total_file_bytes > MAX_REGULAR_FILE_TOTAL_BYTES:
            raise TransferError("transfer manifest exceeds maximum regular-file bytes")
    return value


def extract_candidate(archive: Path, manifest_path: Path, root: Path) -> dict[str, Any]:
    manifest = _load_manifest(manifest_path)
    expected = manifest["files"]
    root.mkdir(parents=True, exist_ok=False)
    try:
        with tarfile.open(archive, mode="r|*") as bundle:
            member_count = 0
            while True:
                member = bundle.next()
                bundle.members.clear()
                if member is None:
                    break
                member_count += 1
                if member_count > MAX_TRANSFER_ENTRIES:
                    raise TransferError("archive exceeds maximum entry count")
                expected_index = member_count - 1
                if (
                    expected_index >= len(expected)
                    or member.name != expected[expected_index]["path"]
                ):
                    raise TransferError(
                        "archive members do not exactly match the transfer manifest"
                    )
                record = expected[expected_index]
                if (
                    not member.isreg()
                    or member.size != record["size"]
                    or stat.S_IMODE(member.mode) != record["mode"]
                ):
                    raise TransferError(f"invalid archive member: {member.name}")
                destination = root.joinpath(*PurePosixPath(member.name).parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                source = bundle.extractfile(member)
                if source is None:
                    raise TransferError(f"archive member has no content: {member.name}")
                with source, destination.open("xb") as output:
                    shutil.copyfileobj(source, output)
                destination.chmod(record["mode"])
            if member_count != len(expected):
                raise TransferError("archive members do not exactly match the transfer manifest")
        observed = build_manifest(root)
        if observed != manifest:
            raise TransferError("extracted candidate does not match the transfer manifest")
        return manifest
    except Exception:
        # The caller supplies a fresh, run-scoped root. Leaving a partial tree
        # would make later verification ambiguous.
        shutil.rmtree(root)
        raise


def verify_candidate(root: Path, manifest_path: Path) -> dict[str, Any]:
    expected = _load_manifest(manifest_path)
    observed = build_manifest(root)
    if observed != expected:
        raise TransferError("candidate tree does not match the transfer manifest")
    return observed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export")
    export_parser.add_argument("--root", type=Path, required=True)
    export_parser.add_argument("--archive", type=Path, required=True)
    export_parser.add_argument("--manifest", type=Path, required=True)

    extract_parser = subparsers.add_parser("extract")
    extract_parser.add_argument("--archive", type=Path, required=True)
    extract_parser.add_argument("--manifest", type=Path, required=True)
    extract_parser.add_argument("--root", type=Path, required=True)

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--root", type=Path, required=True)
    verify_parser.add_argument("--manifest", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "export":
            manifest = export_candidate(args.root, args.archive, args.manifest)
        elif args.command == "extract":
            manifest = extract_candidate(args.archive, args.manifest, args.root)
        else:
            manifest = verify_candidate(args.root, args.manifest)
    except (OSError, tarfile.TarError, TransferError) as exc:
        print(json.dumps({"passed": False, "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({"file_count": len(manifest["files"]), "passed": True}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
