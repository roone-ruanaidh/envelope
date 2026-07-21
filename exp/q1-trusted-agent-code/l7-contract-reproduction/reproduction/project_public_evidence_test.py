from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("project_public_evidence.py")
SPEC = importlib.util.spec_from_file_location("q1_l7_public_projection", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
projection = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = projection
SPEC.loader.exec_module(projection)


def _make_source(root: Path) -> tuple[Path, Path, bytes, list[dict[str, object]]]:
    source = root / "source"
    source.mkdir()
    masked = b"sk-proj-" + (b"*" * 24) + b"abcd"
    files = {
        "agent/attempt-1/events.jsonl": (
            b'{"error":"' + masked + b'"}\n'
        )
        * projection.EXPECTED_REDACTIONS,
        "pending-RESULT.md": b"# result\n",
        "run.json": json.dumps(
            {
                "contract_commit": projection.CONTRACT_COMMIT,
                "run_id": projection.RUN_ID,
                "status": "Inconclusive",
            }
        ).encode()
        + b"\n",
    }
    records: list[dict[str, object]] = []
    for name, data in files.items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        records.append(
            {
                "path": name,
                "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data),
            }
        )
    index_bytes = projection._json_bytes({"files": records, "version": 3})
    (source / projection.SOURCE_INDEX).write_bytes(index_bytes)
    (source / projection.SOURCE_COMPLETION).write_bytes(
        projection._json_bytes(
            {
                "contract_commit": projection.CONTRACT_COMMIT,
                "index_path": projection.SOURCE_INDEX,
                "index_sha256": hashlib.sha256(index_bytes).hexdigest(),
                "kind": "execution",
                "run_id": projection.RUN_ID,
                "version": 1,
            }
        )
    )
    result = root / "RESULT.md"
    result.write_bytes(files["pending-RESULT.md"])
    return source, result, masked, records


class PublicProjectionTests(unittest.TestCase):
    def test_projection_redacts_without_publishing_raw_commitments(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, result, masked, records = _make_source(root)
            destination = root / "public"

            projection.build_projection(source, result, destination)
            projection.verify_projection(destination)

            self.assertNotIn(
                masked,
                (destination / projection.EXPECTED_CHANGED_PATH).read_bytes(),
            )
            manifest = json.loads((destination / "projection.json").read_text())
            self.assertEqual(
                manifest["projection"]["redactions"],
                projection.EXPECTED_REDACTIONS,
            )
            self.assertEqual(
                manifest["projection"]["changed_files"],
                [
                    {
                        "occurrences": projection.EXPECTED_REDACTIONS,
                        "path": projection.EXPECTED_CHANGED_PATH,
                    }
                ],
            )
            self.assertEqual(
                set(manifest["source"]),
                {"contract_commit", "raw_retention", "run_id", "verification_boundary"},
            )
            self.assertNotIn(records[0]["sha256"], json.dumps(manifest))
            self.assertFalse((destination / "source-integrity").exists())

    def test_source_bound_verification_rejects_self_consistent_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, result, _, _ = _make_source(root)
            destination = root / "public"
            projection.build_projection(source, result, destination)

            changed = destination / projection.EXPECTED_CHANGED_PATH
            changed.write_bytes(changed.read_bytes() + b'{"invented":true}\n')
            index = projection._inventory(
                destination,
                excluded={
                    projection.PROJECTION_INDEX,
                    projection.PROJECTION_COMPLETION,
                },
            )
            (destination / projection.PROJECTION_INDEX).write_bytes(
                projection._json_bytes(index)
            )
            completion_path = destination / projection.PROJECTION_COMPLETION
            completion = json.loads(completion_path.read_text())
            completion["index_sha256"] = projection._sha256(
                destination / projection.PROJECTION_INDEX
            )
            completion_path.write_bytes(projection._json_bytes(completion))

            projection.verify_projection(destination)
            with self.assertRaisesRegex(ValueError, "exact source transform"):
                projection._verify_projection_against_source(
                    destination, source, result
                )

    def test_public_verification_rejects_private_source_commitments(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, result, _, _ = _make_source(root)
            destination = root / "public"
            projection.build_projection(source, result, destination)

            integrity = destination / "source-integrity"
            integrity.mkdir()
            (integrity / projection.SOURCE_INDEX).write_bytes(
                (source / projection.SOURCE_INDEX).read_bytes()
            )
            index = projection._inventory(
                destination,
                excluded={projection.PROJECTION_INDEX, projection.PROJECTION_COMPLETION},
            )
            (destination / projection.PROJECTION_INDEX).write_bytes(
                projection._json_bytes(index)
            )
            completion_path = destination / projection.PROJECTION_COMPLETION
            completion = json.loads(completion_path.read_text())
            completion["index_sha256"] = projection._sha256(
                destination / projection.PROJECTION_INDEX
            )
            completion_path.write_bytes(projection._json_bytes(completion))

            with self.assertRaisesRegex(ValueError, "private source commitment"):
                projection.verify_projection(destination)

    def test_masked_key_boundaries_cover_the_declared_alphabet(self) -> None:
        stars = b"*" * 20
        for suffix in (b"Ab1-", b"Ab1_", b"Ab12"):
            with self.subTest(suffix=suffix):
                self.assertIsNotNone(
                    projection.MASKED_KEY.search(b" " + b"sk-proj-" + stars + suffix + b".")
                )
        for value in (
            b"xsk-proj-" + stars + b"Ab12",
            b"sk-proj-" + stars + b"Ab12-",
            b"sk-proj-" + stars + b"Ab12_",
            b"sk-proj-" + stars + b"Ab12x",
        ):
            with self.subTest(value=value):
                self.assertIsNone(projection.MASKED_KEY.search(value))

    def test_project_is_idempotent_and_repairs_public_result(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, result, masked, _ = _make_source(root)
            loop = root / "loop"
            public_evidence = loop / "evidence" / projection.RUN_ID
            public_evidence.parent.mkdir(parents=True)
            source.rename(public_evidence)
            public_result = loop / "RESULT.md"
            result.rename(public_result)
            private_root = root / "private" / projection.RUN_ID
            staging = root / "staging"
            with patch.multiple(
                projection,
                PUBLIC_EVIDENCE=public_evidence,
                PUBLIC_RESULT=public_result,
                PRIVATE_ROOT=private_root,
                PRIVATE_EVIDENCE=private_root / "evidence",
                PRIVATE_RESULT=private_root / "RESULT.md",
                STAGING=staging,
            ):
                projection.project()
                public_result.write_text("truncated\n")
                public_result.with_name(".RESULT.md.projection-tmp").write_bytes(
                    (private_root / "RESULT.md").read_bytes()
                )
                projection.project()

                self.assertFalse(staging.exists())
                self.assertFalse(
                    public_result.with_name(".RESULT.md.projection-tmp").exists()
                )
                self.assertIn(
                    masked,
                    (private_root / "evidence" / projection.EXPECTED_CHANGED_PATH).read_bytes(),
                )
                self.assertNotIn(
                    masked,
                    (public_evidence / projection.EXPECTED_CHANGED_PATH).read_bytes(),
                )
                projection._verify_private_retention(public_evidence)
                projection._verify_public_result(public_evidence, public_result)

    def test_rebuild_quarantines_the_v1_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, result, _, _ = _make_source(root)
            public_evidence = root / "loop" / "evidence" / projection.RUN_ID
            public_evidence.mkdir(parents=True)
            (public_evidence / "projection.json").write_text('{"version":1}\n')
            public_result = root / "loop" / "RESULT.md"
            public_result.write_text("old\n")
            staging = root / "staging"
            superseded = root / "private" / "superseded"
            superseded.parent.mkdir()

            with patch.multiple(
                projection,
                PUBLIC_EVIDENCE=public_evidence,
                PUBLIC_RESULT=public_result,
                PRIVATE_EVIDENCE=source,
                PRIVATE_RESULT=result,
                SUPERSEDED_PUBLIC=superseded,
                STAGING=staging,
            ):
                projection.rebuild_projection()
                self.assertEqual(
                    json.loads((superseded / "projection.json").read_text()),
                    {"version": 1},
                )
                projection.verify_projection(public_evidence)
                projection._verify_private_retention(public_evidence)
                projection._verify_public_result(public_evidence, public_result)

    def test_projection_rejects_unindexed_source_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            (source / "pending-RESULT.md").write_text("# result\n")
            index = {
                "files": [
                    {
                        "path": "pending-RESULT.md",
                        "sha256": projection._sha256(source / "pending-RESULT.md"),
                        "size": (source / "pending-RESULT.md").stat().st_size,
                    }
                ],
                "version": 3,
            }
            (source / projection.SOURCE_INDEX).write_bytes(projection._json_bytes(index))
            (source / projection.SOURCE_COMPLETION).write_bytes(
                projection._json_bytes(
                    {
                        "contract_commit": projection.CONTRACT_COMMIT,
                        "index_path": projection.SOURCE_INDEX,
                        "index_sha256": projection._sha256(
                            source / projection.SOURCE_INDEX
                        ),
                        "kind": "execution",
                        "run_id": projection.RUN_ID,
                        "version": 1,
                    }
                )
            )
            (source / "extra.txt").write_text("extra\n")
            result = root / "RESULT.md"
            result.write_text("# result\n")
            with self.assertRaisesRegex(ValueError, "inventory is not exact"):
                projection.build_projection(source, result, root / "public")


if __name__ == "__main__":
    unittest.main(verbosity=2)
