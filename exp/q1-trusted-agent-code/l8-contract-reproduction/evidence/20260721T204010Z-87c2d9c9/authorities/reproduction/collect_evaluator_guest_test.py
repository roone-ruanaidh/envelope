"""Mechanical tests for the active evaluator-guest fingerprint collector."""

from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
import stat
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from types import ModuleType
from unittest import mock


ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "collect_evaluator_guest.py"
AUTHORITY = ROOT / "evaluator-authority.json"


def _load_collector() -> ModuleType:
    specification = importlib.util.spec_from_file_location("collect_evaluator_guest", SCRIPT)
    if specification is None or specification.loader is None:
        raise RuntimeError("could not load evaluator-guest collector")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


COLLECTOR = _load_collector()


def _expected() -> dict[str, object]:
    authority = json.loads(AUTHORITY.read_text(encoding="utf-8"))
    return authority["expected_observation"]


class EvaluatorGuestCollectorTests(unittest.TestCase):
    def test_tmpdir_must_be_a_real_run_envelope_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="q1-l1-run-test-", dir="/tmp") as temporary:
            tmpdir = Path(temporary) / "tmp"
            tmpdir.mkdir()
            with mock.patch.dict(os.environ, {"TMPDIR": str(tmpdir)}):
                self.assertEqual(COLLECTOR._validated_tmpdir(), tmpdir)
                self.assertEqual(COLLECTOR._command_environment()["TMPDIR"], str(tmpdir))
        with (
            mock.patch.dict(os.environ, {"TMPDIR": "/tmp"}),
            self.assertRaises(COLLECTOR.CollectionError),
        ):
            COLLECTOR._validated_tmpdir()

    def test_stdlib_tree_uses_the_declared_record_grammar(self) -> None:
        with tempfile.TemporaryDirectory(prefix="guest-collector-tree-") as temporary:
            root = Path(temporary)
            directory = root / "a"
            directory.mkdir()
            directory.chmod(0o750)
            binary = directory / "x.bin"
            binary.write_bytes(b"\x00\xff\n")
            binary.chmod(0o640)
            link = root / "link"
            link.symlink_to("a/x.bin")
            text = root / "z.txt"
            text.write_bytes(b"z")
            text.chmod(0o600)

            expected_records: list[bytes] = []
            for path in sorted(
                root.rglob("*"), key=lambda item: os.fsencode(item.relative_to(root))
            ):
                metadata = path.lstat()
                relative = os.fsencode(path.relative_to(root))
                if stat.S_ISDIR(metadata.st_mode):
                    kind, payload = b"d", b""
                elif stat.S_ISREG(metadata.st_mode):
                    kind = b"f"
                    payload = hashlib.sha256(path.read_bytes()).hexdigest().encode("ascii")
                else:
                    kind = b"l"
                    payload = os.fsencode(os.readlink(path))
                expected_records.append(
                    kind
                    + b"\0"
                    + oct(stat.S_IMODE(metadata.st_mode)).encode("ascii")
                    + b"\0"
                    + relative
                    + b"\0"
                    + payload
                    + b"\n"
                )

            observed = COLLECTOR._stdlib_tree(root)

            self.assertEqual(observed["count"], 4)
            self.assertEqual(
                observed["sha256"], hashlib.sha256(b"".join(expected_records)).hexdigest()
            )
            self.assertEqual(
                observed["mode_encoding"],
                "Python oct(stat.S_IMODE(mode)) as ASCII, including 0o prefix",
            )
            self.assertFalse(observed["root_record_included"])

    def test_package_names_are_derived_from_the_reviewed_package_file(self) -> None:
        self.assertEqual(
            COLLECTOR._package_names(),
            [
                "bubblewrap",
                "iproute2",
                "make",
                "python3",
                "python3.14",
                "python3.14-venv",
                "util-linux",
            ],
        )

    def test_tool_symlink_binds_target_and_resolved_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="guest-collector-tool-") as temporary:
            root = Path(temporary)
            resolved = root / "mke2fs"
            resolved.write_bytes(b"tool-bytes")
            link = root / "mkfs.ext4"
            link.symlink_to("mke2fs")

            observed = COLLECTOR._tool_identity(link, allow_symlink=True)

            self.assertEqual(
                observed,
                {
                    "path": str(link),
                    "path_kind": "symlink",
                    "resolved_path": str(resolved),
                    "sha256": hashlib.sha256(b"tool-bytes").hexdigest(),
                    "symlink_target": "mke2fs",
                },
            )

    def test_tool_symlink_cannot_resolve_through_another_symlink(self) -> None:
        with tempfile.TemporaryDirectory(prefix="guest-collector-tool-") as temporary:
            root = Path(temporary)
            (root / "binary").write_bytes(b"tool-bytes")
            (root / "mke2fs").symlink_to("binary")
            link = root / "mkfs.ext4"
            link.symlink_to("mke2fs")

            with self.assertRaises(COLLECTOR.CollectionError):
                COLLECTOR._tool_identity(link, allow_symlink=True)

    def test_collect_composes_exact_authority_guest_shape(self) -> None:
        expected = _expected()
        guest_keys = {
            "installed_package_inventory",
            "isolation",
            "packages",
            "runtime",
            "tools",
        }
        expected_guest = {key: copy.deepcopy(expected[key]) for key in guest_keys}
        python = copy.deepcopy(expected["runtime"]["python"])
        stdlib = python.pop("stdlib_tree")
        uname = types.SimpleNamespace(**expected["runtime"]["kernel"])

        with (
            mock.patch.object(COLLECTOR.os, "geteuid", return_value=0),
            mock.patch.object(COLLECTOR, "_safe_interpreter", return_value=True),
            mock.patch.object(
                COLLECTOR,
                "_validated_tmpdir",
                return_value=Path("/tmp/q1-l1-run-test/tmp"),
            ),
            mock.patch.object(
                COLLECTOR,
                "_installed_packages",
                side_effect=[
                    (
                        copy.deepcopy(expected["installed_package_inventory"]),
                        copy.deepcopy(expected["packages"]),
                    ),
                    (
                        copy.deepcopy(expected["installed_package_inventory"]),
                        copy.deepcopy(expected["packages"]),
                    ),
                ],
            ),
            mock.patch.object(
                COLLECTOR,
                "_automatic_package_updates",
                return_value=copy.deepcopy(
                    expected["runtime"]["automatic_package_updates"]
                ),
            ),
            mock.patch.object(
                COLLECTOR, "_python_runtime", return_value=(python, COLLECTOR.PYTHON_STDLIB)
            ),
            mock.patch.object(COLLECTOR, "_stdlib_tree", return_value=stdlib),
            mock.patch.object(
                COLLECTOR,
                "_tools",
                side_effect=[copy.deepcopy(expected["tools"]), copy.deepcopy(expected["tools"])],
            ),
            mock.patch.object(COLLECTOR.os, "uname", return_value=uname),
            mock.patch.object(
                COLLECTOR,
                "_cgroup_probe",
                return_value=(
                    copy.deepcopy(expected["isolation"]["cgroup_v2"]),
                    copy.deepcopy(expected["isolation"]["resource_envelope"]),
                ),
            ),
            mock.patch.object(
                COLLECTOR,
                "_user_namespace_probe",
                return_value=copy.deepcopy(expected["isolation"]["user_namespaces"]),
            ),
            mock.patch.object(
                COLLECTOR,
                "_filesystems",
                return_value=copy.deepcopy(expected["isolation"]["filesystems"]),
            ),
            mock.patch.object(
                COLLECTOR,
                "_writable_state_probe",
                return_value=copy.deepcopy(expected["isolation"]["writable_state"]),
            ),
        ):
            self.assertEqual(COLLECTOR.collect(), expected_guest)

    def test_automatic_package_updates_must_be_masked(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="q1-l1-systemd-config-"
        ) as temporary:
            root = Path(temporary)
            for unit in COLLECTOR.AUTOMATIC_PACKAGE_UPDATE_UNITS:
                (root / unit).symlink_to("/dev/null")
            with mock.patch.object(COLLECTOR, "SYSTEMD_CONFIG_ROOT", root):
                self.assertEqual(
                    COLLECTOR._automatic_package_updates(),
                    {"masked_units": list(COLLECTOR.AUTOMATIC_PACKAGE_UPDATE_UNITS)},
                )
                first = root / COLLECTOR.AUTOMATIC_PACKAGE_UPDATE_UNITS[0]
                first.unlink()
                first.symlink_to("/usr/lib/systemd/system/apt-daily.service")
                with self.assertRaises(COLLECTOR.CollectionError):
                    COLLECTOR._automatic_package_updates()

    def test_collector_has_no_evaluator_authority_input(self) -> None:
        self.assertFalse(hasattr(COLLECTOR, "AUTHORITY_PATH"))
        first_line = SCRIPT.read_text(encoding="utf-8").splitlines()[0]
        self.assertNotIn("evaluator-authority.json", first_line)

    def test_failure_emits_only_a_fixed_safe_error(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            mock.patch.object(
                COLLECTOR, "collect", side_effect=COLLECTOR.CollectionError("secret")
            ),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            self.assertEqual(COLLECTOR.main(), 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), '{"error":"evaluator_guest_collection_failed"}\n')
        self.assertNotIn("secret", stderr.getvalue())

    def test_unexpected_failure_emits_only_a_fixed_safe_error(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            mock.patch.object(COLLECTOR, "collect", side_effect=RuntimeError("secret")),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            self.assertEqual(COLLECTOR.main(), 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), '{"error":"evaluator_guest_collection_failed"}\n')

    def test_command_output_is_actively_capped(self) -> None:
        with (
            mock.patch.object(COLLECTOR, "MAX_COMMAND_OUTPUT_BYTES", 64),
            mock.patch.object(
                COLLECTOR,
                "_validated_tmpdir",
                return_value=Path("/tmp/q1-l1-run-test/tmp"),
            ),
            self.assertRaises(COLLECTOR.CollectionError),
        ):
            COLLECTOR._command(
                (sys.executable, "-c", "import os;os.write(1,b'x'*4096)")
            )

    def test_command_timeout_kills_its_process_group(self) -> None:
        started = time.monotonic()
        with (
            mock.patch.object(COLLECTOR, "COMMAND_TIMEOUT_SECONDS", 0.05),
            mock.patch.object(
                COLLECTOR,
                "_validated_tmpdir",
                return_value=Path("/tmp/q1-l1-run-test/tmp"),
            ),
            self.assertRaises(COLLECTOR.CollectionError),
        ):
            COLLECTOR._command((sys.executable, "-c", "import time;time.sleep(10)"))
        self.assertLess(time.monotonic() - started, 2.0)

    def test_mount_cleanup_detaches_only_owned_image_loops(self) -> None:
        root = Path(
            tempfile.mkdtemp(prefix="q1-l1-authority-", dir="/tmp")
        )
        image = root / "state.ext4"
        image.write_bytes(b"owned")
        tmpfs = root / "tmpfs"
        ext4 = root / "ext4"
        tmpfs.mkdir()
        ext4.mkdir()
        with (
            mock.patch.object(COLLECTOR, "_unmount") as unmount,
            mock.patch.object(
                COLLECTOR,
                "_wait_for_loop_absence",
                side_effect=[["/dev/loop7"], []],
            ),
            mock.patch.object(COLLECTOR, "_command") as command,
        ):
            COLLECTOR._cleanup_mount_probe(
                tmpfs, ext4, image, owned_parent=root.parent
            )
        self.assertEqual(
            unmount.call_args_list,
            [mock.call(ext4), mock.call(tmpfs)],
        )
        command.assert_called_once_with(
            ("/usr/sbin/losetup", "--detach", "/dev/loop7"),
            timeout_seconds=COLLECTOR.LOOP_DETACH_TIMEOUT_SECONDS,
        )
        self.assertFalse(root.exists())

    def test_mount_cleanup_accepts_the_owned_run_tmpdir(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="q1-l1-run-", dir="/tmp"
        ) as run_root:
            owned_parent = Path(run_root) / "tmp"
            owned_parent.mkdir()
            root = Path(
                tempfile.mkdtemp(
                    prefix="q1-l1-authority-", dir=owned_parent
                )
            )
            image = root / "state.ext4"
            image.write_bytes(b"owned")
            tmpfs = root / "tmpfs"
            ext4 = root / "ext4"
            tmpfs.mkdir()
            ext4.mkdir()
            with (
                mock.patch.object(COLLECTOR, "_unmount"),
                mock.patch.object(
                    COLLECTOR,
                    "_wait_for_loop_absence",
                    side_effect=[[], []],
                ),
            ):
                COLLECTOR._cleanup_mount_probe(
                    tmpfs,
                    ext4,
                    image,
                    owned_parent=owned_parent,
                )
            self.assertFalse(root.exists())

    def test_mount_cleanup_allows_bounded_kernel_autoclear(self) -> None:
        root = Path(
            tempfile.mkdtemp(prefix="q1-l1-authority-", dir="/tmp")
        )
        image = root / "state.ext4"
        image.write_bytes(b"owned")
        tmpfs = root / "tmpfs"
        ext4 = root / "ext4"
        tmpfs.mkdir()
        ext4.mkdir()
        with (
            mock.patch.object(COLLECTOR, "_unmount"),
            mock.patch.object(
                COLLECTOR,
                "_wait_for_loop_absence",
                side_effect=[[], []],
            ),
            mock.patch.object(COLLECTOR, "_command") as command,
        ):
            COLLECTOR._cleanup_mount_probe(
                tmpfs, ext4, image, owned_parent=root.parent
            )
        command.assert_not_called()
        self.assertFalse(root.exists())

    def test_loop_autoclear_wait_polls_until_absent(self) -> None:
        with (
            mock.patch.object(
                COLLECTOR,
                "_loop_devices",
                side_effect=[["/dev/loop7"], []],
            ),
            mock.patch.object(COLLECTOR.time, "sleep") as sleep,
        ):
            self.assertEqual(
                COLLECTOR._wait_for_loop_absence(
                    Path("/tmp/owned.ext4"),
                    deadline_seconds=COLLECTOR.LOOP_AUTOCLEAR_DEADLINE_SECONDS,
                ),
                [],
            )
        sleep.assert_called_once()

    def test_loop_settle_deadlines_are_fixed(self) -> None:
        self.assertEqual(COLLECTOR.LOOP_AUTOCLEAR_DEADLINE_SECONDS, 2.0)
        self.assertEqual(COLLECTOR.LOOP_ABSENCE_DEADLINE_SECONDS, 1.0)
        self.assertEqual(COLLECTOR.LOOP_POLL_SECONDS, 0.05)
        self.assertEqual(COLLECTOR.LOOP_QUERY_TIMEOUT_SECONDS, 0.5)
        self.assertEqual(COLLECTOR.LOOP_DETACH_TIMEOUT_SECONDS, 1.0)

    def test_mount_cleanup_fails_if_owned_loop_survives(self) -> None:
        root = Path(
            tempfile.mkdtemp(prefix="q1-l1-authority-", dir="/tmp")
        )
        image = root / "state.ext4"
        image.write_bytes(b"owned")
        tmpfs = root / "tmpfs"
        ext4 = root / "ext4"
        tmpfs.mkdir()
        ext4.mkdir()
        try:
            with (
                mock.patch.object(COLLECTOR, "_unmount"),
                mock.patch.object(
                    COLLECTOR,
                    "_wait_for_loop_absence",
                    side_effect=[["/dev/loop7"], ["/dev/loop7"]],
                ),
                mock.patch.object(COLLECTOR, "_command"),
                self.assertRaises(COLLECTOR.CollectionError),
            ):
                COLLECTOR._cleanup_mount_probe(
                    tmpfs, ext4, image, owned_parent=root.parent
                )
            self.assertTrue(image.exists())
            self.assertTrue(root.exists())
        finally:
            image.unlink(missing_ok=True)
            ext4.rmdir()
            tmpfs.rmdir()
            root.rmdir()

    def test_mount_cleanup_retains_orphan_when_unmount_fails(self) -> None:
        root = Path(
            tempfile.mkdtemp(prefix="q1-l1-authority-", dir="/tmp")
        )
        image = root / "state.ext4"
        image.write_bytes(b"owned")
        tmpfs = root / "tmpfs"
        ext4 = root / "ext4"
        tmpfs.mkdir()
        ext4.mkdir()
        try:
            with (
                mock.patch.object(
                    COLLECTOR,
                    "_unmount",
                    side_effect=[COLLECTOR.CollectionError("failed"), None],
                ),
                mock.patch.object(COLLECTOR, "_wait_for_loop_absence") as loops,
                mock.patch.object(COLLECTOR, "_command") as command,
                self.assertRaises(COLLECTOR.CollectionError),
            ):
                COLLECTOR._cleanup_mount_probe(
                    tmpfs, ext4, image, owned_parent=root.parent
                )
            loops.assert_not_called()
            command.assert_not_called()
            self.assertTrue(image.exists())
            self.assertTrue(root.exists())
        finally:
            image.unlink(missing_ok=True)
            ext4.rmdir()
            tmpfs.rmdir()
            root.rmdir()


if __name__ == "__main__":
    unittest.main()
