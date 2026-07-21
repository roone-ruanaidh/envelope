"""Create and verify Q1/L7's separately indexed public evidence projection."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
from pathlib import Path, PurePosixPath
from typing import Any, Sequence


LOOP_ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "20260721T181955Z-4de70100"
CONTRACT_COMMIT = "3ca254222aac83c7054ba38b29bba7348f2ec536"
PUBLIC_EVIDENCE = LOOP_ROOT / "evidence" / RUN_ID
PUBLIC_RESULT = LOOP_ROOT / "RESULT.md"
PRIVATE_ROOT = (
    Path.home()
    / ".local"
    / "share"
    / "envelope"
    / "q1-private-evidence"
    / RUN_ID
)
PRIVATE_EVIDENCE = PRIVATE_ROOT / "evidence"
PRIVATE_RESULT = PRIVATE_ROOT / "RESULT.md"
SUPERSEDED_PUBLIC = PRIVATE_ROOT / "superseded-public-projection-v1"
STAGING = LOOP_ROOT / "build" / f"public-projection-{RUN_ID}"
SOURCE_INDEX = "evidence-index.json"
SOURCE_COMPLETION = "execution-completion.json"
PROJECTION_INDEX = "projection-evidence-index.json"
PROJECTION_COMPLETION = "projection-completion.json"
MASKED_KEY = re.compile(
    rb"(?<![A-Za-z0-9_-])sk-(?:proj-|svcacct-)?\*{20,}"
    rb"[A-Za-z0-9_-]{4}(?![A-Za-z0-9_-])"
)
FULL_KEY = re.compile(
    rb"(?<![A-Za-z0-9_-])sk-(?:proj-|svcacct-)?"
    rb"[A-Za-z0-9_-]{20,}(?![A-Za-z0-9_-])"
)
PRIVATE_KEY = re.compile(
    rb"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
    re.DOTALL,
)
BEARER = re.compile(rb"(?i:authorization\s*:\s*bearer\s+)[A-Za-z0-9._~+/=-]{12,}")
REPLACEMENT = b"[REDACTED:OPENAI_KEY_FINGERPRINT]"
EXPECTED_CHANGED_PATH = "agent/attempt-1/events.jsonl"
EXPECTED_REDACTIONS = 12


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} is not a JSON object")
    return value


def _relative_path(value: Any) -> PurePosixPath:
    if not isinstance(value, str):
        raise ValueError("evidence path is not a string")
    relative = PurePosixPath(value)
    if relative.is_absolute() or not relative.parts or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise ValueError("evidence path escapes its root")
    return relative


def _source_inventory(evidence: Path, result: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if evidence.is_symlink() or result.is_symlink():
        raise ValueError("source evidence contains a symbolic link")
    index = _load_object(evidence / SOURCE_INDEX)
    completion = _load_object(evidence / SOURCE_COMPLETION)
    if index.get("version") != 3 or not isinstance(index.get("files"), list):
        raise ValueError("source evidence index is invalid")
    if (
        completion.get("version") != 1
        or completion.get("kind") != "execution"
        or completion.get("run_id") != RUN_ID
        or completion.get("contract_commit") != CONTRACT_COMMIT
        or completion.get("index_path") != SOURCE_INDEX
        or completion.get("index_sha256") != _sha256(evidence / SOURCE_INDEX)
    ):
        raise ValueError("source execution receipt does not bind the expected run")
    indexed: set[str] = set()
    for record in index["files"]:
        if not isinstance(record, dict) or set(record) != {"path", "sha256", "size"}:
            raise ValueError("source inventory record is invalid")
        relative = _relative_path(record["path"])
        name = relative.as_posix()
        path = evidence.joinpath(*relative.parts)
        if name in indexed or path.is_symlink() or not path.is_file():
            raise ValueError("source inventory is not one-to-one")
        if record["sha256"] != _sha256(path) or record["size"] != path.stat().st_size:
            raise ValueError(f"source evidence changed: {name}")
        indexed.add(name)
    source_paths = list(evidence.rglob("*"))
    if any(path.is_symlink() for path in source_paths):
        raise ValueError("source evidence contains a symbolic link")
    observed = {
        path.relative_to(evidence).as_posix() for path in source_paths if path.is_file()
    }
    if observed != indexed | {SOURCE_INDEX, SOURCE_COMPLETION}:
        raise ValueError("source evidence inventory is not exact")
    if result.read_bytes() != (evidence / "pending-RESULT.md").read_bytes():
        raise ValueError("source RESULT.md does not match its indexed projection")
    return index, completion


def _assert_public(path: Path) -> None:
    for item in path.rglob("*"):
        if item.is_symlink() or (not item.is_dir() and not item.is_file()):
            raise ValueError("projection contains a non-regular path")
        relative = item.relative_to(path)
        if "source-integrity" in relative.parts or item.name in {
            SOURCE_INDEX,
            SOURCE_COMPLETION,
        }:
            raise ValueError("projection contains a private source commitment")
        if not item.is_file():
            continue
        data = item.read_bytes()
        if MASKED_KEY.search(data) or FULL_KEY.search(data) or PRIVATE_KEY.search(data) or BEARER.search(data):
            raise ValueError(f"projection is not public-safe: {item.name}")


def _verify_public_result(evidence: Path, result: Path) -> None:
    if result.is_symlink() or not result.is_file():
        raise ValueError("public RESULT.md is unavailable")
    if result.read_bytes() != (evidence / "pending-RESULT.md").read_bytes():
        raise ValueError("public RESULT.md changed from the closed result")
    data = result.read_bytes()
    if MASKED_KEY.search(data) or FULL_KEY.search(data) or PRIVATE_KEY.search(data) or BEARER.search(data):
        raise ValueError("public RESULT.md is not public-safe")


def _atomic_copy(source: Path, destination: Path) -> None:
    temporary = destination.with_name(f".{destination.name}.projection-tmp")
    source_data = source.read_bytes()
    if temporary.is_symlink():
        raise ValueError("public RESULT.md temporary path is a symbolic link")
    if temporary.exists():
        if not temporary.is_file():
            raise ValueError("public RESULT.md temporary path is not a regular file")
        if temporary.read_bytes() == source_data:
            os.replace(temporary, destination)
            return
        temporary.unlink()
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        view = memoryview(source_data)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short write while projecting RESULT.md")
            view = view[written:]
        os.fsync(descriptor)
    except BaseException:
        os.close(descriptor)
        temporary.unlink(missing_ok=True)
        raise
    else:
        os.close(descriptor)
    os.replace(temporary, destination)


def _inventory(root: Path, *, excluded: set[str]) -> dict[str, Any]:
    files = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative in excluded:
            continue
        files.append(
            {
                "path": relative,
                "sha256": _sha256(path),
                "size": path.stat().st_size,
            }
        )
    return {"files": files, "version": 1}


def _projection_readme() -> bytes:
    return (
        "# Q1/L7 public evidence projection\n\n"
        "This directory is a separately indexed projection of the closed Q1/L7 run. "
        "The raw terminal tree remains private and unchanged. The only content change "
        "replaces provider-masked API-key fingerprints; disposition and observed values "
        "are unchanged.\n\n"
        "The public index and receipt bind only these sanitized bytes. They deliberately "
        "publish no hash, size, receipt, or aggregate commitment derived from the changed "
        "raw file because its masked credential suffix has low entropy. Exact transform "
        "verification therefore requires the retained private indexed source.\n"
    ).encode("utf-8")


def build_projection(source: Path, result: Path, destination: Path) -> None:
    index, _ = _source_inventory(source, result)
    if destination.exists() or destination.is_symlink():
        raise ValueError("projection destination already exists")
    destination.mkdir(parents=True, mode=0o755)
    changed = []
    total_redactions = 0
    source_records = {record["path"]: record for record in index["files"]}
    for name in source_records:
        relative = _relative_path(name)
        source_path = source.joinpath(*relative.parts)
        data = source_path.read_bytes()
        projected, count = MASKED_KEY.subn(REPLACEMENT, data)
        target = destination.joinpath(*relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(projected)
        if count:
            total_redactions += count
            changed.append(
                {
                    "occurrences": count,
                    "path": name,
                }
            )
    (destination / "PROJECTION.md").write_bytes(_projection_readme())
    manifest = {
        "kind": "public-safe-redacted-projection",
        "projection": {
            "changed_files": changed,
            "redactions": total_redactions,
            "replacement": REPLACEMENT.decode("ascii"),
        },
        "source": {
            "contract_commit": CONTRACT_COMMIT,
            "raw_retention": "private local storage outside the repository",
            "run_id": RUN_ID,
            "verification_boundary": "exact transform requires retained private evidence",
        },
        "version": 2,
    }
    (destination / "projection.json").write_bytes(_json_bytes(manifest))
    projection_index = _inventory(
        destination,
        excluded={PROJECTION_INDEX, PROJECTION_COMPLETION},
    )
    (destination / PROJECTION_INDEX).write_bytes(_json_bytes(projection_index))
    projection_completion = {
        "contract_commit": CONTRACT_COMMIT,
        "index_path": PROJECTION_INDEX,
        "index_sha256": _sha256(destination / PROJECTION_INDEX),
        "kind": "public-evidence-projection",
        "run_id": RUN_ID,
        "version": 2,
    }
    (destination / PROJECTION_COMPLETION).write_bytes(_json_bytes(projection_completion))
    _assert_public(destination)
    _verify_projection_against_source(destination, source, result)


def verify_projection(evidence: Path) -> None:
    manifest = _load_object(evidence / "projection.json")
    index = _load_object(evidence / PROJECTION_INDEX)
    completion = _load_object(evidence / PROJECTION_COMPLETION)
    source = manifest.get("source")
    projection = manifest.get("projection")
    if (
        set(manifest) != {"kind", "projection", "source", "version"}
        or manifest.get("version") != 2
        or manifest.get("kind") != "public-safe-redacted-projection"
        or not isinstance(source, dict)
        or set(source)
        != {"contract_commit", "raw_retention", "run_id", "verification_boundary"}
        or source.get("run_id") != RUN_ID
        or source.get("contract_commit") != CONTRACT_COMMIT
        or source.get("raw_retention")
        != "private local storage outside the repository"
        or source.get("verification_boundary")
        != "exact transform requires retained private evidence"
        or not isinstance(projection, dict)
        or set(projection) != {"changed_files", "redactions", "replacement"}
    ):
        raise ValueError("projection source lineage is invalid")
    if index != _inventory(evidence, excluded={PROJECTION_INDEX, PROJECTION_COMPLETION}):
        raise ValueError("projection inventory changed")
    if (
        set(completion)
        != {"contract_commit", "index_path", "index_sha256", "kind", "run_id", "version"}
        or completion.get("version") != 2
        or completion.get("kind") != "public-evidence-projection"
        or completion.get("run_id") != RUN_ID
        or completion.get("contract_commit") != CONTRACT_COMMIT
        or completion.get("index_path") != PROJECTION_INDEX
        or completion.get("index_sha256") != _sha256(evidence / PROJECTION_INDEX)
    ):
        raise ValueError("projection completion receipt is invalid")
    changed_records = projection.get("changed_files")
    if not isinstance(changed_records, list):
        raise ValueError("projection changed-file map is invalid")
    if any(
        not isinstance(record, dict) or set(record) != {"occurrences", "path"}
        for record in changed_records
    ):
        raise ValueError("projection changed-file record is invalid")
    changed = {record["path"]: record for record in changed_records}
    if (
        len(changed_records) != 1
        or set(changed) != {EXPECTED_CHANGED_PATH}
        or changed[EXPECTED_CHANGED_PATH].get("occurrences") != EXPECTED_REDACTIONS
        or projection.get("redactions") != EXPECTED_REDACTIONS
        or projection.get("replacement") != REPLACEMENT.decode("ascii")
    ):
        raise ValueError("projection redaction count is invalid")
    _assert_public(evidence)


def _verify_projection_against_source(
    public: Path, source: Path, result: Path
) -> None:
    index, _ = _source_inventory(source, result)
    verify_projection(public)
    for record in index["files"]:
        relative = _relative_path(record["path"])
        expected = MASKED_KEY.sub(REPLACEMENT, source.joinpath(*relative.parts).read_bytes())
        if public.joinpath(*relative.parts).read_bytes() != expected:
            raise ValueError(
                f"projected evidence is not the exact source transform: {relative}"
            )


def _verify_private_retention(public: Path) -> None:
    _verify_projection_against_source(public, PRIVATE_EVIDENCE, PRIVATE_RESULT)


def project() -> None:
    if (PUBLIC_EVIDENCE / "projection.json").exists():
        if PRIVATE_EVIDENCE.exists() and not PRIVATE_RESULT.exists() and PUBLIC_RESULT.exists():
            _atomic_copy(PUBLIC_RESULT, PRIVATE_RESULT)
        verify_projection(PUBLIC_EVIDENCE)
        _verify_private_retention(PUBLIC_EVIDENCE)
        if (
            PUBLIC_RESULT.is_symlink()
            or not PUBLIC_RESULT.is_file()
            or PUBLIC_RESULT.read_bytes() != PRIVATE_RESULT.read_bytes()
        ):
            _atomic_copy(PRIVATE_RESULT, PUBLIC_RESULT)
        _verify_public_result(PUBLIC_EVIDENCE, PUBLIC_RESULT)
        return
    if PRIVATE_EVIDENCE.exists() and not PRIVATE_RESULT.exists() and PUBLIC_RESULT.exists():
        os.replace(PUBLIC_RESULT, PRIVATE_RESULT)
    if PRIVATE_EVIDENCE.exists():
        source = PRIVATE_EVIDENCE
        result = PRIVATE_RESULT
    elif PUBLIC_EVIDENCE.exists() and not (PUBLIC_EVIDENCE / "projection.json").exists():
        source = PUBLIC_EVIDENCE
        result = PUBLIC_RESULT
    else:
        raise ValueError("closed Q1/L7 source evidence is unavailable")
    if STAGING.is_symlink():
        raise ValueError("projection staging path is a symbolic link")
    if STAGING.exists():
        _verify_projection_against_source(STAGING, source, result)
    else:
        try:
            build_projection(source, result, STAGING)
        except BaseException:
            if STAGING.exists() and not STAGING.is_symlink():
                shutil.rmtree(STAGING)
            raise
    if not PRIVATE_EVIDENCE.exists():
        PRIVATE_ROOT.mkdir(parents=True, mode=0o700, exist_ok=True)
        os.replace(PUBLIC_EVIDENCE, PRIVATE_EVIDENCE)
        os.replace(PUBLIC_RESULT, PRIVATE_RESULT)
    PUBLIC_EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    os.replace(STAGING, PUBLIC_EVIDENCE)
    _atomic_copy(PRIVATE_RESULT, PUBLIC_RESULT)
    verify_projection(PUBLIC_EVIDENCE)
    _verify_private_retention(PUBLIC_EVIDENCE)
    _verify_public_result(PUBLIC_EVIDENCE, PUBLIC_RESULT)


def rebuild_projection() -> None:
    """Replace the unsafe v1 projection while retaining it outside the repository."""

    if not PRIVATE_EVIDENCE.exists() or not PRIVATE_RESULT.exists():
        raise ValueError("private Q1/L7 source evidence is unavailable")
    try:
        manifest = _load_object(PUBLIC_EVIDENCE / "projection.json")
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        manifest = {}
    if manifest.get("version") == 2:
        project()
        return
    if STAGING.exists() or STAGING.is_symlink():
        raise ValueError("projection staging path already exists")
    build_projection(PRIVATE_EVIDENCE, PRIVATE_RESULT, STAGING)
    if SUPERSEDED_PUBLIC.exists() or SUPERSEDED_PUBLIC.is_symlink():
        raise ValueError("superseded projection retention path already exists")
    if PUBLIC_EVIDENCE.exists() or PUBLIC_EVIDENCE.is_symlink():
        os.replace(PUBLIC_EVIDENCE, SUPERSEDED_PUBLIC)
    os.replace(STAGING, PUBLIC_EVIDENCE)
    _atomic_copy(PRIVATE_RESULT, PUBLIC_RESULT)
    verify_projection(PUBLIC_EVIDENCE)
    _verify_private_retention(PUBLIC_EVIDENCE)
    _verify_public_result(PUBLIC_EVIDENCE, PUBLIC_RESULT)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=("project", "rebuild", "verify", "verify-public"),
    )
    arguments = parser.parse_args(argv)
    if arguments.action == "project":
        project()
    elif arguments.action == "rebuild":
        rebuild_projection()
    elif arguments.action == "verify":
        verify_projection(PUBLIC_EVIDENCE)
        _verify_private_retention(PUBLIC_EVIDENCE)
        _verify_public_result(PUBLIC_EVIDENCE, PUBLIC_RESULT)
    else:
        verify_projection(PUBLIC_EVIDENCE)
        _verify_public_result(PUBLIC_EVIDENCE, PUBLIC_RESULT)
    print(
        json.dumps(
            {"evidence": str(PUBLIC_EVIDENCE.relative_to(LOOP_ROOT)), "status": "verified"},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
