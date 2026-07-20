"""Focused offline tests for the evaluator-boundary authority verifier."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest import mock


SCRIPT = Path(__file__).with_name("verify_evaluator_boundary.py")


def _load_verifier() -> ModuleType:
    specification = importlib.util.spec_from_file_location(
        "verify_evaluator_boundary", SCRIPT
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("could not load evaluator-boundary verifier")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


VERIFIER = _load_verifier()


def _expected() -> dict[str, object]:
    authority = json.loads(VERIFIER.AUTHORITY_PATH.read_text(encoding="utf-8"))
    return authority["expected_observation"]


def _payload(value: object) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _leaf_paths(value: object, path: tuple[object, ...] = ()) -> list[tuple[object, ...]]:
    if isinstance(value, dict):
        paths: list[tuple[object, ...]] = []
        for key, item in value.items():
            paths.extend(_leaf_paths(item, (*path, key)))
        return paths
    if isinstance(value, list):
        paths = []
        for index, item in enumerate(value):
            paths.extend(_leaf_paths(item, (*path, index)))
        return paths
    return [path]


def _replace_leaf(value: object, path: tuple[object, ...]) -> None:
    parent = value
    for member in path[:-1]:
        parent = parent[member]
    leaf = parent[path[-1]]
    if isinstance(leaf, bool):
        replacement = not leaf
    elif isinstance(leaf, int):
        replacement = leaf + 1
    elif isinstance(leaf, str):
        replacement = leaf + "-drift"
    else:
        replacement = "drift"
    parent[path[-1]] = replacement


class EvaluatorBoundaryVerifierTests(unittest.TestCase):
    def test_exact_observation_passes(self) -> None:
        report = VERIFIER.verify_bytes(_payload(_expected()))

        self.assertTrue(report["passed"])
        self.assertEqual(report["mismatch_count"], 0)
        self.assertEqual(report["mismatches"], [])

    def test_every_authority_leaf_is_load_bearing(self) -> None:
        expected = _expected()
        for path in _leaf_paths(expected):
            with self.subTest(path=path):
                observation = copy.deepcopy(expected)
                _replace_leaf(observation, path)
                self.assertFalse(VERIFIER.verify_bytes(_payload(observation))["passed"])

    def test_required_authority_paths_exist(self) -> None:
        expected = _expected()
        for path in VERIFIER.REQUIRED_AUTHORITY_PATHS:
            with self.subTest(path=path):
                self.assertTrue(VERIFIER._has_path(expected, path))

    def test_value_drift_is_rejected_without_echoing_value(self) -> None:
        observation = copy.deepcopy(_expected())
        observation["instance"]["status"] = "secret-local-state"

        report = VERIFIER.verify_bytes(_payload(observation))
        rendered = json.dumps(report, sort_keys=True)

        self.assertFalse(report["passed"])
        self.assertIn("$.instance.status", rendered)
        self.assertNotIn("secret-local-state", rendered)

    def test_unexpected_secret_member_is_not_named_or_echoed(self) -> None:
        observation = copy.deepcopy(_expected())
        observation["runtime"]["super_secret_password"] = "hunter2"

        report = VERIFIER.verify_bytes(_payload(observation))
        rendered = json.dumps(report, sort_keys=True)

        self.assertFalse(report["passed"])
        self.assertIn("unexpected_members", rendered)
        self.assertNotIn("super_secret_password", rendered)
        self.assertNotIn("hunter2", rendered)

    def test_extra_mount_is_rejected(self) -> None:
        observation = copy.deepcopy(_expected())
        observation["config"]["mounts"].append(
            {"role": "workspace-parent", "writable": True}
        )

        report = VERIFIER.verify_bytes(_payload(observation))

        self.assertFalse(report["passed"])
        self.assertEqual(report["mismatches"][0]["path"], "$.config.mounts")
        self.assertEqual(report["mismatches"][0]["kind"], "length_mismatch")

    def test_duplicate_member_is_invalid_input(self) -> None:
        with self.assertRaises(VERIFIER.VerificationInputError):
            VERIFIER.verify_bytes(b'{"schema_version":1,"schema_version":1}')

    def test_oversized_document_is_invalid_input(self) -> None:
        with self.assertRaises(VERIFIER.VerificationInputError):
            VERIFIER.verify_bytes(b" " * (VERIFIER.MAX_INPUT_BYTES + 1))

    def test_non_finite_number_is_invalid_input(self) -> None:
        with self.assertRaises(VERIFIER.VerificationInputError):
            VERIFIER.verify_bytes(b'{"schema_version":1e999}')

    def test_oversized_integer_is_invalid_input(self) -> None:
        payload = b'{"schema_version":' + b"9" * 5000 + b"}"
        with self.assertRaises(VERIFIER.VerificationInputError):
            VERIFIER.verify_bytes(payload)

    def test_control_character_is_invalid_input(self) -> None:
        with self.assertRaises(VERIFIER.VerificationInputError):
            VERIFIER.verify_bytes(b'{"schema_version":"line\\nfeed"}')

    def test_excessive_depth_is_invalid_input(self) -> None:
        value: object = 0
        for _ in range(VERIFIER.MAX_JSON_DEPTH + 1):
            value = [value]
        with self.assertRaises(VERIFIER.VerificationInputError):
            VERIFIER.verify_bytes(_payload({"schema_version": value}))

    def test_excessive_entry_count_is_invalid_input(self) -> None:
        value = {"schema_version": [0] * VERIFIER.MAX_JSON_ENTRIES}
        with self.assertRaises(VERIFIER.VerificationInputError):
            VERIFIER.verify_bytes(_payload(value))

    def test_authority_digest_tamper_is_rejected(self) -> None:
        with mock.patch.object(VERIFIER, "AUTHORITY_SHA256", "0" * 64):
            with self.assertRaises(VERIFIER.VerificationInputError):
                VERIFIER.load_authority()

    def test_authority_schema_tamper_is_rejected(self) -> None:
        with mock.patch.object(VERIFIER, "AUTHORITY_SCHEMA_SHA256", "0" * 64):
            with self.assertRaises(VERIFIER.VerificationInputError):
                VERIFIER.load_authority()

    def test_package_authority_tamper_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="evaluator-authority-test-") as temporary:
            tampered = Path(temporary) / "apt-packages.txt"
            tampered.write_bytes(VERIFIER.PACKAGE_AUTHORITY_PATH.read_bytes() + b"\n")
            with mock.patch.object(VERIFIER, "PACKAGE_AUTHORITY_PATH", tampered):
                with self.assertRaises(VERIFIER.VerificationInputError):
                    VERIFIER.load_authority()


if __name__ == "__main__":
    unittest.main()
