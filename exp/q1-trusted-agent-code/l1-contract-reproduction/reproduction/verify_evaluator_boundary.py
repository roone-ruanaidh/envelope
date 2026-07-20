"""Fail closed unless a normalized q1-l1-evaluator observation exactly matches its authority.

This verifier is deliberately offline. It reads one public-safe JSON observation from
``--observation`` (or stdin), compares it to ``evaluator-authority.json``, and emits a
report that contains only authority-derived paths and mismatch classes. It never
invokes Lima, a guest command, a package manager, or an isolation mechanism.

The collector must normalize the single workspace-parent mount to the literal role
``workspace-parent`` and reject every non-dynamic Lima field not represented by the
authority. It may omit only the instance directory, live ports and PIDs, SSH
configuration and identity paths, LimaHome, host OS/architecture, and the host
username, home, and uid. It must retain the ordered architecture-matching image list;
``base_image`` is its first entry. Port-forward and DNS fields are absent from the
reviewed config; they are not implicit defaults.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parent
AUTHORITY_PATH = ROOT / "evaluator-authority.json"
PACKAGE_AUTHORITY_PATH = ROOT / "apt-packages.txt"
AUTHORITY_SHA256 = "a8c2cf0ff21c45d957dbe2206c34e1c27c73e49a0943a65c031f012645dc5f4d"
AUTHORITY_SCHEMA_SHA256 = "2e7cd8d28d10d1cf0cc04cc99642b3d5597a2162425b5ed050d31e90a08772ef"
MAX_INPUT_BYTES = 1024 * 1024
MAX_INTEGER_DIGITS = 64
MAX_JSON_DEPTH = 32
MAX_JSON_ENTRIES = 10_000
MAX_KEY_CHARACTERS = 128
MAX_STRING_CHARACTERS = 4096
MAX_REPORTED_MISMATCHES = 128
SAFE_AUTHORITY_KEY = re.compile(r"^[A-Za-z0-9_.-]+$")
REQUIRED_AUTHORITY_PATHS = (
    ("schema_version",),
    ("instance", "name"),
    ("instance", "status"),
    ("config", "mounts"),
    ("base_image", "digest"),
    ("packages",),
    ("installed_package_inventory", "count"),
    ("installed_package_inventory", "sha256"),
    ("runtime", "automatic_package_updates", "masked_units"),
    ("runtime", "kernel", "release"),
    ("runtime", "kernel", "machine"),
    ("runtime", "python", "version"),
    ("runtime", "python", "build"),
    ("runtime", "python", "stdlib_tree", "count"),
    ("runtime", "python", "stdlib_tree", "sha256"),
    ("tools", "python", "sha256"),
    ("tools", "bubblewrap", "sha256"),
    ("tools", "losetup", "sha256"),
    ("tools", "unshare", "sha256"),
    ("tools", "mount", "sha256"),
    ("tools", "umount", "sha256"),
    ("tools", "mkfs_ext4", "sha256"),
    ("tools", "mkfs_ext4", "symlink_target"),
    ("isolation", "cgroup_v2", "controllers"),
    ("isolation", "cgroup_v2", "direct_child_control"),
    ("isolation", "user_namespaces", "creation_probe"),
    ("isolation", "user_namespaces", "unprivileged_clone"),
    ("isolation", "user_namespaces", "maximum"),
    ("isolation", "filesystems"),
    ("isolation", "resource_envelope"),
    ("isolation", "writable_state"),
)


class VerificationInputError(ValueError):
    """An authority or observation was not an admissible normalized document."""


def _reject_constant(_value: str) -> None:
    raise VerificationInputError("non-finite number")


def _parse_int(value: str) -> int:
    if len(value.removeprefix("-")) > MAX_INTEGER_DIGITS:
        raise VerificationInputError("integer exceeds normalized limit")
    return int(value)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise VerificationInputError("duplicate object member")
        value[key] = item
    return value


def _decode_json(payload: bytes) -> Any:
    if len(payload) > MAX_INPUT_BYTES:
        raise VerificationInputError("document exceeds one MiB")
    try:
        text = payload.decode("utf-8")
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
            parse_int=_parse_int,
        )
    except VerificationInputError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise VerificationInputError("document is not strict UTF-8 JSON") from exc
    _validate_json_shape(value)
    if not isinstance(value, dict):
        raise VerificationInputError("document root must be an object")
    return value


def _validate_json_shape(root: Any) -> None:
    entries = 0
    pending: list[tuple[Any, int]] = [(root, 0)]
    while pending:
        value, depth = pending.pop()
        if depth > MAX_JSON_DEPTH:
            raise VerificationInputError("document nesting exceeds limit")
        entries += 1
        if entries > MAX_JSON_ENTRIES:
            raise VerificationInputError("document entry count exceeds limit")
        if isinstance(value, dict):
            for key, item in value.items():
                if (
                    not isinstance(key, str)
                    or len(key) > MAX_KEY_CHARACTERS
                    or any(ord(character) < 0x20 for character in key)
                ):
                    raise VerificationInputError("object member name is not public-safe")
                pending.append((item, depth + 1))
        elif isinstance(value, list):
            pending.extend((item, depth + 1) for item in value)
        elif isinstance(value, str):
            if len(value) > MAX_STRING_CHARACTERS or any(
                ord(character) < 0x20 for character in value
            ):
                raise VerificationInputError("string is not public-safe")
        elif isinstance(value, float):
            if not math.isfinite(value):
                raise VerificationInputError("document contains a non-finite number")
        elif value is not None and type(value) not in {bool, int}:
            raise VerificationInputError("document contains a non-JSON value")


def _parse_package_authority(payload: bytes) -> dict[str, str]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VerificationInputError("package authority is not UTF-8") from exc
    packages: dict[str, str] = {}
    for line in text.splitlines():
        if not line or line.count("=") != 1:
            raise VerificationInputError("package authority is not canonical")
        package, version = line.split("=", 1)
        if not package or not version or package in packages:
            raise VerificationInputError("package authority is not canonical")
        packages[package] = version
    if list(packages) != sorted(packages):
        raise VerificationInputError("package authority is not sorted")
    return packages


def load_authority() -> tuple[dict[str, Any], str]:
    authority_payload = AUTHORITY_PATH.read_bytes()
    observed_digest = hashlib.sha256(authority_payload).hexdigest()
    if observed_digest != AUTHORITY_SHA256:
        raise VerificationInputError("evaluator authority digest mismatch")
    authority = _decode_json(authority_payload)
    if set(authority) != {
        "authority_schema_version",
        "expected_observation",
        "package_authority_sha256",
    } or authority["authority_schema_version"] != 1:
        raise VerificationInputError("evaluator authority envelope is invalid")
    expected = authority["expected_observation"]
    if not isinstance(expected, dict):
        raise VerificationInputError("evaluator authority expectation is invalid")
    if _schema_digest(expected) != AUTHORITY_SCHEMA_SHA256:
        raise VerificationInputError("evaluator authority schema mismatch")
    for value in _walk_object_keys(expected):
        if SAFE_AUTHORITY_KEY.fullmatch(value) is None:
            raise VerificationInputError("evaluator authority has an unsafe member name")
    for path in REQUIRED_AUTHORITY_PATHS:
        if not _has_path(expected, path):
            raise VerificationInputError("evaluator authority lacks a required field")

    package_payload = PACKAGE_AUTHORITY_PATH.read_bytes()
    package_digest = hashlib.sha256(package_payload).hexdigest()
    if package_digest != authority["package_authority_sha256"]:
        raise VerificationInputError("package authority digest mismatch")
    packages = _parse_package_authority(package_payload)
    if expected.get("packages") != packages:
        raise VerificationInputError("package authorities disagree")
    return expected, observed_digest


def _walk_object_keys(root: Any) -> list[str]:
    keys: list[str] = []
    pending = [root]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            keys.extend(value)
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
    return keys


def _schema_digest(root: Any) -> str:
    def shape(value: Any) -> Any:
        if isinstance(value, dict):
            return {"object": {key: shape(item) for key, item in value.items()}}
        if isinstance(value, list):
            return {"array": [shape(item) for item in value]}
        if value is None:
            return "null"
        return type(value).__name__

    canonical = json.dumps(
        shape(root),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return hashlib.sha256(canonical).hexdigest()


def _has_path(root: dict[str, Any], path: tuple[str, ...]) -> bool:
    value: Any = root
    for member in path:
        if not isinstance(value, dict) or member not in value:
            return False
        value = value[member]
    return True


def _append_mismatch(
    mismatches: list[dict[str, Any]],
    path: str,
    kind: str,
    **safe_details: Any,
) -> None:
    mismatches.append({"kind": kind, "path": path, **safe_details})


def _compare(expected: Any, observed: Any, path: str, mismatches: list[dict[str, Any]]) -> None:
    if type(expected) is not type(observed):
        _append_mismatch(
            mismatches,
            path,
            "type_mismatch",
            expected_type=type(expected).__name__,
            observed_type=type(observed).__name__,
        )
        return
    if isinstance(expected, dict):
        missing = sorted(set(expected) - set(observed))
        for key in missing:
            _append_mismatch(mismatches, f"{path}.{key}", "missing_member")
        unexpected_count = len(set(observed) - set(expected))
        if unexpected_count:
            _append_mismatch(
                mismatches,
                path,
                "unexpected_members",
                count=unexpected_count,
            )
        for key in sorted(set(expected) & set(observed)):
            _compare(expected[key], observed[key], f"{path}.{key}", mismatches)
        return
    if isinstance(expected, list):
        if len(expected) != len(observed):
            _append_mismatch(
                mismatches,
                path,
                "length_mismatch",
                expected_count=len(expected),
                observed_count=len(observed),
            )
        for index, (expected_item, observed_item) in enumerate(zip(expected, observed)):
            _compare(expected_item, observed_item, f"{path}[{index}]", mismatches)
        return
    if expected != observed:
        _append_mismatch(mismatches, path, "value_mismatch")


def verify_bytes(payload: bytes) -> dict[str, Any]:
    expected, authority_digest = load_authority()
    observed = _decode_json(payload)
    mismatches: list[dict[str, Any]] = []
    _compare(expected, observed, "$", mismatches)
    reported = mismatches[:MAX_REPORTED_MISMATCHES]
    return {
        "authority_sha256": authority_digest,
        "mismatch_count": len(mismatches),
        "mismatches": reported,
        "mismatches_truncated": len(reported) != len(mismatches),
        "passed": not mismatches,
        "schema_version": 1,
    }


def _read_observation(source: str) -> bytes:
    if source == "-":
        payload = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    else:
        with Path(source).open("rb") as stream:
            payload = stream.read(MAX_INPUT_BYTES + 1)
    if len(payload) > MAX_INPUT_BYTES:
        raise VerificationInputError("observation exceeds one MiB")
    return payload


def _error_report(code: str) -> dict[str, Any]:
    return {
        "authority_sha256": AUTHORITY_SHA256,
        "error": code,
        "passed": False,
        "schema_version": 1,
    }


def _render(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--observation",
        default="-",
        help="normalized public-safe JSON file, or '-' for stdin (default)",
    )
    parser.add_argument("--report", type=Path, help="optional JSON report destination")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = verify_bytes(_read_observation(args.observation))
        return_code = 0 if report["passed"] else 1
    except VerificationInputError:
        report = _error_report("observation_or_authority_invalid")
        return_code = 2
    except OSError:
        report = _error_report("input_or_report_unavailable")
        return_code = 2

    rendered = _render(report)
    if args.report is not None:
        try:
            args.report.write_text(rendered, encoding="utf-8")
        except OSError:
            print(_render(_error_report("report_unavailable")), end="", file=sys.stderr)
            return 2
    print(rendered, end="")
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
