"""Verify the proposed e1 freeze inventory and visibility boundary."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "freeze-manifest.json"
EXCLUDED_PARTS = frozenset(
    {".git", ".mypy_cache", ".typing-venv", "__pycache__", "build"}
)
EXCLUDED_FILES = frozenset({"freeze-manifest.json", ".DS_Store"})


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _repository_files() -> set[str]:
    files: set[str] = set()
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if not path.is_file() or path.name in EXCLUDED_FILES or path.suffix == ".pyc":
            continue
        files.add(relative.as_posix())
    return files


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _governing_path(binding: dict[str, Any], *, label: str) -> Path:
    raw_path = binding.get("path")
    _require(isinstance(raw_path, str), f"{label} path must be a string")
    assert isinstance(raw_path, str)
    path = Path(raw_path)
    if not path.is_absolute():
        path = ROOT / path
    path = path.resolve()
    _require(path.is_file(), f"governing {label} is missing")
    _require(binding.get("sha256") == _sha256(path), f"{label} hash drift")
    return path


def verify() -> dict[str, Any]:
    manifest = json.loads(
        MANIFEST_PATH.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
    )
    _require(isinstance(manifest, dict), "manifest must be a JSON object")
    _require(manifest.get("schema_version") == 1, "unsupported manifest schema")
    _require(manifest.get("experiment_id") == "e1", "manifest experiment mismatch")
    _require(
        manifest.get("status") in {"proposed_for_signoff", "frozen"},
        "invalid manifest status",
    )
    _require(
        manifest.get("frozen") is (manifest.get("status") == "frozen"),
        "frozen flag and status disagree",
    )

    artifacts = manifest.get("artifacts")
    _require(isinstance(artifacts, list), "artifacts must be an array")
    artifact_paths: set[str] = set()
    for entry in artifacts:
        _require(isinstance(entry, dict), "artifact entry must be an object")
        relative = entry.get("path")
        _require(isinstance(relative, str), "artifact path must be a string")
        _require(relative not in artifact_paths, f"duplicate artifact {relative!r}")
        path = ROOT / relative
        _require(path.is_file(), f"artifact does not exist: {relative}")
        _require(path.resolve().is_relative_to(ROOT), f"artifact escapes repository: {relative}")
        _require(entry.get("size_bytes") == path.stat().st_size, f"size drift: {relative}")
        _require(entry.get("sha256") == _sha256(path), f"hash drift: {relative}")
        artifact_paths.add(relative)

    expected_paths = _repository_files()
    _require(
        artifact_paths == expected_paths,
        "artifact inventory drift: "
        f"missing={sorted(expected_paths - artifact_paths)!r}, "
        f"extra={sorted(artifact_paths - expected_paths)!r}",
    )

    public_bundle = manifest.get("public_bundle")
    sealed_bundle = manifest.get("sealed_bundle")
    _require(isinstance(public_bundle, list), "public_bundle must be an array")
    _require(isinstance(sealed_bundle, list), "sealed_bundle must be an array")
    public_paths = set(public_bundle)
    sealed_paths = set(sealed_bundle)
    expected_public = {path for path in artifact_paths if path.startswith("public/contract/")}
    _require(public_paths == expected_public, "public bundle does not equal public contract files")
    _require(sealed_paths == artifact_paths - public_paths, "sealed bundle inventory mismatch")
    _require(not public_paths & sealed_paths, "public and sealed bundles overlap")

    instructions = manifest.get("governing_instructions")
    _require(isinstance(instructions, dict), "governing_instructions must be an object")
    _governing_path(instructions, label="AGENTS.md")

    policy = manifest.get("governing_repository_policy")
    _require(isinstance(policy, dict), "governing_repository_policy must be an object")
    policy_path = _governing_path(policy, label="repository README")
    _require(
        policy_path == ROOT.parents[1] / "README.md",
        "governing README is not at the repository root",
    )

    decisions = manifest.get("approved_decisions")
    _require(isinstance(decisions, list) and len(decisions) == 5, "five decisions required")
    _require(all(item.get("approved") is True for item in decisions), "unapproved decision")

    run = manifest.get("implementation_run")
    _require(isinstance(run, dict), "implementation_run must be an object")
    _require(run.get("model") == "gpt-5", "unexpected implementation model")
    budget = run.get("budget")
    _require(isinstance(budget, dict), "run budget must be an object")
    _require(budget.get("total_tokens") == 100_000, "unexpected run budget")
    _require(run.get("candidate_run_performed") is False, "candidate run already performed")

    ledger = manifest.get("cost_ledger")
    _require(isinstance(ledger, dict), "cost_ledger must be an object")
    required_fields = ledger.get("required_event_fields")
    _require(isinstance(required_fields, list), "ledger fields must be an array")
    _require(
        "experiment_id" in required_fields
        and "phase" in required_fields
        and "elapsed_ms" in required_fields,
        "ledger fields incomplete",
    )

    prompt = manifest.get("implementation_prompt")
    _require(isinstance(prompt, str) and bool(prompt.strip()), "implementation prompt is empty")
    assert isinstance(prompt, str)
    _require("evaluator" in prompt and "public/contract" in prompt, "prompt omits isolation boundary")

    return {
        "experiment_id": manifest["experiment_id"],
        "status": manifest["status"],
        "artifacts_verified": len(artifact_paths),
        "public_artifacts": len(public_paths),
        "sealed_artifacts": len(sealed_paths),
        "passed": True,
    }


def main() -> int:
    try:
        result = verify()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"passed": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
