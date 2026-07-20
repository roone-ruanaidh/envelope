"""Verify the approved Q1/L1 candidate-transfer envelope without executing Q1/L1."""

from __future__ import annotations

import io
import json
import os
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path, PurePosixPath
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import candidate_transfer


class CandidateTransferEnvelopeTests(unittest.TestCase):
    @staticmethod
    def _write_archive(path: Path, members: list[tuple[str, bytes]]) -> None:
        with tarfile.open(path, mode="w", format=tarfile.PAX_FORMAT) as bundle:
            for name, content in members:
                info = tarfile.TarInfo(name)
                info.size = len(content)
                info.mode = 0o644
                info.mtime = 0
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                bundle.addfile(info, io.BytesIO(content))

    def test_approved_limits_are_exact(self) -> None:
        self.assertEqual(candidate_transfer.MAX_TRANSFER_ENTRIES, 10_000)
        self.assertEqual(candidate_transfer.MAX_REGULAR_FILE_BYTES, 16 * 1024 * 1024)
        self.assertEqual(candidate_transfer.MAX_REGULAR_FILE_TOTAL_BYTES, 128 * 1024 * 1024)
        self.assertEqual(candidate_transfer.MAX_PATH_DEPTH, 32)
        self.assertEqual(candidate_transfer.MAX_PATH_BYTES, 1_024)
        self.assertEqual(candidate_transfer.MAX_MANIFEST_BYTES, 8 * 1024 * 1024)

    def test_entry_limit_counts_empty_directories_and_is_inclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, patch.object(
            candidate_transfer, "MAX_TRANSFER_ENTRIES", 3
        ):
            root = Path(temporary)
            for name in ("a", "b", "c"):
                (root / name).mkdir()
            self.assertEqual(candidate_transfer.build_manifest(root)["files"], [])
            (root / "d").mkdir()
            with self.assertRaises(candidate_transfer.TransferError):
                candidate_transfer.build_manifest(root)

    def test_path_depth_limit_is_inclusive(self) -> None:
        candidate_transfer._validate_path_envelope(PurePosixPath(*(["d"] * 31), "file"))
        with self.assertRaises(candidate_transfer.TransferError):
            candidate_transfer._validate_path_envelope(
                PurePosixPath(*(["d"] * 32), "file")
            )

    def test_path_byte_limit_is_inclusive(self) -> None:
        exact = PurePosixPath("a" * 1_020, "bbb")
        over = PurePosixPath("a" * 1_020, "bbbb")
        self.assertEqual(len(os.fsencode(exact.as_posix())), 1_024)
        candidate_transfer._validate_path_envelope(exact)
        with self.assertRaises(candidate_transfer.TransferError):
            candidate_transfer._validate_path_envelope(over)

    def test_per_file_limit_is_inclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, patch.object(
            candidate_transfer, "MAX_REGULAR_FILE_BYTES", 4
        ):
            root = Path(temporary)
            candidate = root / "candidate"
            candidate.mkdir()
            (candidate / "file").write_bytes(b"1234")
            self.assertEqual(candidate_transfer.build_manifest(candidate)["files"][0]["size"], 4)
            (candidate / "file").write_bytes(b"12345")
            with self.assertRaises(candidate_transfer.TransferError):
                candidate_transfer.build_manifest(candidate)

    def test_total_file_limit_is_inclusive(self) -> None:
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.object(candidate_transfer, "MAX_REGULAR_FILE_BYTES", 8),
            patch.object(candidate_transfer, "MAX_REGULAR_FILE_TOTAL_BYTES", 8),
        ):
            root = Path(temporary)
            candidate = root / "candidate"
            candidate.mkdir()
            (candidate / "a").write_bytes(b"1234")
            (candidate / "b").write_bytes(b"5678")
            self.assertEqual(len(candidate_transfer.build_manifest(candidate)["files"]), 2)
            (candidate / "c").write_bytes(b"9")
            with self.assertRaises(candidate_transfer.TransferError):
                candidate_transfer.build_manifest(candidate)

    def test_manifest_limit_is_inclusive(self) -> None:
        value = {"files": [], "version": candidate_transfer.MANIFEST_VERSION}
        base = json.dumps(value).encode("utf-8")
        limit = len(base) + 4
        with tempfile.TemporaryDirectory() as temporary, patch.object(
            candidate_transfer, "MAX_MANIFEST_BYTES", limit
        ):
            manifest = Path(temporary) / "manifest.json"
            manifest.write_bytes(base + b" " * 4)
            self.assertEqual(candidate_transfer._load_manifest(manifest), value)
            manifest.write_bytes(base + b" " * 5)
            with self.assertRaises(candidate_transfer.TransferError):
                candidate_transfer._load_manifest(manifest)

    def test_manifest_entry_limit_counts_implied_directories(self) -> None:
        value = {
            "files": [
                {"mode": 0o644, "path": "a/file", "sha256": "a" * 64, "size": 0},
                {"mode": 0o644, "path": "b", "sha256": "b" * 64, "size": 0},
            ],
            "version": candidate_transfer.MANIFEST_VERSION,
        }
        with tempfile.TemporaryDirectory() as temporary, patch.object(
            candidate_transfer, "MAX_TRANSFER_ENTRIES", 2
        ):
            manifest = Path(temporary) / "manifest.json"
            manifest.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(candidate_transfer.TransferError):
                candidate_transfer._load_manifest(manifest)

    def test_manifest_file_and_total_limits_are_inclusive(self) -> None:
        def record(path: str, size: int) -> dict[str, object]:
            return {"mode": 0o644, "path": path, "sha256": "a" * 64, "size": size}

        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.object(candidate_transfer, "MAX_REGULAR_FILE_BYTES", 8),
            patch.object(candidate_transfer, "MAX_REGULAR_FILE_TOTAL_BYTES", 8),
        ):
            manifest = Path(temporary) / "manifest.json"
            value = {
                "files": [record("a", 4), record("b", 4)],
                "version": candidate_transfer.MANIFEST_VERSION,
            }
            manifest.write_text(json.dumps(value), encoding="utf-8")
            self.assertEqual(candidate_transfer._load_manifest(manifest), value)

            value["files"] = [record("a", 9)]
            manifest.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(candidate_transfer.TransferError):
                candidate_transfer._load_manifest(manifest)

            value["files"] = [record("a", 4), record("b", 5)]
            manifest.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(candidate_transfer.TransferError):
                candidate_transfer._load_manifest(manifest)

    def test_owner_mismatch_fails_transfer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(candidate_transfer.TransferError):
                candidate_transfer.build_manifest(root, owner_uid=os.getuid() + 1)

    def test_candidate_owned_exclusion_fails_authoritative_transfer(self) -> None:
        excluded_roots = (Path(".git"), Path(".venv"), Path("public") / "contract")
        for relative in excluded_roots:
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / relative).mkdir(parents=True)
                with self.assertRaises(candidate_transfer.TransferError):
                    candidate_transfer.build_manifest(root, owner_uid=os.getuid())

    def test_regular_bytes_modes_ignored_and_cache_files_are_included(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".gitignore").write_text("*.db\n__pycache__/\n", encoding="utf-8")
            (root / "__pycache__").mkdir()
            binary = root / "__pycache__" / "module.pyc"
            binary.write_bytes(b"\x00\xff\x80cache")
            binary.chmod(0o000)
            (root / "state.db").write_bytes(b"SQLite\x00\xff")
            for excluded in (root / ".git", root / ".venv", root / "public" / "contract"):
                excluded.mkdir(parents=True)
                (excluded / "excluded").write_bytes(b"excluded")

            records = {
                record["path"]: record
                for record in candidate_transfer.build_manifest(root)["files"]
            }
            self.assertEqual(set(records), {".gitignore", "__pycache__/module.pyc", "state.db"})
            self.assertEqual(records["__pycache__/module.pyc"]["mode"], 0o000)
            self.assertEqual(binary.stat().st_mode & 0o7777, 0o000)

    def test_mode_zero_file_round_trips_with_bytes_and_mode_intact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            source.mkdir()
            payload = source / "opaque"
            payload.write_bytes(b"\x00\xffarbitrary")
            payload.chmod(0o000)
            archive = base / "candidate.tar"
            manifest = base / "manifest.json"

            candidate_transfer.export_candidate(source, archive, manifest)
            extracted = base / "extracted"
            candidate_transfer.extract_candidate(archive, manifest, extracted)

            observed = extracted / "opaque"
            verified = candidate_transfer.verify_candidate(extracted, manifest)
            self.assertEqual(verified["files"][0]["mode"], 0)
            self.assertEqual(observed.stat().st_mode & 0o7777, 0)
            observed.chmod(0o400)
            self.assertEqual(observed.read_bytes(), b"\x00\xffarbitrary")

    def test_extraction_stops_at_archive_entry_cap_and_cleans_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, patch.object(
            candidate_transfer, "MAX_TRANSFER_ENTRIES", 3
        ):
            base = Path(temporary)
            source = base / "source"
            source.mkdir()
            for name in ("a", "b", "c"):
                path = source / name
                path.write_bytes(name.encode("ascii"))
                path.chmod(0o644)
            manifest = base / "manifest.json"
            candidate_transfer.export_candidate(source, base / "canonical.tar", manifest)
            archive = base / "over-cap.tar"
            self._write_archive(
                archive,
                [(name, name.encode("ascii")) for name in ("a", "b", "c", "d")],
            )
            extracted = base / "extracted"

            with self.assertRaisesRegex(
                candidate_transfer.TransferError, "archive exceeds maximum entry count"
            ):
                candidate_transfer.extract_candidate(archive, manifest, extracted)
            self.assertFalse(extracted.exists())

    def test_extraction_rejects_nonexact_members_and_cleans_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            source.mkdir()
            (source / "a").write_bytes(b"a")
            (source / "b").write_bytes(b"b")
            (source / "a").chmod(0o644)
            (source / "b").chmod(0o644)
            manifest = base / "manifest.json"
            candidate_transfer.export_candidate(source, base / "canonical.tar", manifest)
            variants = {
                "extra": [("a", b"a"), ("b", b"b"), ("c", b"c")],
                "missing": [("a", b"a")],
                "reordered": [("b", b"b"), ("a", b"a")],
            }

            for label, members in variants.items():
                with self.subTest(label=label):
                    archive = base / f"{label}.tar"
                    self._write_archive(archive, members)
                    extracted = base / f"extracted-{label}"
                    with self.assertRaisesRegex(
                        candidate_transfer.TransferError,
                        "archive members do not exactly match the transfer manifest",
                    ):
                        candidate_transfer.extract_candidate(archive, manifest, extracted)
                    self.assertFalse(extracted.exists())

    def test_extraction_rejects_member_mode_mismatch_and_cleans_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            source.mkdir()
            candidate = source / "candidate"
            candidate.write_bytes(b"content")
            candidate.chmod(0o600)
            manifest = base / "manifest.json"
            candidate_transfer.export_candidate(source, base / "canonical.tar", manifest)
            archive = base / "wrong-mode.tar"
            with tarfile.open(archive, mode="w", format=tarfile.PAX_FORMAT) as bundle:
                info = tarfile.TarInfo("candidate")
                info.size = len(b"content")
                info.mode = 0o644
                bundle.addfile(info, io.BytesIO(b"content"))
            extracted = base / "extracted"

            with self.assertRaisesRegex(
                candidate_transfer.TransferError, "invalid archive member: candidate"
            ):
                candidate_transfer.extract_candidate(archive, manifest, extracted)
            self.assertFalse(extracted.exists())


if __name__ == "__main__":
    unittest.main()
