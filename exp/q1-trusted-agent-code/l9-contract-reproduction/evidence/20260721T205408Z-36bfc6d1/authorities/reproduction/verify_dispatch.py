"""Verify dispatchability mechanics without provisioning or invoking an agent."""

from __future__ import annotations

import argparse
import errno
import hashlib
import io
import json
import os
import re
import shlex
import signal
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import tomllib
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
L2_ROOT = ROOT.parent / "l2-contract-reproduction"
L2_RUNNER = L2_ROOT / "reproduction" / "run_l2.py"
L4_ROOT = ROOT.parent / "l4-contract-reproduction"
L4_RUNNER = L4_ROOT / "reproduction" / "run_l4.py"
L5_ROOT = ROOT.parent / "l5-contract-reproduction"
L5_RUNNER = L5_ROOT / "reproduction" / "run_l5.py"
L6_ROOT = ROOT.parent / "l6-contract-reproduction"
L6_RUNNER = L6_ROOT / "reproduction" / "run_l6.py"
L7_ROOT = ROOT.parent / "l7-contract-reproduction"
L7_RUNNER = L7_ROOT / "reproduction" / "run_l7.py"
L8_ROOT = ROOT.parent / "l8-contract-reproduction"
L8_RUNNER = L8_ROOT / "reproduction" / "run_l8.py"
L9_ROOT = ROOT.parent / "l9-contract-reproduction"
L9_RUNNER = L9_ROOT / "reproduction" / "run_l9.py"
DERIVED_LOOPS = (
    {
        "id": "Q1/L2",
        "intervention": "hermetic_dispatch_test_state",
        "prior": {
            "loop_id": "Q1/L1",
            "result_commit": "c069bc0a19b410562b30b78885efd3618fb41ec9",
            "run_id": "20260721T062629Z-b09fbc7b",
        },
        "root": L2_ROOT,
        "runner": L2_RUNNER,
        "qualification": None,
    },
    {
        "id": "Q1/L4",
        "intervention": "qualified_candidate_boundary",
        "prior": {
            "loop_id": "Q1/L3",
            "result_commit": "42b4c48880bc98358dbad84e3b71e7d06b416211",
            "run_id": "20260721T153644Z-b31c1649",
        },
        "root": L4_ROOT,
        "runner": L4_RUNNER,
        "qualification": L4_ROOT / "build" / "candidate-boundary-qualification",
    },
    {
        "id": "Q1/L5",
        "intervention": "single_codex_metadata_authority",
        "prior": {
            "loop_id": "Q1/L4",
            "result_commit": "4e83baae3884e23dd7c1b59293800218ab157006",
            "run_id": "20260721T170944Z-919d5660",
        },
        "root": L5_ROOT,
        "runner": L5_RUNNER,
        "qualification": L5_ROOT / "build" / "candidate-boundary-qualification",
    },
    {
        "id": "Q1/L6",
        "intervention": "hermetic_candidate_home_redaction",
        "prior": {
            "loop_id": "Q1/L5",
            "result_commit": "ae60848ae9465019a547d53bd95f62a1fa12144f",
            "run_id": "20260721T173838Z-aef45487",
        },
        "root": L6_ROOT,
        "runner": L6_RUNNER,
        "qualification": L6_ROOT / "build" / "candidate-boundary-qualification",
    },
    {
        "id": "Q1/L7",
        "intervention": "live_candidate_lima_shape",
        "prior": {
            "loop_id": "Q1/L6",
            "result_commit": "f00af3cab9c952bb42b8490973c4de697c0ccb4c",
            "run_id": "20260721T175525Z-f7c72be4",
        },
        "root": L7_ROOT,
        "runner": L7_RUNNER,
        "qualification": L7_ROOT / "build" / "candidate-boundary-qualification",
    },
    {
        "id": "Q1/L8",
        "intervention": "api_authentication_public_safety",
        "prior": {
            "loop_id": "Q1/L7",
            "result_commit": "9de1e949d7cdb4b00ca5c2451bb313af4b4b9ad5",
            "run_id": "20260721T181955Z-4de70100",
        },
        "root": L8_ROOT,
        "runner": L8_RUNNER,
        "qualification": None,
    },
    {
        "id": "Q1/L9",
        "intervention": "structured_output_root_object",
        "prior": {
            "loop_id": "Q1/L8",
            "result_commit": "744a13986555adcd93adf0f59102ffada9f871e5",
            "run_id": "20260721T204010Z-87c2d9c9",
        },
        "root": L9_ROOT,
        "runner": L9_RUNNER,
        "qualification": None,
    },
)
sys.path.insert(0, str(ROOT / "reproduction"))
sys.path.insert(0, str(ROOT))

import api_authentication_preflight
import run_l1
RUN_L1_IMPORTED_CANDIDATE_TRANSFER = "candidate_transfer" in sys.modules
import candidate_transfer
import candidate_snapshot
import evaluator_residue_probe
import verify_candidate_boundary
import verify_isolated_runtime
from evaluator import (
    acceptance,
    candidate_exec,
    controller,
    isolated_service,
    rerun,
    verify_evaluator,
)

run_l1._load_candidate_transfer()


class CandidateTransferTests(unittest.TestCase):
    def test_round_trip_preserves_candidate_files_and_excludes_provisioner_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            source.mkdir()
            (source / "service.py").write_text("print('ok')\n", encoding="utf-8")
            (source / "script").write_text("#!/bin/sh\n", encoding="utf-8")
            (source / "script").chmod(0o755)
            for excluded in (source / ".git", source / ".venv", source / "public" / "contract"):
                excluded.mkdir(parents=True)
                (excluded / "excluded").write_text("not transferred\n", encoding="utf-8")
            archive = base / "candidate.tar"
            manifest = base / "manifest.json"
            candidate_transfer.export_candidate(source, archive, manifest)
            extracted = base / "extracted"
            candidate_transfer.extract_candidate(archive, manifest, extracted)
            self.assertEqual(
                candidate_transfer.build_manifest(source),
                candidate_transfer.build_manifest(extracted),
            )
            self.assertEqual(stat.S_IMODE((extracted / "script").stat().st_mode), 0o755)
            self.assertFalse((extracted / ".git").exists())
            self.assertFalse((extracted / ".venv").exists())
            self.assertFalse((extracted / "public" / "contract").exists())

    def test_rejects_candidate_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            root.mkdir()
            (root / "target").write_text("target\n", encoding="utf-8")
            (root / "link").symlink_to("target")
            with self.assertRaises(candidate_transfer.TransferError):
                candidate_transfer.build_manifest(root)

    def test_rejects_multiply_linked_candidate_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            root.mkdir()
            (root / "first").write_text("same inode\n", encoding="utf-8")
            os.link(root / "first", root / "second")
            with self.assertRaises(candidate_transfer.TransferError):
                candidate_transfer.build_manifest(root)

    def test_rejects_credential_shaped_candidate_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ("sk-" + "a" * 24)).write_text("not a credential\n", encoding="utf-8")
            with self.assertRaises(candidate_transfer.TransferError):
                candidate_transfer.build_manifest(root)

    def test_credential_word_filename_without_a_secret_shape_is_admissible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            name = "authorization-bearer-handler.py"
            (root / name).write_text("pass\n", encoding="utf-8")
            manifest = candidate_transfer.build_manifest(root)
            self.assertEqual([record["path"] for record in manifest["files"]], [name])

    def test_rejects_candidate_control_paths(self) -> None:
        for relative in (
            Path("AGENTS.md"),
            Path("AGENTS.override.md"),
            Path("nested/AGENTS.md"),
            Path("nested/AGENTS.override.md"),
            Path(".agents/skills/example/SKILL.md"),
            Path("nested/.codex/config.toml"),
        ):
            with self.subTest(path=relative), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("control\n", encoding="utf-8")
                with self.assertRaisesRegex(
                    candidate_transfer.TransferError,
                    "control path",
                ):
                    candidate_transfer.build_manifest(root)

    def test_quiescence_accumulates_and_resignals_new_candidate_processes(self) -> None:
        signals: list[tuple[set[int], int]] = []
        with (
            patch.object(candidate_snapshot, "_ancestors", return_value={1, 2}),
            patch.object(
                candidate_snapshot,
                "_user_processes",
                side_effect=[{10}, {10, 11}, set()],
            ),
            patch.object(
                candidate_snapshot,
                "_signal_all",
                side_effect=lambda pids, signum: signals.append((set(pids), signum)),
            ),
            patch.object(
                candidate_snapshot.time,
                "monotonic",
                side_effect=[0.0, 0.0, 0.1],
            ),
            patch.object(candidate_snapshot.time, "sleep"),
        ):
            self.assertEqual(candidate_snapshot._quiesce(1000), [10, 11])
        self.assertEqual(
            signals,
            [
                ({10}, candidate_snapshot.signal.SIGTERM),
                ({10, 11}, candidate_snapshot.signal.SIGTERM),
            ],
        )

    def test_quiescence_escalates_to_sigkill(self) -> None:
        signals: list[tuple[set[int], int]] = []
        with (
            patch.object(candidate_snapshot, "_ancestors", return_value={1, 2}),
            patch.object(
                candidate_snapshot,
                "_user_processes",
                side_effect=[{10}, {10}, {10}, set()],
            ),
            patch.object(
                candidate_snapshot,
                "_signal_all",
                side_effect=lambda pids, signum: signals.append((set(pids), signum)),
            ),
            patch.object(
                candidate_snapshot.time,
                "monotonic",
                side_effect=[0.0, 0.0, 1.0, 1.0, 1.0, 1.1],
            ),
            patch.object(candidate_snapshot.time, "sleep"),
        ):
            self.assertEqual(candidate_snapshot._quiesce(1000), [10])
        self.assertEqual(
            signals,
            [
                ({10}, candidate_snapshot.signal.SIGTERM),
                ({10}, candidate_snapshot.signal.SIGTERM),
                ({10}, candidate_snapshot.signal.SIGKILL),
            ],
        )

    def test_quiescence_rejects_a_surviving_candidate_process(self) -> None:
        with (
            patch.object(candidate_snapshot, "_ancestors", return_value={1, 2}),
            patch.object(candidate_snapshot, "_user_processes", return_value={10}),
            patch.object(candidate_snapshot, "_signal_all"),
            patch.object(
                candidate_snapshot.time,
                "monotonic",
                side_effect=[0.0, 1.0, 1.0, 1.0, 2.0],
            ),
            patch.object(candidate_snapshot.time, "sleep"),
            self.assertRaisesRegex(candidate_snapshot.SnapshotError, "still owns live processes"),
        ):
            candidate_snapshot._quiesce(1000)

    def test_rejects_path_swap_before_descriptor_open(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            root.mkdir()
            source = root / "service.py"
            source.write_text("safe\n", encoding="utf-8")
            target = root / "target"
            target.write_text("secret\n", encoding="utf-8")
            original_open = os.open
            swapped = False

            def racing_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
                nonlocal swapped
                if path == "service.py" and kwargs.get("dir_fd") is not None and not swapped:
                    source.unlink()
                    source.symlink_to("target")
                    swapped = True
                return original_open(path, flags, *args, **kwargs)

            with patch.object(candidate_transfer.os, "open", side_effect=racing_open):
                with self.assertRaises(candidate_transfer.TransferError):
                    candidate_transfer.export_candidate(
                        root,
                        Path(temporary) / "candidate.tar",
                        Path(temporary) / "manifest.json",
                    )

    def test_rejects_archive_member_not_in_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            source.mkdir()
            (source / "service.py").write_text("pass\n", encoding="utf-8")
            archive = base / "candidate.tar"
            manifest = base / "manifest.json"
            candidate_transfer.export_candidate(source, archive, manifest)
            malicious = base / "malicious.tar"
            with tarfile.open(malicious, "w") as bundle:
                info = tarfile.TarInfo("../escape")
                info.size = 1
                bundle.addfile(info, io.BytesIO(b"x"))
            with self.assertRaises(candidate_transfer.TransferError):
                candidate_transfer.extract_candidate(malicious, manifest, base / "out")


class CandidateCommandTests(unittest.TestCase):
    def test_completion_accepts_argv_without_shell_parsing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            completion = Path(temporary) / "completion.json"
            command = ["python3", "-m", "service", "", "space value", "雪"]
            completion.write_text(
                json.dumps({"status": "declared_complete", "service_command": command}),
                encoding="utf-8",
            )
            self.assertEqual(rerun.load_completion(completion), command)

    def test_completion_rejects_empty_executable_and_nul(self) -> None:
        for command in ([""], ["python3", "bad\0value"]):
            with self.subTest(command=command), tempfile.TemporaryDirectory() as temporary:
                completion = Path(temporary) / "completion.json"
                completion.write_text(
                    json.dumps({"status": "declared_complete", "service_command": command}),
                    encoding="utf-8",
                )
                with self.assertRaises(ValueError):
                    rerun.load_completion(completion)

    def test_argv_envelope_uses_utf8_bytes_and_exact_boundaries(self) -> None:
        aggregate_limit = ["a" * (run_l1.ARGV_MAX_ENTRY_BYTES - 1)] * 8
        self.assertEqual(run_l1._validate_argv(aggregate_limit), aggregate_limit)
        self.assertEqual(
            sum(len(value.encode("utf-8")) + 1 for value in aggregate_limit),
            run_l1.ARGV_MAX_AGGREGATE_BYTES,
        )
        with self.assertRaises(ValueError):
            run_l1._validate_argv([*aggregate_limit[:-1], "a" * run_l1.ARGV_MAX_ENTRY_BYTES])
        utf8_limit = ["é" * (run_l1.ARGV_MAX_ENTRY_BYTES // 2)]
        self.assertEqual(run_l1._validate_argv(utf8_limit), utf8_limit)
        with self.assertRaises(ValueError):
            run_l1._validate_argv([utf8_limit[0] + "é"])
        with self.assertRaises(ValueError):
            run_l1._validate_argv(["x"] * (run_l1.ARGV_MAX_ENTRIES + 1))
        self.assertEqual(rerun._parse_service_command(aggregate_limit), aggregate_limit)

    def test_bubblewrap_end_of_options_precedes_candidate_argv(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = root / "candidate"
            candidate.mkdir()
            state = root / "state"
            state.mkdir()
            environment = {
                "Q1_L1_CLOCK_INITIAL_MS": "1",
                "Q1_L1_DATABASE_PATH": str(state / "service.sqlite3"),
                "Q1_L1_HOST": "127.0.0.1",
                "Q1_L1_PORT": "8765",
            }
            with patch.dict(os.environ, environment, clear=False):
                command = isolated_service._sandbox_command(candidate, ["--bind", "value"], 7)
            separator = command.index("--")
            self.assertEqual(
                command[separator : separator + 4],
                ["--", "/usr/bin/python3", "/q1-l1-candidate-exec.py", "--"],
            )
            self.assertEqual(command[-2:], ["--bind", "value"])

    def test_candidate_exit_125_is_remapped_inside_sandbox_launcher(self) -> None:
        socket_context = Mock()
        socket_context.__enter__ = Mock(return_value=socket_context)
        socket_context.__exit__ = Mock(return_value=False)
        with (
            patch.object(candidate_exec.socket, "socket", return_value=socket_context),
            patch.dict(
                os.environ,
                {candidate_exec.ENTRY_SOCKET_ENV: "/trusted/entry.sock"},
                clear=False,
            ),
        ):
            self.assertEqual(
                candidate_exec.run([sys.executable, "-c", "raise SystemExit(125)"]),
                1,
            )
        socket_context.sendto.assert_called_once_with(
            candidate_exec.ENTRY_TOKEN,
            "/trusted/entry.sock",
        )

    def test_declared_foreground_exit_rejects_a_surviving_process(self) -> None:
        socket_context = Mock()
        socket_context.__enter__ = Mock(return_value=socket_context)
        socket_context.__exit__ = Mock(return_value=False)
        process = Mock()
        process.wait.return_value = 0
        with (
            patch.object(candidate_exec.socket, "socket", return_value=socket_context),
            patch.object(candidate_exec.subprocess, "Popen", return_value=process),
            patch.object(
                candidate_exec,
                "_surviving_candidate_processes",
                return_value=True,
            ),
            patch.dict(
                os.environ,
                {candidate_exec.ENTRY_SOCKET_ENV: "/trusted/entry.sock"},
                clear=False,
            ),
        ):
            self.assertEqual(
                candidate_exec.run(["candidate-service"]),
                candidate_exec.FOREGROUND_VIOLATION_EXIT,
            )

    def test_candidate_launch_resource_failure_is_an_isolation_exit(self) -> None:
        socket_context = Mock()
        socket_context.__enter__ = Mock(return_value=socket_context)
        socket_context.__exit__ = Mock(return_value=False)
        with (
            patch.object(candidate_exec.socket, "socket", return_value=socket_context),
            patch.object(
                candidate_exec.subprocess,
                "Popen",
                side_effect=OSError(errno.ENOMEM, "out of memory"),
            ),
            patch.dict(
                os.environ,
                {candidate_exec.ENTRY_SOCKET_ENV: "/trusted/entry.sock"},
                clear=False,
            ),
        ):
            self.assertEqual(candidate_exec.run(["candidate-service"]), 125)

    def test_candidate_launch_missing_executable_is_a_candidate_exit(self) -> None:
        socket_context = Mock()
        socket_context.__enter__ = Mock(return_value=socket_context)
        socket_context.__exit__ = Mock(return_value=False)
        with (
            patch.object(candidate_exec.socket, "socket", return_value=socket_context),
            patch.object(
                candidate_exec.subprocess,
                "Popen",
                side_effect=OSError(errno.ENOENT, "not found"),
            ),
            patch.dict(
                os.environ,
                {candidate_exec.ENTRY_SOCKET_ENV: "/trusted/entry.sock"},
                clear=False,
            ),
        ):
            self.assertEqual(candidate_exec.run(["candidate-service"]), 127)

    def test_exit_125_origin_depends_on_the_declared_wrapper(self) -> None:
        direct = controller.ServiceController(
            base_url="http://127.0.0.1:1",
            command="candidate-service",
            clock_initial_ms=0,
        )
        isolated = controller.ServiceController(
            base_url="http://127.0.0.1:1",
            command="trusted-wrapper",
            clock_initial_ms=0,
            isolation_wrapper=True,
        )
        self.addCleanup(direct.close)
        self.addCleanup(isolated.close)
        self.assertEqual(direct._process_exit_origin(125), "candidate")
        self.assertEqual(isolated._process_exit_origin(125), "isolation")
        self.assertEqual(isolated._process_exit_origin(1), "candidate")

    def test_isolation_exit_during_teardown_is_not_a_candidate_failure(self) -> None:
        service = controller.ServiceController(
            base_url="http://127.0.0.1:1",
            command="trusted-wrapper",
            clock_initial_ms=0,
            isolation_wrapper=True,
        )
        process = Mock(returncode=125, stdout=None)
        process.poll.return_value = 125
        service._process = process
        with patch.object(service, "_wait_for_listener_close", return_value=True):
            with self.assertRaises(controller.ControllerFailure) as raised:
                service.stop(graceful=True)
            self.assertEqual(raised.exception.origin, "isolation")

    def test_isolated_graceful_timeout_asks_wrapper_to_unwind_before_sigkill(self) -> None:
        service = controller.ServiceController(
            base_url="http://127.0.0.1:1",
            command="trusted-wrapper",
            clock_initial_ms=0,
            force_stop_signal=signal.SIGUSR1,
            isolation_wrapper=True,
        )
        process = Mock(returncode=-signal.SIGKILL, stdout=None)
        process.poll.side_effect = [None, -signal.SIGKILL]
        process.wait.side_effect = [subprocess.TimeoutExpired("wrapper", 1.5), None]
        service._process = process
        with (
            patch.object(service, "_wait_for_listener_close", return_value=True),
            patch.object(controller.os, "kill") as kill,
            patch.object(controller.os, "killpg") as killpg,
        ):
            result = service.stop(graceful=True)
        kill.assert_called_once_with(process.pid, signal.SIGUSR1)
        killpg.assert_called_once_with(process.pid, signal.SIGTERM)
        self.assertTrue(result.forced_kill)
        service._temporary.cleanup()
        service._closed = True

    def test_isolated_unwind_wait_is_not_clipped_by_expired_suite_deadline(self) -> None:
        service = controller.ServiceController(
            base_url="http://127.0.0.1:1",
            command="trusted-wrapper",
            clock_initial_ms=0,
            suite_deadline=time.monotonic() - 1.0,
            force_stop_signal=signal.SIGUSR1,
            isolation_wrapper=True,
        )
        process = Mock(returncode=-signal.SIGKILL, stdout=None)
        process.poll.side_effect = [None, -signal.SIGKILL]
        process.wait.side_effect = [subprocess.TimeoutExpired("wrapper", 0.01), None]
        service._process = process
        with (
            patch.object(service, "_wait_for_listener_close", return_value=True),
            patch.object(controller.os, "kill"),
            patch.object(controller.os, "killpg"),
        ):
            service.stop(graceful=True)
        self.assertEqual(process.wait.call_args_list[1].kwargs["timeout"], 0.75)
        service._temporary.cleanup()
        service._closed = True

    def test_isolated_unwind_timeout_is_an_isolation_failure(self) -> None:
        service = controller.ServiceController(
            base_url="http://127.0.0.1:1",
            command="trusted-wrapper",
            clock_initial_ms=0,
            force_stop_signal=signal.SIGUSR1,
            isolation_wrapper=True,
        )
        process = Mock(returncode=-signal.SIGKILL, stdout=None)
        process.poll.side_effect = [None, -signal.SIGKILL]
        process.wait.side_effect = [
            subprocess.TimeoutExpired("wrapper", 1.5),
            subprocess.TimeoutExpired("wrapper", 0.75),
            None,
        ]
        service._process = process
        with (
            patch.object(service, "_wait_for_listener_close", return_value=True),
            patch.object(controller.os, "kill"),
            patch.object(controller.os, "killpg"),
        ):
            with self.assertRaises(controller.ControllerFailure) as raised:
                service.stop(graceful=True)
        self.assertEqual(raised.exception.origin, "isolation")
        service._temporary.cleanup()
        service._closed = True

    def test_candidate_and_evaluator_roots_must_be_disjoint(self) -> None:
        with self.assertRaises(ValueError):
            rerun._validate_candidate_root(ROOT)
        with self.assertRaises(ValueError):
            rerun._validate_candidate_root(ROOT.parent)

    def test_unexpected_evaluator_exception_is_not_a_candidate_failure(self) -> None:
        self.assertEqual(acceptance._failure_origin(acceptance.AcceptanceFailure("bad")), "candidate")
        self.assertEqual(acceptance._failure_origin(KeyError("evaluator bug")), "evaluator")
        self.assertEqual(
            acceptance._failure_origin(
                controller.ControllerFailure("teardown escaped", origin="isolation")
            ),
            "isolation",
        )


class CandidateBoundaryReportTests(unittest.TestCase):
    def test_exact_probe_and_installed_provenance_produce_safe_pass_report(self) -> None:
        authority = {
            name: "a" * 64 for name in verify_candidate_boundary.AUTHORITY_FILES
        }
        installed = "\n".join(
            f"{'a' * 64}  "
            + (
                "/home/lima/candidate/.boundary_probe.py"
                if path == "candidate_boundary_probe.py"
                else path
            )
            for path in verify_candidate_boundary.INSTALLED_AUTHORITIES
        )
        runtime = json.dumps(
            {
                "packages": [
                    *[list(item) for item in verify_candidate_boundary._required_packages().items()],
                    ["pip", "25.3"],
                ],
                "python_sha256": "b" * 64,
                "python_version": "3.14.4",
            }
        )
        probe = json.dumps(verify_candidate_boundary.EXPECTED_PROBE)
        results = (
            subprocess.CompletedProcess([], 0, installed + "\n", "not recorded"),
            subprocess.CompletedProcess([], 0, runtime + "\n", "not recorded"),
            subprocess.CompletedProcess([], 0, probe + "\n", "not recorded"),
        )
        with (
            patch.object(verify_candidate_boundary, "_authority_hashes", return_value=authority),
            patch.object(verify_candidate_boundary, "_run_lima", side_effect=results),
        ):
            report = verify_candidate_boundary.verify("q1-l1-test")
        self.assertTrue(report["passed"])
        self.assertEqual(report["probe"], verify_candidate_boundary.EXPECTED_PROBE)
        self.assertEqual(
            report["provenance"]["installed_sha256"],
            {
                authority: "a" * 64
                for authority in verify_candidate_boundary.INSTALLED_AUTHORITIES.values()
            },
        )
        self.assertEqual(report["provenance"]["lima"]["configured_mounts"], [])
        self.assertEqual(
            report["provenance"]["codex_cli_required"],
            "codex-cli 0.144.6",
        )
        self.assertEqual(report["provenance"]["candidate_runtime"]["python_version"], "3.14.4")
        self.assertEqual(report["schema_version"], 2)
        self.assertIsNone(report["failure_phase"])
        self.assertEqual(report["probe_process"]["return_code"], 0)
        self.assertEqual(report["probe_process"]["stderr"]["text"], "not recorded")
        self.assertFalse(report["probe_process"]["stderr"]["truncated"])
        encoded = json.dumps(report)
        self.assertIn("not recorded", encoded)
        self.assertNotIn(str(ROOT), encoded)

    def test_probe_schema_or_result_change_fails_closed(self) -> None:
        extra = {**verify_candidate_boundary.EXPECTED_PROBE, "extra": "value"}
        changed = {**verify_candidate_boundary.EXPECTED_PROBE, "workspace": "read_only"}
        self.assertEqual(
            verify_candidate_boundary._probe_result(json.dumps(extra)),
            (None, "probe_schema_invalid"),
        )
        self.assertEqual(
            verify_candidate_boundary._probe_result(json.dumps(changed)),
            (None, "probe_result_mismatch"),
        )

    def test_installed_authority_mismatch_stops_before_probe(self) -> None:
        authority = {
            name: "a" * 64 for name in verify_candidate_boundary.AUTHORITY_FILES
        }
        installed = "\n".join(
            f"{('b' if path == 'candidate_boundary_probe.py' else 'a') * 64}  "
            + (
                "/home/lima/candidate/.boundary_probe.py"
                if path == "candidate_boundary_probe.py"
                else path
            )
            for path in verify_candidate_boundary.INSTALLED_AUTHORITIES
        )
        with (
            patch.object(verify_candidate_boundary, "_authority_hashes", return_value=authority),
            patch.object(
                verify_candidate_boundary,
                "_run_lima",
                return_value=subprocess.CompletedProcess([], 0, installed + "\n", ""),
            ) as run_lima,
        ):
            report = verify_candidate_boundary.verify("q1-l1-test")
        self.assertFalse(report["passed"])
        self.assertEqual(report["failure"], "installed_authority_mismatch")
        self.assertEqual(report["failure_phase"], "installed_authority")
        self.assertIsNone(report["probe_process"])
        run_lima.assert_called_once()

    def test_failed_probe_retains_bounded_public_safe_process_evidence(self) -> None:
        authority = {
            name: "a" * 64 for name in verify_candidate_boundary.AUTHORITY_FILES
        }
        installed = "\n".join(
            f"{'a' * 64}  "
            + (
                "/home/lima/candidate/.boundary_probe.py"
                if path == "candidate_boundary_probe.py"
                else path
            )
            for path in verify_candidate_boundary.INSTALLED_AUTHORITIES
        )
        runtime = json.dumps(
            {
                "packages": [
                    *[list(item) for item in verify_candidate_boundary._required_packages().items()],
                    ["pip", "25.3"],
                ],
                "python_sha256": "b" * 64,
                "python_version": "3.14.4",
            }
        )
        secret = "sk-proj-" + "x" * 30
        host_home = Path("/home/test-host")
        host_repository = host_home / "workspace" / "ev"
        candidate_home = Path("/home/test-host.guest")
        diagnostic = (
            str(host_repository)
            + " "
            + str(host_home)
            + " "
            + str(candidate_home)
            + " "
            + secret
            + " "
            + "z" * (verify_candidate_boundary.PROBE_STREAM_RETENTION_BYTES + 100)
        )
        results = (
            subprocess.CompletedProcess([], 0, installed + "\n", ""),
            subprocess.CompletedProcess([], 0, runtime + "\n", ""),
            subprocess.CompletedProcess([], -9, "", diagnostic),
        )
        with (
            patch.object(verify_candidate_boundary, "_authority_hashes", return_value=authority),
            patch.object(verify_candidate_boundary, "_run_lima", side_effect=results),
            patch.object(verify_candidate_boundary, "HOST_HOME", host_home),
            patch.object(verify_candidate_boundary, "HOST_REPOSITORY", host_repository),
            patch.object(verify_candidate_boundary, "CANDIDATE_HOME", candidate_home),
            patch.dict(os.environ, {"OPENAI_API_KEY": secret}),
        ):
            report = verify_candidate_boundary.verify("q1-l1-test")
        self.assertFalse(report["passed"])
        self.assertEqual(report["failure"], "probe_command_failed")
        self.assertEqual(report["failure_phase"], "candidate_boundary_probe")
        process = report["probe_process"]
        self.assertEqual(process["return_code"], -9)
        self.assertTrue(process["stderr"]["truncated"])
        self.assertLessEqual(
            len(process["stderr"]["text"].encode("utf-8")),
            verify_candidate_boundary.PROBE_STREAM_RETENTION_BYTES,
        )
        encoded = json.dumps(process)
        self.assertNotIn(secret, encoded)
        self.assertNotIn(str(host_repository), encoded)
        self.assertNotIn(str(host_home), encoded)
        self.assertNotIn(str(candidate_home), encoded)
        self.assertEqual(
            {record["item"] for record in process["stderr"]["redactions"]},
            {"CANDIDATE_HOME", "HOST_HOME", "HOST_REPOSITORY", "OPENAI_API_KEY"},
        )

    def test_probe_redaction_deterministically_handles_identical_homes(self) -> None:
        shared_home = Path("/home/evaluator.guest")
        host_repository = shared_home / "workspace" / "ev"
        with (
            patch.object(verify_candidate_boundary, "HOST_HOME", shared_home),
            patch.object(verify_candidate_boundary, "HOST_REPOSITORY", host_repository),
            patch.object(verify_candidate_boundary, "CANDIDATE_HOME", shared_home),
            patch.dict(os.environ, {"OPENAI_API_KEY": ""}),
        ):
            public, records = verify_candidate_boundary._public_safe_probe_text(
                f"{host_repository} {shared_home} {shared_home}"
            )
        self.assertEqual(public, "[HOST_REPOSITORY] [HOST_HOME] [HOST_HOME]")
        self.assertEqual(
            records,
            [
                {"count": 1, "item": "HOST_REPOSITORY"},
                {"count": 2, "item": "HOST_HOME"},
            ],
        )

    def test_probe_diagnostics_do_not_change_acceptance(self) -> None:
        valid = json.dumps(verify_candidate_boundary.EXPECTED_PROBE)
        process = subprocess.CompletedProcess([], 1, valid, "diagnostic")
        self.assertEqual(
            verify_candidate_boundary._probe_process(process)["stderr"]["text"],
            "diagnostic",
        )
        self.assertEqual(
            verify_candidate_boundary._probe_result(valid),
            (verify_candidate_boundary.EXPECTED_PROBE, None),
        )


class ContractMechanicsTests(unittest.TestCase):
    def setUp(self) -> None:
        state = tempfile.TemporaryDirectory(prefix="q1-l1-dispatch-test-state-")
        self.addCleanup(state.cleanup)
        root = Path(state.name)
        self.enterContext(patch.object(run_l1, "EVIDENCE_ROOT", root / "evidence"))
        self.enterContext(patch.object(run_l1, "RESULT_PATH", root / "RESULT.md"))
        self.enterContext(
            patch.object(run_l1, "EXECUTION_LOCK_PATH", root / "execute.lock")
        )

    def _pending_generation(self, root: Path) -> tuple[Path, Path, dict[str, object]]:
        evidence = root / "evidence"
        evidence.mkdir()
        run_l1._write_json(
            evidence / "setup" / run_l1.API_AUTHENTICATION_REPORT,
            {
                "category": "api_authentication",
                "duration_seconds": 0.25,
                "status": 200,
            },
        )
        run_id = "20260101T000000Z-deadbeef"
        candidate = evidence / "candidate" / "attempt-1"
        source = candidate / "source"
        source.mkdir(parents=True)
        (source / "service.py").write_text("print('service')\n", encoding="utf-8")
        manifest_path = candidate / "manifest.json"
        run_l1._write_json(manifest_path, candidate_transfer.build_manifest(source))
        service_command = ["python3", "service.py"]
        identity_value = {
            "manifest_sha256": run_l1._sha256(manifest_path),
            "service_command": service_command,
        }
        identity_hash = hashlib.sha256(
            json.dumps(identity_value, separators=(",", ":"), sort_keys=True).encode()
        ).hexdigest()
        state: dict[str, object] = {
            "completed_attempts": 1,
            "contract_commit": "a" * 40,
            "final_candidate_identity_sha256": identity_hash,
            "final_gate_summary": {
                "attempt": 1,
                "candidate_identity_sha256": identity_hash,
                "manifest_path": "candidate/attempt-1/manifest.json",
                "service_command": service_command,
            },
            "final_manifest_sha256": identity_value["manifest_sha256"],
            "review_requested_at": "2026-01-01T00:01:00+00:00",
            "run_id": run_id,
            "run_started_at": "2026-01-01T00:00:00+00:00",
            "status": "PendingHumanReview",
        }
        run_l1._write_json(evidence / "run.json", state)
        (evidence / "commands.jsonl").write_text("", encoding="utf-8")
        pending_result = run_l1._render_result(state)
        (evidence / "pending-RESULT.md").write_text(pending_result, encoding="utf-8")
        result = root / "RESULT.md"
        result.write_text(pending_result, encoding="utf-8")
        run_l1._write_json(evidence / "evidence-index.json", run_l1._evidence_index(evidence))
        run_l1._write_completion_receipt(
            evidence,
            kind="execution",
            run_id=run_id,
            contract_commit="a" * 40,
        )
        return evidence, result, state

    def _write_finalization_marker(
        self,
        evidence: Path,
        state: dict[str, object],
    ) -> None:
        marker = {
            "contract_commit": state["contract_commit"],
            "run_id": state["run_id"],
            "started_at": "2026-01-01T00:02:00+00:00",
            "version": 1,
        }
        run_l1._atomic_write_new(
            evidence / run_l1.FINALIZATION_ATTEMPT_NAME,
            (json.dumps(marker, indent=2, sort_keys=True) + "\n").encode(),
        )

    def test_managed_requirements_enforce_q1_l1(self) -> None:
        requirements = tomllib.loads(
            (ROOT / "reproduction" / "candidate-codex-requirements.toml").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(requirements["allowed_approval_policies"], ["never"])
        self.assertEqual(requirements["allowed_web_search_modes"], [])
        self.assertEqual(requirements["default_permissions"], "q1_l1")
        self.assertEqual(requirements["allowed_permission_profiles"], {"q1_l1": True})
        self.assertFalse(requirements["permissions"]["q1_l1"]["network"]["enabled"])
        profile = requirements["permissions"]["q1_l1"]
        self.assertNotIn("extends", profile)
        workspace = profile["filesystem"][":workspace_roots"]
        self.assertNotIn(".agents", workspace)
        self.assertNotIn(".codex", workspace)
        self.assertNotIn("**/AGENTS.md", workspace)
        self.assertEqual(workspace["AGENTS.md"], "read")
        self.assertEqual(profile["filesystem"]["~/.codex"], "deny")
        for feature in ("apps", "multi_agent", "plugins", "remote_plugin"):
            with self.subTest(feature=feature):
                self.assertFalse(requirements["features"][feature])
        self.assertEqual(requirements["mcp_servers"], {})
        self.assertEqual(
            requirements["permissions"]["q1_l1"]["filesystem"][":workspace_roots"][
                "public/contract"
            ],
            "read",
        )
        config = tomllib.loads(
            (ROOT / "reproduction" / "candidate-codex-config.toml").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(config["model"], "gpt-5.6-luna")
        self.assertEqual(config["model"], run_l1.MODEL)
        self.assertEqual(config["model_reasoning_effort"], "max")
        self.assertEqual(config["model_reasoning_effort"], run_l1.REASONING_EFFORT)
        self.assertEqual(
            run_l1.EXPECTED_CANDIDATE_BOUNDARY,
            verify_candidate_boundary.EXPECTED_PROBE,
        )
        self.assertEqual(
            config["shell_environment_policy"]["set"]["PYTHONDONTWRITEBYTECODE"],
            "1",
        )
        bootstrap = (
            ROOT / "reproduction" / "bootstrap-candidate-lima.sh"
        ).read_text(encoding="utf-8")
        self.assertIn("@openai/codex@0.144.6", bootstrap)
        self.assertIn('codex-cli 0.144.6', bootstrap)
        self.assertNotIn("findmnt --json", bootstrap)
        self.assertEqual(run_l1.CODEX_VERSION, "codex-cli 0.144.6")
        self.assertEqual(
            str(verify_candidate_boundary.CANDIDATE_HOME),
            run_l1._expected_lima_user()["home"],
        )
        loop = (ROOT / "LOOP.md").read_text(encoding="utf-8")
        self.assertIn("`codex-cli 0.144.6`", loop)
        self.assertIn("`gpt-5.6-luna`", loop)
        self.assertIn("reasoning effort `max`", loop)
        prepare = (ROOT / "reproduction" / "prepare-candidate-lima.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn('sudo rmdir "$HOME/candidate/.codex"', prepare)
        self.assertLess(
            prepare.index('sudo rmdir "$HOME/candidate/.codex"'),
            prepare.index("verify_candidate_boundary.py"),
        )
        boundary_probe = (
            ROOT / "reproduction" / "candidate_boundary_probe.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"create Codex control directory"', boundary_probe)
        self.assertIn('(workspace / ".codex").mkdir()', boundary_probe)

    def test_runner_imports_no_repository_module_before_the_checkout_guard(self) -> None:
        self.assertFalse(RUN_L1_IMPORTED_CANDIDATE_TRANSFER)

    def test_prompts_and_completion_schema_are_fixed(self) -> None:
        schema = json.loads(
            (ROOT / "reproduction" / "agent-completion.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(schema["type"], "object")
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["required"], ["completion"])
        completion = schema["properties"]["completion"]
        statuses = {
            branch["properties"]["status"]["const"]
            for branch in completion["anyOf"]
        }
        self.assertEqual(statuses, {"blocked", "declared_complete"})
        remediation = (
            ROOT / "reproduction" / "agent-remediation-prompt.md"
        ).read_text(encoding="utf-8")
        self.assertEqual(remediation.count("{{FEEDBACK_JSON}}"), 1)

    def test_completion_predicate_and_attestation(self) -> None:
        complete = {"status": "declared_complete", "service_command": ["python3", "service.py"]}
        self.assertEqual(run_l1._validate_completion(complete), complete)
        self.assertEqual(run_l1._unwrap_completion({"completion": complete}), complete)
        with self.assertRaises(run_l1.Inconclusive):
            run_l1._unwrap_completion(complete)
        with self.assertRaises(run_l1.Inconclusive):
            run_l1._unwrap_completion({"completion": complete, "extra": None})
        with self.assertRaises(run_l1.Inconclusive):
            run_l1._unwrap_completion(
                {"completion": {"status": "blocked", "reason": "undefined boundary"}}
            )
        attestation = {
            "active_minutes": "unknown",
            "approved_boundary_exceptions": [],
            "decision": "Affirmative",
            "findings": [],
            "reviewed_candidate_identity_sha256": "b" * 64,
            "reviewed_manifest_sha256": "a" * 64,
        }
        self.assertEqual(
            run_l1._validate_attestation(
                attestation,
                "a" * 64,
                "b" * 64,
                {"service.py"},
                ["python3", "service.py"],
            ),
            attestation,
        )

    def test_affirmative_attestation_cannot_hide_findings_or_core_exceptions(self) -> None:
        base = {
            "active_minutes": 1,
            "approved_boundary_exceptions": [],
            "decision": "Affirmative",
            "findings": [],
            "reviewed_candidate_identity_sha256": "b" * 64,
            "reviewed_manifest_sha256": "a" * 64,
        }
        with self.assertRaises(ValueError):
            run_l1._validate_attestation(
                {
                    **base,
                    "findings": [
                        {
                            "clause": "1",
                            "detail": "violation",
                            "location": {
                                "file": "service.py",
                                "kind": "source_line",
                                "line": 1,
                            },
                        }
                    ],
                },
                "a" * 64,
                "b" * 64,
                {"service.py"},
                ["python3", "service.py"],
            )
        with self.assertRaisesRegex(ValueError, "declared checklist"):
            run_l1._validate_attestation(
                {
                    **base,
                    "decision": "Negative",
                    "findings": [
                        {
                            "clause": "style preference",
                            "detail": "not a declared violation",
                            "location": {
                                "file": "service.py",
                                "kind": "source_line",
                                "line": 1,
                            },
                        }
                    ],
                },
                "a" * 64,
                "b" * 64,
                {"service.py"},
                ["python3", "service.py"],
            )

    def test_negative_attestation_can_locate_source_argv_or_missing_path(self) -> None:
        base = {
            "active_minutes": 2,
            "approved_boundary_exceptions": [],
            "decision": "Negative",
            "reviewed_candidate_identity_sha256": "b" * 64,
            "reviewed_manifest_sha256": "a" * 64,
        }
        locations = (
            {"file": "service.py", "kind": "source_line", "line": 1},
            {"file": "service.py", "kind": "source_file"},
            {"argument_index": 1, "kind": "service_command_argument"},
            {"kind": "missing_workspace_path", "path": "Makefile"},
        )
        for location in locations:
            with self.subTest(location=location):
                value = {
                    **base,
                    "findings": [
                        {"clause": "1", "detail": "violation", "location": location}
                    ],
                }
                self.assertEqual(
                    run_l1._validate_attestation(
                        value,
                        "a" * 64,
                        "b" * 64,
                        {"service.py"},
                        ["python3", "-c", "code"],
                    ),
                    value,
                )
        with self.assertRaisesRegex(ValueError, "absent regular-file path"):
            run_l1._validate_attestation(
                {
                    **base,
                    "findings": [
                        {
                            "clause": "1",
                            "detail": "violation",
                            "location": {
                                "kind": "missing_workspace_path",
                                "path": "package",
                            },
                        }
                    ],
                },
                "a" * 64,
                "b" * 64,
                {"package/service.py"},
                ["python3", "package/service.py"],
            )
        with self.assertRaisesRegex(ValueError, "absent regular-file path"):
            run_l1._validate_attestation(
                {
                    **base,
                    "findings": [
                        {
                            "clause": "1",
                            "detail": "violation",
                            "location": {
                                "kind": "missing_workspace_path",
                                "path": "service.py/child",
                            },
                        }
                    ],
                },
                "a" * 64,
                "b" * 64,
                {"service.py"},
                ["python3", "service.py"],
            )
        with self.assertRaises(ValueError):
            run_l1._validate_attestation(
                {
                    **base,
                    "findings": [
                        {
                            "clause": "1",
                            "detail": "violation",
                            "location": {
                                "argument_index": 9,
                                "kind": "service_command_argument",
                            },
                        }
                    ],
                },
                "a" * 64,
                "b" * 64,
                {"service.py"},
                ["python3", "service.py"],
            )
        with self.assertRaises(ValueError):
            run_l1._validate_attestation(
                {
                    **base,
                    "approved_boundary_exceptions": [
                        {
                            "boundary": "domain",
                            "kind": "core_surface",
                            "location": {
                                "file": "service.py",
                                "kind": "source_line",
                                "line": 1,
                            },
                            "necessity": "none",
                        }
                    ],
                },
                "a" * 64,
                "b" * 64,
                {"service.py"},
                ["python3", "service.py"],
            )

    def test_remediation_resumes_from_candidate_workspace(self) -> None:
        command = run_l1._agent_shell_command(
            "$HOME/.codex/completion.json",
            "0199a213-81c0-7800-8aa1-bbab2a035a53",
        )
        self.assertTrue(command.startswith('cd "$HOME/candidate" && exec timeout'))
        self.assertIn("-m gpt-5.6-luna", command)
        self.assertIn('model_reasoning_effort="max"', command)

    def test_remediation_evidence_must_report_the_original_thread(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            events = Path(temporary) / "events.jsonl"
            events.write_text(
                json.dumps(
                    {
                        "thread_id": "0199a213-81c0-7800-8aa1-bbab2a035a53",
                        "type": "thread.started",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            self.assertEqual(
                run_l1._validated_thread_id(
                    events, "0199a213-81c0-7800-8aa1-bbab2a035a53"
                ),
                "0199a213-81c0-7800-8aa1-bbab2a035a53",
            )
            with self.assertRaises(run_l1.Inconclusive):
                run_l1._validated_thread_id(
                    events, "0199a213-81c0-7800-8aa1-bbab2a035a54"
                )

    def test_plan_is_read_only_and_complete(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(io.StringIO()):
            self.assertEqual(run_l1.plan(), 0)
        plan = json.loads(output.getvalue())
        self.assertEqual(
            plan["agent_stack"],
            {
                "codex_cli": "codex-cli 0.144.6",
                "model": "gpt-5.6-luna",
                "reasoning_effort": "max",
            },
        )
        self.assertEqual(
            plan["agent_budget"],
            {"initial": 1, "remediation": 1, "retries": 0, "same_thread": True},
        )
        self.assertEqual(
            plan["experiment"],
            {
                "loop": {"id": "Q1/L1", "intervention": "baseline"},
                "schema_version": 1,
                "workload": {
                    "id": "q1-lease-service-v1",
                    "resource_namespace": "q1-l1",
                    "source_loop": "Q1/L1",
                },
            },
        )
        self.assertEqual(plan["timeouts_seconds"]["agent_guest"], 1800)
        self.assertEqual(plan["timeouts_seconds"]["agent_outer"], 1860)
        self.assertEqual(plan["timeouts_seconds"]["api_authentication_total"], 30)
        self.assertEqual(plan["timeouts_seconds"]["automated_execute"], 10800)
        self.assertEqual(
            plan["timeouts_seconds"]["automated_work_before_cleanup_reserve"],
            10500,
        )
        self.assertTrue(plan["evaluator"]["preexisting_only"])
        self.assertEqual(
            plan["sequence"][:5],
            [
                "clean reviewed contract commit",
                "no prior result, key present, and zero scoped residue",
                "one read-only API authentication preflight before run state; "
                "a failure is a prerequisite refusal",
                "load the fixed candidate-transfer boundary",
                "start Q1/L1 run clocks and evidence, then recheck zero scoped residue",
            ],
        )
        self.assertTrue(
            any("human attestation" in step for step in plan["sequence"])
        )

    def test_derived_launchers_select_only_loop_owned_state(self) -> None:
        for case in DERIVED_LOOPS:
            with self.subTest(loop=case["id"]), tempfile.TemporaryDirectory() as temporary:
                completed = subprocess.run(
                    [sys.executable, "-B", "-I", str(case["runner"]), "plan"],
                    cwd=temporary,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                plan = json.loads(completed.stdout)
                self.assertEqual(
                    plan["experiment"]["loop"],
                    {"id": case["id"], "intervention": case["intervention"]},
                )
                self.assertEqual(plan["experiment"]["prior_loop"], case["prior"])
                self.assertEqual(
                    plan["experiment"]["workload"],
                    {
                        "id": "q1-lease-service-v1",
                        "resource_namespace": "q1-l1",
                        "source_loop": "Q1/L1",
                    },
                )
                self.assertEqual(plan["evaluator"]["instance"], "q1-l1-evaluator")
                self.assertTrue(any(case["id"] in step for step in plan["sequence"]))
                if case["qualification"] is not None:
                    self.assertIn("qualification", plan["sequence"][1])

    def test_derived_context_capture_and_result_are_loop_scoped(self) -> None:
        for case in DERIVED_LOOPS:
            with self.subTest(loop=case["id"]):
                context = run_l1.LoopContext(
                    loop_id=case["id"],
                    root=case["root"],
                    intervention=case["intervention"],
                    launcher=case["runner"],
                    prior_loop_id=case["prior"]["loop_id"],
                    prior_run_id=case["prior"]["run_id"],
                    prior_result_commit=case["prior"]["result_commit"],
                    candidate_qualification_root=case["qualification"],
                )
                run_l1.configure_loop(context)
                try:
                    self.assertEqual(run_l1.ROOT, ROOT)
                    self.assertEqual(run_l1.REPRODUCTION, ROOT / "reproduction")
                    self.assertEqual(run_l1.LOOP_PATH, case["root"] / "LOOP.md")
                    self.assertEqual(run_l1.EVIDENCE_ROOT, case["root"] / "evidence")
                    self.assertEqual(run_l1.RESULT_PATH, case["root"] / "RESULT.md")
                    self.assertEqual(run_l1.EVALUATOR_INSTANCE, "q1-l1-evaluator")
                    expected_context = {
                        "loop": {
                            "id": case["id"],
                            "intervention": case["intervention"],
                        },
                        "prior_loop": case["prior"],
                        "schema_version": 1,
                        "workload": {
                            "id": "q1-lease-service-v1",
                            "resource_namespace": "q1-l1",
                            "source_loop": "Q1/L1",
                        },
                    }
                    if case["qualification"] is not None:
                        expected_context["setup"] = {
                            "candidate_boundary_qualification": {
                                "included_in_evidence": True,
                                "measured_as_task_cost": False,
                            }
                        }
                    self.assertEqual(run_l1._run_context_record(), expected_context)
                    rendered = run_l1._render_result(
                        {
                            "completed_attempts": 0,
                            "contract_commit": "a" * 40,
                            "disposition_reason": "test",
                            "run_id": "20260101T000000Z-deadbeef",
                            "status": "Inconclusive",
                        }
                    )
                    self.assertTrue(rendered.startswith(f"# {case['id']} result"))
                    with tempfile.TemporaryDirectory() as temporary:
                        evidence_root = Path(temporary) / "evidence"
                        evidence = evidence_root / "20260101T000000Z-deadbeef"
                        evidence.mkdir(parents=True)
                        qualification = None
                        if case["qualification"] is not None:
                            qualification = Path(temporary) / "qualification"
                            (qualification / "logs").mkdir(parents=True)
                            (qualification / "commands.jsonl").write_text(
                                "{}\n", encoding="utf-8"
                            )
                            for name in (
                                "boundary-validation.json",
                                "redactions.json",
                                "setup-accounting.json",
                                run_l1.QUALIFICATION_REPORT_NAME,
                                run_l1.QUALIFICATION_INDEX_NAME,
                                run_l1.QUALIFICATION_COMPLETION_NAME,
                            ):
                                (qualification / name).write_text("{}\n", encoding="utf-8")
                            (qualification / "logs" / "probe.stdout").write_text(
                                "ok\n", encoding="utf-8"
                            )
                        with (
                            patch.object(run_l1, "EVIDENCE_ROOT", evidence_root),
                            patch.object(
                                run_l1,
                                "LOOP_CANDIDATE_QUALIFICATION_ROOT",
                                qualification,
                            ),
                        ):
                            run_l1._copy_run_authorities(evidence)
                            required = {
                                path.relative_to(evidence).as_posix()
                                for path in run_l1._required_evidence(
                                    evidence,
                                    {"agent_attempts_invoked": 0},
                                )
                            }
                        launcher_name = Path(case["runner"]).name
                        self.assertTrue(
                            {
                                "context.json",
                                f"authorities/loop/{launcher_name}",
                                "authorities/workload/LOOP.md",
                            }.issubset(required)
                        )
                        if qualification is not None:
                            self.assertTrue(
                                {
                                    "setup/candidate-boundary-qualification/commands.jsonl",
                                    "setup/candidate-boundary-qualification/qualification.json",
                                    "setup/candidate-boundary-qualification/boundary-validation.json",
                                    "setup/candidate-boundary-qualification/redactions.json",
                                    "setup/candidate-boundary-qualification/setup-accounting.json",
                                    "setup/candidate-boundary-qualification/logs/probe.stdout",
                                }.issubset(required)
                            )
                        self.assertEqual(
                            (evidence / "authorities" / "LOOP.md").read_bytes(),
                            (case["root"] / "LOOP.md").read_bytes(),
                        )
                        self.assertEqual(
                            (
                                evidence / "authorities" / "workload" / "LOOP.md"
                            ).read_bytes(),
                            (ROOT / "LOOP.md").read_bytes(),
                        )
                        self.assertEqual(
                            {
                                path.name
                                for path in (evidence / "authorities" / "loop").iterdir()
                            },
                            {launcher_name},
                        )
                        unsafe = {
                            path.relative_to(evidence).as_posix(): sorted(
                                run_l1._public_safety_labels(
                                    path.read_bytes(),
                                    check_host_paths=True,
                                )
                            )
                            for path in evidence.rglob("*")
                            if path.is_file()
                            and run_l1._public_safety_labels(
                                path.read_bytes(),
                                check_host_paths=True,
                            )
                        }
                        self.assertEqual(unsafe, {})
                    encoded = json.dumps(expected_context).encode()
                    self.assertEqual(
                        run_l1._public_safety_labels(encoded, check_host_paths=True),
                        set(),
                    )
                finally:
                    run_l1.configure_loop(run_l1.DEFAULT_LOOP)

    def test_candidate_boundary_qualification_reuses_measured_provisioner(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            loop_root = Path(temporary) / "l4-contract-reproduction"
            qualification_root = loop_root / "build" / "candidate-boundary-qualification"
            events: list[tuple[str, object]] = []

            def provision(
                _recorder: run_l1.Recorder,
                evidence: Path,
                instance: str,
            ) -> None:
                events.append(("provision", instance))
                authority = verify_candidate_boundary._authority_hashes()
                installed = {
                    name: authority[name]
                    for name in verify_candidate_boundary.INSTALLED_AUTHORITIES.values()
                }
                required = verify_candidate_boundary._required_packages()
                run_l1._write_json(
                    evidence / "boundary-validation.json",
                    verify_candidate_boundary._report(
                        authority,
                        lima_authority=verify_candidate_boundary._lima_authority(),
                        failure=None,
                        failure_phase=None,
                        installed_hashes=installed,
                        candidate_runtime={
                            "packages": {**required, "pip": "25.3"},
                            "python_sha256": "b" * 64,
                            "python_version": "3.14.4",
                        },
                        probe=verify_candidate_boundary.EXPECTED_PROBE.copy(),
                        probe_process={
                            "encoding": "utf-8-backslashreplace",
                            "retention_limit_bytes": 4096,
                            "return_code": 0,
                            "stderr": {
                                "redactions": [],
                                "text": "",
                                "truncated": False,
                            },
                            "stdout": {
                                "redactions": [],
                                "text": json.dumps(
                                    verify_candidate_boundary.EXPECTED_PROBE
                                ),
                                "truncated": False,
                            },
                        },
                    ),
                )

            def cleanup(
                recorder: run_l1.Recorder,
                instance: str,
                login_attempted: bool,
            ) -> list[str]:
                events.append(("cleanup", (instance, login_attempted)))
                prepare = (
                    f"{run_l1.REDACTED_HOST_REPOSITORY}/"
                    + (run_l1.REPRODUCTION / "prepare-candidate-lima.sh")
                    .relative_to(run_l1.REPOSITORY_ROOT)
                    .as_posix()
                )
                specifications = (
                    (
                        "provision and probe candidate VM",
                        [prepare, instance],
                        "",
                    ),
                    (
                        "inspect candidate VM before teardown",
                        ["limactl", "list", "--json"],
                        json.dumps({"name": run_l1.EVALUATOR_INSTANCE})
                        + "\n"
                        + json.dumps({"name": instance})
                        + "\n",
                    ),
                    (
                        "delete candidate VM",
                        ["limactl", "delete", "--force", instance],
                        "",
                    ),
                    (
                        "verify candidate VM teardown",
                        ["limactl", "list", "--json"],
                        json.dumps({"name": run_l1.EVALUATOR_INSTANCE}) + "\n",
                    ),
                )
                records = []
                for sequence, (label, argv, stdout) in enumerate(specifications, start=1):
                    stdout_path = f"logs/{sequence:03d}.stdout"
                    stderr_path = f"logs/{sequence:03d}.stderr"
                    (recorder.evidence / stdout_path).write_text(stdout, encoding="utf-8")
                    (recorder.evidence / stderr_path).write_text("", encoding="utf-8")
                    records.append(
                        {
                            "argv": argv,
                            "category": "machine",
                            "duration_seconds": 1.0,
                            "finished_at": "2026-01-01T00:00:01+00:00",
                            "kind": "command",
                            "label": label,
                            "limit_breach": None,
                            "resources": ["trusted_machine"],
                            "return_code": 0,
                            "sequence": sequence,
                            "started_at": "2026-01-01T00:00:00+00:00",
                            "stderr_path": stderr_path,
                            "stdout_path": stdout_path,
                            "timed_out": False,
                        }
                    )
                (recorder.evidence / "commands.jsonl").write_text(
                    "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
                    encoding="utf-8",
                )
                return []

            active = run_l1.LoopContext(
                loop_id="Q1/L4",
                root=loop_root,
                intervention="qualified_candidate_boundary",
            )
            with (
                patch.object(run_l1, "LOOP_ROOT", loop_root),
                patch.object(run_l1, "ACTIVE_LOOP", active),
                patch.object(run_l1, "RESULT_PATH", loop_root / "RESULT.md"),
                patch.object(run_l1, "_checkout_guard"),
                patch.object(run_l1, "_assert_no_orphaned_run"),
                patch.object(
                    run_l1,
                    "_acquire_execution_lock",
                    side_effect=lambda: os.open(os.devnull, os.O_RDONLY),
                ),
                patch.object(
                    run_l1,
                    "_run_id",
                    return_value="20260101T000000Z-deadbeef",
                ),
                patch.object(run_l1, "_provision_candidate", side_effect=provision),
                patch.object(run_l1, "_cleanup_candidate", side_effect=cleanup),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(
                    run_l1.qualify_candidate_boundary("a" * 40, qualification_root),
                    0,
                )
                run_l1.require_candidate_boundary_qualification(
                    qualification_root,
                    "a" * 40,
                )
                invalid_boundary = json.loads(
                    (qualification_root / "boundary-validation.json").read_text()
                )
                invalid_boundary["probe"] = {}
                with self.assertRaisesRegex(ValueError, "did not pass"):
                    run_l1._validate_candidate_boundary_report(invalid_boundary)
                original_commands = (qualification_root / "commands.jsonl").read_text()
                (qualification_root / "commands.jsonl").write_text("{}\n")
                with self.assertRaisesRegex(ValueError, "command sequence"):
                    run_l1._validate_candidate_boundary_commands(
                        qualification_root,
                        "q1-l1-candidate-20260101t000000z-deadbeef",
                    )
                (qualification_root / "commands.jsonl").write_text(original_commands)
                command_records = [
                    json.loads(line) for line in original_commands.splitlines()
                ]
                command_records[0]["stdout_path"] = "logs/../outside.stdout"
                (qualification_root / "commands.jsonl").write_text(
                    "".join(
                        json.dumps(record, sort_keys=True) + "\n"
                        for record in command_records
                    )
                )
                with self.assertRaisesRegex(ValueError, "command stream"):
                    run_l1._validate_candidate_boundary_commands(
                        qualification_root,
                        "q1-l1-candidate-20260101t000000z-deadbeef",
                    )
                (qualification_root / "commands.jsonl").write_text(original_commands)
                with self.assertRaisesRegex(RuntimeError, "did not pass this contract"):
                    run_l1.require_candidate_boundary_qualification(
                        qualification_root,
                        "b" * 40,
                    )
                (qualification_root / "boundary-validation.json").write_text(
                    "{}\n", encoding="utf-8"
                )
                with self.assertRaisesRegex(ValueError, "indexed evidence changed"):
                    run_l1.require_candidate_boundary_qualification(
                        qualification_root,
                        "a" * 40,
                    )
            self.assertEqual(events[0][0], "provision")
            self.assertEqual(events[1][0], "cleanup")
            self.assertFalse(events[1][1][1])

    def test_measured_provisioner_copies_into_qualification_owner(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "workload"
            source = root / "build" / "candidate-boundary-validation.json"
            run_l1._write_json(source, {"passed": True})
            qualification = Path(temporary) / "candidate-boundary-qualification"
            qualification.mkdir()
            recorder = Mock()
            recorder.run.return_value = run_l1.CommandResult(
                sequence=1,
                label="provision and probe candidate VM",
                category="machine",
                argv=["prepare"],
                started_at="2026-01-01T00:00:00+00:00",
                finished_at="2026-01-01T00:00:01+00:00",
                duration_seconds=1.0,
                return_code=0,
                timed_out=False,
                limit_breach=None,
                resources=["trusted_machine"],
                stdout_path="logs/001.stdout",
                stderr_path="logs/001.stderr",
            )
            with (
                patch.object(run_l1, "ROOT", root),
                patch.object(run_l1, "REPRODUCTION", root / "reproduction"),
                patch.object(
                    run_l1,
                    "LOOP_CANDIDATE_QUALIFICATION_ROOT",
                    qualification,
                ),
            ):
                run_l1._provision_candidate(
                    recorder,
                    qualification,
                    "q1-l1-candidate-20260101t000000z-deadbeef",
                )
            self.assertEqual(
                (qualification / "boundary-validation.json").read_bytes(),
                source.read_bytes(),
            )

    def test_failed_candidate_boundary_qualification_closes_inconclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            loop_root = Path(temporary) / "l5-contract-reproduction"
            qualification_root = loop_root / "build" / "candidate-boundary-qualification"
            cleanup = Mock(return_value=[])

            def fail_provision(
                _recorder: run_l1.Recorder,
                evidence: Path,
                _instance: str,
            ) -> None:
                (evidence / "commands.jsonl").write_text("{}\n", encoding="utf-8")
                raise run_l1.Inconclusive("candidate_provisioning", "failed")

            with (
                patch.object(run_l1, "LOOP_ROOT", loop_root),
                patch.object(
                    run_l1,
                    "ACTIVE_LOOP",
                    run_l1.LoopContext(
                        loop_id="Q1/L5",
                        root=loop_root,
                        intervention="single_codex_metadata_authority",
                    ),
                ),
                patch.object(run_l1, "EVIDENCE_ROOT", loop_root / "evidence"),
                patch.object(run_l1, "RESULT_PATH", loop_root / "RESULT.md"),
                patch.object(run_l1, "_checkout_guard"),
                patch.object(run_l1, "_assert_no_orphaned_run"),
                patch.object(
                    run_l1,
                    "_acquire_execution_lock",
                    side_effect=lambda: os.open(os.devnull, os.O_RDONLY),
                ),
                patch.object(run_l1, "_provision_candidate", side_effect=fail_provision),
                patch.object(run_l1, "_cleanup_candidate", cleanup),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(
                    run_l1.qualify_candidate_boundary("a" * 40, qualification_root),
                    2,
                )
            cleanup.assert_called_once()
            self.assertFalse(qualification_root.exists())
            terminal = next((loop_root / "evidence").iterdir())
            self.assertTrue((terminal / run_l1.QUALIFICATION_INDEX_NAME).is_file())
            self.assertTrue((terminal / run_l1.QUALIFICATION_COMPLETION_NAME).is_file())
            self.assertTrue((terminal / "terminal-RESULT.md").is_file())
            result_text = (loop_root / "RESULT.md").read_text()
            self.assertIn("**Inconclusive.**", result_text)
            self.assertIn("Q1/L5 cannot execute or retry", result_text)
            self.assertNotIn("Q1/L4", result_text)
            self.assertIn("existing human-approved troubleshooting sequence", result_text)
            self.assertEqual(
                (loop_root / "RESULT.md").read_bytes(),
                (terminal / "terminal-RESULT.md").read_bytes(),
            )

    def test_measured_preflight_revalidates_candidate_qualification(self) -> None:
        events: list[str] = []

        def require(_root: Path, _commit: str) -> None:
            events.append("qualification")
            raise RuntimeError("qualification rejected")

        with (
            patch.object(
                run_l1,
                "LOOP_CANDIDATE_QUALIFICATION_ROOT",
                L4_ROOT / "build" / "candidate-boundary-qualification",
            ),
            patch.object(
                run_l1,
                "_checkout_guard",
                side_effect=lambda _commit: events.append("checkout"),
            ),
            patch.object(
                run_l1,
                "require_candidate_boundary_qualification",
                side_effect=require,
            ),
            self.assertRaisesRegex(RuntimeError, "qualification rejected"),
        ):
            run_l1._preflight("a" * 40)
        self.assertEqual(events, ["checkout", "qualification"])

    def test_api_authentication_helper_is_one_bodyless_request(self) -> None:
        secret = "sk-" + "proj-" + "secret-" + "control-" + "value"
        for status in (200, 401, 429):
            with self.subTest(status=status):
                response = Mock(status=status)
                connection = Mock()
                connection.getresponse.return_value = response
                with (
                    patch.object(
                        api_authentication_preflight.http.client,
                        "HTTPSConnection",
                        return_value=connection,
                    ) as constructor,
                ):
                    observed = api_authentication_preflight.probe(secret)
                self.assertEqual(observed, status)
                constructor.assert_called_once_with(
                    api_authentication_preflight.HOST,
                    timeout=api_authentication_preflight.SOCKET_TIMEOUT_SECONDS,
                )
                connection.request.assert_called_once_with(
                    "GET",
                    api_authentication_preflight.PATH,
                    headers={"Authorization": f"Bearer {secret}"},
                )
                connection.getresponse.assert_called_once_with()
                response.read.assert_not_called()
                response.peek.assert_not_called()
                response.getheaders.assert_not_called()
                response.close.assert_called_once_with()
                connection.close.assert_called_once_with()

    def test_api_authentication_preflight_is_hard_bounded_and_secret_stdin_only(
        self,
    ) -> None:
        secret = "sk-" + "proj-" + "secret-" + "control-" + "value"
        captured = run_l1.CapturedProcess(
            return_code=0,
            stdout=b'{"status": 200}',
            stderr=b"",
            timed_out=False,
            breaches=(),
        )
        with (
            patch.object(run_l1, "_run_bounded_process", return_value=captured) as run,
            patch.object(
                run_l1.time,
                "monotonic",
                side_effect=[10.0, 10.25],
            ),
        ):
            report = run_l1._api_authentication_preflight(secret)
        self.assertEqual(
            report,
            {
                "category": "api_authentication",
                "duration_seconds": 0.25,
                "status": 200,
            },
        )
        run.assert_called_once()
        command = run.call_args.args[0]
        options = run.call_args.kwargs
        self.assertEqual(
            command,
            [
                sys.executable,
                "-B",
                "-I",
                str(run_l1.API_AUTHENTICATION_HELPER),
            ],
        )
        self.assertEqual(options["input_bytes"], secret.encode("utf-8"))
        self.assertEqual(
            options["timeout_seconds"],
            run_l1.API_AUTHENTICATION_TIMEOUT_SECONDS,
        )
        self.assertNotIn(secret, json.dumps(command))
        self.assertNotIn(secret, json.dumps(options["environment"], sort_keys=True))
        self.assertNotIn("OPENAI_API_KEY", options["environment"])

    def test_api_authentication_preflight_fails_safely_without_retry(self) -> None:
        secret = "sk-" + "proj-" + "secret-" + "control-" + "value"
        failures = (
            OSError(secret),
            run_l1.CapturedProcess(1, b"", secret.encode(), False, ()),
            run_l1.CapturedProcess(0, b'{"status":null}', b"", False, ()),
            run_l1.CapturedProcess(0, b'{"status":200.0}', b"", False, ()),
            run_l1.CapturedProcess(0, b'{"status":200}', b"", True, ()),
        )
        for failure in failures:
            with self.subTest(failure=repr(failure)):
                outcome = (
                    {"side_effect": failure}
                    if isinstance(failure, Exception)
                    else {"return_value": failure}
                )
                with (
                    patch.object(
                        run_l1,
                        "_run_bounded_process",
                        **outcome,
                    ),
                    patch.object(
                        run_l1.time,
                        "monotonic",
                        side_effect=[10.0, 10.25],
                    ),
                ):
                    report = run_l1._api_authentication_preflight(secret)
                self.assertEqual(
                    report,
                    {
                        "category": "api_authentication",
                        "duration_seconds": 0.25,
                        "status": None,
                    },
                )
                with (
                    patch.object(
                        run_l1,
                        "_api_authentication_preflight",
                        return_value=report,
                    ),
                    self.assertRaisesRegex(RuntimeError, "authentication preflight failed")
                    as raised,
                ):
                    run_l1._require_api_authentication(secret)
                rendered = str(raised.exception)
                self.assertNotIn(secret, rendered)

    def test_api_authentication_report_schema_is_exact(self) -> None:
        valid = {
            "category": "api_authentication",
            "duration_seconds": 0.25,
            "status": 200,
        }
        self.assertEqual(run_l1._validated_api_authentication_report(valid), valid)
        for invalid in (
            {**valid, "extra": True},
            {**valid, "status": 401},
            {**valid, "status": 200.0},
            {**valid, "status": True},
            {**valid, "duration_seconds": float("nan")},
            {**valid, "duration_seconds": -1},
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                run_l1._validated_api_authentication_report(invalid)

    def test_api_authentication_refusal_precedes_all_run_state(self) -> None:
        load = Mock()
        run_id = Mock()
        deadline = Mock()
        with (
            patch.object(run_l1, "_preflight", return_value="secret"),
            patch.object(
                run_l1,
                "_require_api_authentication",
                side_effect=RuntimeError("safe refusal"),
            ),
            patch.object(run_l1, "_load_candidate_transfer", load),
            patch.object(run_l1, "_run_id", run_id),
            self.assertRaisesRegex(RuntimeError, "safe refusal"),
        ):
            run_l1._execute_locked("a" * 40, deadline)
        load.assert_not_called()
        run_id.assert_not_called()
        self.assertFalse(run_l1.EVIDENCE_ROOT.exists())

    def test_missing_candidate_boundary_qualification_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            loop_root = Path(temporary) / "l4-contract-reproduction"
            with (
                patch.object(run_l1, "LOOP_ROOT", loop_root),
                self.assertRaisesRegex(RuntimeError, "qualification is missing"),
            ):
                run_l1.require_candidate_boundary_qualification(
                    loop_root / "build" / "candidate-boundary-qualification",
                    "a" * 40,
                )

    def test_loop_context_rejects_an_external_root_without_mutation(self) -> None:
        before = run_l1.ACTIVE_LOOP
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "direct Q1 loop directory"):
                run_l1.configure_loop(
                    run_l1.LoopContext(
                        loop_id="Q1/L2",
                        root=Path(temporary) / "l2-contract-reproduction",
                        intervention="hermetic_dispatch_test_state",
                    )
                )
        self.assertEqual(run_l1.ACTIVE_LOOP, before)

    def test_derived_loop_context_requires_its_launcher(self) -> None:
        before = run_l1.ACTIVE_LOOP
        with self.assertRaisesRegex(ValueError, "requires its reviewed launcher"):
            run_l1.configure_loop(
                run_l1.LoopContext(
                    loop_id="Q1/L2",
                    root=L2_ROOT,
                    intervention="hermetic_dispatch_test_state",
                )
            )
        self.assertEqual(run_l1.ACTIVE_LOOP, before)

    def test_recorder_enforces_stream_limit_as_infrastructure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary) / "evidence"
            evidence.mkdir()
            with patch.object(run_l1, "COMMAND_STREAM_MAX_BYTES", 16):
                result = run_l1.Recorder(evidence).run(
                    [sys.executable, "-c", "import os; os.write(1,b'x'*17)"],
                    label="stream envelope probe",
                )
            self.assertIn("stdout_size", result.limit_breach or "")
            self.assertLessEqual((evidence / result.stdout_path).stat().st_size, 16)
            with self.assertRaises(run_l1.Inconclusive):
                run_l1._require_success(result, "probe")

    def test_stream_limit_does_not_limit_descendant_files(self) -> None:
        descendant = (
            "import os,sys;"
            "fd=os.open(sys.argv[1],os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);"
            "os.ftruncate(fd,64*1024*1024);os.close(fd)"
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            recorded_file = root / "recorded-sparse-disk"
            preflight_file = root / "preflight-sparse-disk"
            parent = (
                "import subprocess,sys;"
                f"subprocess.run([sys.executable,'-c',{descendant!r},sys.argv[1]],check=True);"
                "print('ok')"
            )
            evidence = root / "evidence"
            evidence.mkdir()
            result = run_l1.Recorder(evidence).run(
                [sys.executable, "-c", parent, str(recorded_file)],
                label="recorded descendant sparse-file probe",
            )
            self.assertEqual(result.return_code, 0)
            self.assertIsNone(result.limit_breach)
            self.assertEqual(recorded_file.stat().st_size, 64 * 1024 * 1024)
            return_code, stdout, stderr, timed_out = run_l1._bounded_preflight_command(
                [sys.executable, "-c", parent, str(preflight_file)]
            )
            self.assertEqual(return_code, 0)
            self.assertEqual(stdout, b"ok\n")
            self.assertEqual(stderr, b"")
            self.assertFalse(timed_out)
            self.assertEqual(preflight_file.stat().st_size, 64 * 1024 * 1024)

    def test_exact_stdout_and_stderr_limits_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary) / "evidence"
            evidence.mkdir()
            with patch.object(run_l1, "COMMAND_STREAM_MAX_BYTES", 16):
                result = run_l1.Recorder(evidence).run(
                    [
                        sys.executable,
                        "-c",
                        "import os;os.write(1,b'o'*16);os.write(2,b'e'*16)",
                    ],
                    label="exact stream boundary probe",
                )
            self.assertEqual(result.return_code, 0)
            self.assertIsNone(result.limit_breach)
            self.assertEqual((evidence / result.stdout_path).read_bytes(), b"o" * 16)
            self.assertEqual((evidence / result.stderr_path).read_bytes(), b"e" * 16)

    def test_stdout_and_stderr_overflow_are_independently_bounded_online(self) -> None:
        for descriptor, expected, other in (
            (1, "stdout_size", 2),
            (2, "stderr_size", 1),
        ):
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as temporary:
                evidence = Path(temporary) / "evidence"
                evidence.mkdir()
                code = (
                    f"import os,time;os.write({other},b'ok');"
                    f"os.write({descriptor},b'x'*17);time.sleep(5)"
                )
                started = time.monotonic()
                with patch.object(run_l1, "COMMAND_STREAM_MAX_BYTES", 16):
                    result = run_l1.Recorder(evidence).run(
                        [sys.executable, "-c", code],
                        label=f"{expected} online probe",
                        timeout_seconds=2,
                    )
                self.assertLess(time.monotonic() - started, 1.5)
                self.assertFalse(result.timed_out)
                self.assertEqual(result.limit_breach, expected)
                target = result.stdout_path if descriptor == 1 else result.stderr_path
                self.assertEqual((evidence / target).stat().st_size, 16)

    def test_stream_overflow_kills_the_descendant_process_group(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence = root / "evidence"
            evidence.mkdir()
            marker = root / "descendant-survived"
            descendant = (
                "import pathlib,sys,time;time.sleep(0.5);"
                "pathlib.Path(sys.argv[1]).write_text('alive')"
            )
            parent = (
                "import os,subprocess,sys,time;"
                f"subprocess.Popen([sys.executable,'-c',{descendant!r},sys.argv[1]]);"
                "os.write(1,b'x'*17);time.sleep(5)"
            )
            with patch.object(run_l1, "COMMAND_STREAM_MAX_BYTES", 16):
                result = run_l1.Recorder(evidence).run(
                    [sys.executable, "-c", parent, str(marker)],
                    label="descendant stream-overflow cleanup probe",
                    timeout_seconds=2,
                )
            self.assertEqual(result.limit_breach, "stdout_size")
            time.sleep(0.75)
            self.assertFalse(marker.exists())

    def test_work_alarm_during_active_capture_kills_the_descendant_group(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            marker = Path(temporary) / "descendant-survived"
            descendant = (
                "import pathlib,sys,time;time.sleep(0.25);"
                "pathlib.Path(sys.argv[1]).write_text('alive')"
            )
            parent = (
                "import subprocess,sys,time;"
                f"subprocess.Popen([sys.executable,'-c',{descendant!r},sys.argv[1]]);"
                "time.sleep(5)"
            )
            previous_handler = signal.getsignal(signal.SIGALRM)
            previous_timer = signal.setitimer(signal.ITIMER_REAL, 0)

            def work_alarm(_signum: int, _frame: object) -> None:
                raise run_l1.ExecuteWorkDeadline()

            signal.signal(signal.SIGALRM, work_alarm)
            signal.setitimer(signal.ITIMER_REAL, 0.05)
            try:
                with self.assertRaises(run_l1.ExecuteWorkDeadline):
                    run_l1._run_bounded_process(
                        [sys.executable, "-c", parent, str(marker)],
                        environment=run_l1._safe_environment(),
                        input_bytes=None,
                        timeout_seconds=2,
                    )
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, previous_handler)
                if previous_timer[0] > 0:
                    signal.setitimer(
                        signal.ITIMER_REAL,
                        previous_timer[0],
                        previous_timer[1],
                    )
            time.sleep(0.4)
            self.assertFalse(marker.exists())

    def test_stream_overflow_never_reaches_observer_or_transform(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary) / "evidence"
            evidence.mkdir()
            observer = Mock()
            transform = Mock(return_value="transformed")
            with patch.object(run_l1, "COMMAND_STREAM_MAX_BYTES", 16):
                result = run_l1.Recorder(evidence).run(
                    [sys.executable, "-c", "import os;os.write(2,b'x'*17)"],
                    label="consumer isolation probe",
                    stdout_observer=observer,
                    stdout_transform=transform,
                )
            self.assertEqual(result.limit_breach, "stderr_size")
            observer.assert_not_called()
            transform.assert_not_called()

    def test_bounded_capture_multiplexes_input_stdout_and_stderr(self) -> None:
        code = (
            "import os,threading;"
            "a=threading.Thread(target=os.write,args=(1,b'o'*(128*1024)));"
            "b=threading.Thread(target=os.write,args=(2,b'e'*(128*1024)));"
            "a.start();b.start();a.join();b.join();"
            "data=b'';"
            "\nwhile len(data)<262144:"
            "\n chunk=os.read(0,262144-len(data))"
            "\n if not chunk: break"
            "\n data+=chunk"
        )
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary) / "evidence"
            evidence.mkdir()
            result = run_l1.Recorder(evidence).run(
                [sys.executable, "-c", code],
                label="multiplexed pipe pressure probe",
                input_text="i" * (256 * 1024),
                timeout_seconds=5,
            )
            self.assertEqual(result.return_code, 0)
            self.assertIsNone(result.limit_breach)
            self.assertEqual((evidence / result.stdout_path).stat().st_size, 128 * 1024)
            self.assertEqual((evidence / result.stderr_path).stat().st_size, 128 * 1024)

    def test_preflight_stream_overflow_is_bounded_online(self) -> None:
        for descriptor, expected in ((1, "stdout_size"), (2, "stderr_size")):
            with self.subTest(expected=expected), patch.object(
                run_l1, "COMMAND_STREAM_MAX_BYTES", 16
            ), patch.object(run_l1, "DEFAULT_COMMAND_TIMEOUT_SECONDS", 2):
                started = time.monotonic()
                with self.assertRaisesRegex(RuntimeError, expected):
                    run_l1._bounded_preflight_command(
                        [
                            sys.executable,
                            "-c",
                            f"import os,time;os.write({descriptor},b'x'*17);time.sleep(5)",
                        ]
                    )
                self.assertLess(time.monotonic() - started, 1.5)

    def test_recorder_timeout_remains_a_bounded_deadline_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary) / "evidence"
            evidence.mkdir()
            result = run_l1.Recorder(evidence).run(
                [sys.executable, "-c", "import time;time.sleep(5)"],
                label="bounded timeout probe",
                timeout_seconds=0.05,
            )
            self.assertTrue(result.timed_out)
            self.assertEqual(result.return_code, 124)
            self.assertEqual(result.limit_breach, "command_deadline")

    def test_timeout_metadata_does_not_turn_exact_stderr_into_overflow(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary) / "evidence"
            evidence.mkdir()
            with patch.object(run_l1, "COMMAND_STREAM_MAX_BYTES", 16):
                result = run_l1.Recorder(evidence).run(
                    [
                        sys.executable,
                        "-c",
                        "import os,time;os.write(2,b'e'*16);time.sleep(5)",
                    ],
                    label="exact stderr then timeout probe",
                    timeout_seconds=0.05,
                )
            self.assertTrue(result.timed_out)
            self.assertEqual(result.limit_breach, "command_deadline")
            self.assertEqual((evidence / result.stderr_path).read_bytes(), b"e" * 16)

    def test_execution_work_alarm_rearms_the_absolute_hard_deadline(self) -> None:
        deadline = run_l1.ExecutionDeadline()
        deadline.phase = deadline.WORK
        deadline.work_deadline = 110.0
        deadline.absolute_deadline = 120.0
        with (
            patch.object(run_l1.time, "monotonic", return_value=110.0),
            patch.object(deadline, "_arm") as arm,
            self.assertRaises(run_l1.ExecuteWorkDeadline),
        ):
            deadline._handle_alarm(signal.SIGALRM, None)
        self.assertEqual(deadline.phase, deadline.CLEANUP_PENDING)
        self.assertTrue(deadline.work_observed)
        self.assertEqual(deadline.hard_deadline, 120.0)
        arm.assert_called_once_with(120.0)

    def test_execution_alarm_delivered_at_the_absolute_deadline_is_hard(self) -> None:
        deadline = run_l1.ExecutionDeadline()
        deadline.phase = deadline.WORK
        deadline.work_deadline = 110.0
        deadline.absolute_deadline = 120.0
        with (
            patch.object(run_l1.time, "monotonic", return_value=120.0),
            patch.object(run_l1.signal, "setitimer") as timer,
            self.assertRaises(run_l1.ExecuteHardDeadline),
        ):
            deadline._handle_alarm(signal.SIGALRM, None)
        self.assertEqual(deadline.phase, deadline.HARD)
        self.assertTrue(deadline.hard_observed)
        timer.assert_called_once_with(signal.ITIMER_REAL, 0)

    def test_pending_work_alarm_enters_cleanup_without_extending_the_deadline(self) -> None:
        deadline = run_l1.ExecutionDeadline()
        deadline._installed = True
        deadline.phase = deadline.WORK
        deadline.work_deadline = 1_000.0
        deadline.absolute_deadline = 1_300.0
        with (
            patch.object(run_l1.signal, "pthread_sigmask", return_value=set()),
            patch.object(run_l1.signal, "setitimer"),
            patch.object(
                deadline,
                "_drain_pending_alarm",
                side_effect=[True, False],
            ),
            patch.object(run_l1.time, "monotonic", side_effect=[1_000.0, 1_001.0]),
            patch.object(deadline, "_arm") as arm,
        ):
            self.assertTrue(deadline.begin_cleanup())
            self.assertTrue(deadline.begin_cleanup())
        self.assertEqual(deadline.phase, deadline.CLEANUP)
        self.assertEqual(deadline.hard_deadline, 1_300.0)
        self.assertEqual(arm.call_args_list[0].args, (1_300.0,))
        self.assertEqual(arm.call_args_list[1].args, (1_300.0,))

    def test_early_cleanup_gets_one_five_minute_window(self) -> None:
        deadline = run_l1.ExecutionDeadline()
        deadline._installed = True
        deadline.phase = deadline.WORK
        deadline.work_deadline = 1_000.0
        deadline.absolute_deadline = 1_300.0
        with (
            patch.object(run_l1.signal, "pthread_sigmask", return_value=set()),
            patch.object(run_l1.signal, "setitimer"),
            patch.object(deadline, "_drain_pending_alarm", return_value=False),
            patch.object(run_l1.time, "monotonic", return_value=100.0),
            patch.object(deadline, "_arm") as arm,
        ):
            self.assertFalse(deadline.begin_cleanup())
        self.assertEqual(deadline.hard_deadline, 400.0)
        arm.assert_called_once_with(400.0)

    def test_execution_deadline_rejects_preexisting_alarm_state(self) -> None:
        deadline = run_l1.ExecutionDeadline()
        with (
            patch.object(run_l1.signal, "pthread_sigmask", return_value=set()),
            patch.object(run_l1.signal, "getitimer", return_value=(1.0, 0.0)),
            patch.object(run_l1.signal, "sigpending", return_value=set()),
            patch.object(run_l1.signal, "signal") as install,
            self.assertRaisesRegex(RuntimeError, "pre-existing SIGALRM"),
        ):
            deadline.install()
        install.assert_not_called()

    def test_work_alarm_at_cleanup_transition_still_runs_closure(self) -> None:
        deadline = Mock()
        deadline.begin_cleanup.side_effect = [run_l1.ExecuteWorkDeadline(), True]
        deadline.hard_deadline = 500.0
        events: list[str] = []
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (
                patch.object(run_l1, "EVIDENCE_ROOT", root / "evidence"),
                patch.object(run_l1, "RESULT_PATH", root / "RESULT.md"),
                patch.object(run_l1, "_preflight", return_value="secret"),
                patch.object(
                    run_l1,
                    "_require_api_authentication",
                    return_value={
                        "category": "api_authentication",
                        "duration_seconds": 0.25,
                        "status": 200,
                    },
                ),
                patch.object(run_l1, "_load_candidate_transfer"),
                patch.object(
                    run_l1,
                    "_run_id",
                    return_value="20260101T000000Z-deadbeef",
                ),
                patch.object(run_l1, "_perform_execution_work"),
                patch.object(
                    run_l1,
                    "_finish_execution",
                    side_effect=lambda **_kwargs: events.append("finish"),
                ) as finish,
                patch.object(
                    deadline,
                    "complete",
                    side_effect=lambda: events.append("complete"),
                ),
                patch.object(
                    run_l1,
                    "_write_completion_receipt",
                    side_effect=lambda *_args, **_kwargs: events.append("receipt"),
                ),
                patch.object(
                    run_l1,
                    "_verify_pending_index",
                    side_effect=lambda *_args, **_kwargs: events.append("verify") or {},
                ),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(run_l1._execute_locked("a" * 40, deadline), 0)
        self.assertEqual(deadline.begin_cleanup.call_count, 2)
        finish.assert_called_once()
        self.assertEqual(
            finish.call_args.kwargs["state"]["failure_stage"],
            "execution_envelope",
        )
        self.assertEqual(events, ["finish", "complete", "receipt", "verify"])

    def test_execution_closure_verifies_the_index_before_completion(self) -> None:
        recorder = Mock()
        recorder.redactions = []
        recorder.deadline_monotonic = 1_000.0
        recorder.protected_values.return_value = ()
        events: list[str] = []
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.object(run_l1, "_require_execution_deadline_open"),
            patch.object(run_l1, "_checkout_guard"),
            patch.object(
                run_l1,
                "_write_run_outputs",
                side_effect=lambda *_args, **_kwargs: events.append("write"),
            ),
            patch.object(
                run_l1,
                "_verify_pending_index",
                side_effect=lambda *_args, **_kwargs: events.append("verify") or {},
            ),
        ):
            run_l1._finish_execution(
                contract_commit="a" * 40,
                evidence=Path(temporary),
                recorder=recorder,
                state={"status": "Inconclusive"},
                instance="q1-l1-candidate-20260101t000000z-deadbeef",
                run_id="20260101T000000Z-deadbeef",
                context={
                    "candidate_vm_observed_monotonic": None,
                    "login_attempted": False,
                    "provision_attempted": False,
                },
                run_started_monotonic=0.0,
                final_phase_deadline=500.0,
            )
        self.assertEqual(events, ["write", "verify"])
        recorder.clear_protected_values.assert_called_once_with()

    def test_api_key_omission_requires_candidate_login_attempt(self) -> None:
        self.assertEqual(run_l1._api_key_omissions({"login_attempted": False}), [])
        omission = run_l1._api_key_omissions({"login_attempted": True})
        self.assertEqual(len(omission), 1)
        self.assertEqual(omission[0]["item"], "OpenAI API key")
        self.assertIn("candidate login", omission[0]["reason"])

    def test_hard_completion_barrier_leaves_no_execution_receipt(self) -> None:
        deadline = Mock()
        deadline.begin_cleanup.return_value = False
        deadline.hard_deadline = 500.0
        deadline.complete.side_effect = run_l1.ExecuteHardDeadline()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (
                patch.object(run_l1, "EVIDENCE_ROOT", root / "evidence"),
                patch.object(run_l1, "RESULT_PATH", root / "RESULT.md"),
                patch.object(run_l1, "_preflight", return_value="secret"),
                patch.object(
                    run_l1,
                    "_require_api_authentication",
                    return_value={
                        "category": "api_authentication",
                        "duration_seconds": 0.25,
                        "status": 200,
                    },
                ),
                patch.object(run_l1, "_load_candidate_transfer"),
                patch.object(
                    run_l1,
                    "_run_id",
                    return_value="20260101T000000Z-deadbeef",
                ),
                patch.object(run_l1, "_perform_execution_work"),
                patch.object(run_l1, "_finish_execution"),
                patch.object(run_l1, "_write_completion_receipt") as receipt,
                self.assertRaises(run_l1.ExecuteHardDeadline),
            ):
                run_l1._execute_locked("a" * 40, deadline)
        receipt.assert_not_called()

    def test_completion_barrier_rejects_pending_or_elapsed_hard_deadline(self) -> None:
        cases = ((True, 100.0), (False, 200.0))
        for pending, now in cases:
            with self.subTest(pending=pending, now=now):
                deadline = run_l1.ExecutionDeadline()
                deadline._installed = True
                deadline.phase = deadline.CLEANUP
                deadline.hard_deadline = 200.0
                with (
                    patch.object(run_l1.signal, "pthread_sigmask", return_value=set()),
                    patch.object(run_l1.signal, "setitimer"),
                    patch.object(deadline, "_drain_pending_alarm", return_value=pending),
                    patch.object(run_l1.time, "monotonic", return_value=now),
                    self.assertRaises(run_l1.ExecuteHardDeadline),
                ):
                    deadline.complete()
                self.assertEqual(deadline.phase, deadline.HARD)
                self.assertTrue(deadline.hard_observed)

    def test_successful_completion_barrier_makes_late_alarm_inert(self) -> None:
        deadline = run_l1.ExecutionDeadline()
        deadline._installed = True
        deadline.phase = deadline.CLEANUP
        deadline.hard_deadline = 200.0
        with (
            patch.object(run_l1.signal, "pthread_sigmask", return_value=set()),
            patch.object(run_l1.signal, "setitimer") as timer,
            patch.object(deadline, "_drain_pending_alarm", return_value=False),
            patch.object(run_l1.time, "monotonic", return_value=199.0),
        ):
            deadline.complete()
            deadline._handle_alarm(signal.SIGALRM, None)
        self.assertEqual(deadline.phase, deadline.COMPLETE)
        timer.assert_called_once_with(signal.ITIMER_REAL, 0)

    def test_alarm_during_process_handoff_kills_and_reaps_the_child(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary) / "evidence"
            evidence.mkdir()
            process = Mock(pid=1234, returncode=0)
            process.communicate.return_value = (None, None)
            with (
                patch.object(run_l1.subprocess, "Popen", return_value=process),
                patch.object(
                    run_l1.signal,
                    "pthread_sigmask",
                    side_effect=[set(), run_l1.ExecuteWorkDeadline()],
                ),
                patch.object(run_l1, "_kill_and_reap_process_group") as cleanup,
                self.assertRaises(run_l1.ExecuteWorkDeadline),
            ):
                run_l1.Recorder(evidence).run(
                    [sys.executable, "-c", "pass"],
                    label="alarm handoff probe",
                )
            cleanup.assert_called_once_with(process, hard_cutoff_active=False)

    def test_alarm_during_preflight_handoff_kills_and_reaps_the_child(self) -> None:
        process = Mock(pid=1234, returncode=0)
        with (
            patch.object(run_l1.subprocess, "Popen", return_value=process),
            patch.object(
                run_l1.signal,
                "pthread_sigmask",
                side_effect=[set(), run_l1.FinalizationHardDeadline()],
            ),
            patch.object(run_l1, "_kill_and_reap_process_group") as cleanup,
            self.assertRaises(run_l1.FinalizationHardDeadline),
        ):
            run_l1._bounded_preflight_command([sys.executable, "-c", "pass"])
        cleanup.assert_called_once_with(process, hard_cutoff_active=True)

    def test_kill_and_reap_kills_before_exposing_the_alarm(self) -> None:
        process = Mock(pid=1234, stdin=None)
        events: list[str] = []

        def mask(how: int, _signals: set[signal.Signals]) -> set[signal.Signals]:
            events.append("block" if how == signal.SIG_BLOCK else "unmask")
            return set()

        process.wait.side_effect = lambda *, timeout: events.append("reap") or 0
        with (
            patch.object(run_l1.signal, "pthread_sigmask", side_effect=mask),
            patch.object(
                run_l1,
                "_kill_process_group",
                side_effect=lambda _process: events.append("kill"),
            ),
        ):
            run_l1._kill_and_reap_process_group(process)
        self.assertEqual(events, ["block", "kill", "unmask", "reap"])
        process.wait.assert_called_once_with(timeout=1.0)

    def test_work_alarm_after_kill_is_deferred_until_the_child_is_reaped(self) -> None:
        process = Mock(pid=1234, stdin=None)
        with (
            patch.object(
                run_l1.signal,
                "pthread_sigmask",
                side_effect=[set(), run_l1.ExecuteWorkDeadline()],
            ),
            patch.object(run_l1, "_kill_process_group") as kill,
            self.assertRaises(run_l1.ExecuteWorkDeadline),
        ):
            run_l1._kill_and_reap_process_group(process)
        kill.assert_called_once_with(process)
        process.wait.assert_called_once_with(timeout=1.0)

    def test_work_alarm_during_reap_gets_one_hard_bounded_reap_retry(self) -> None:
        process = Mock(pid=1234, stdin=None)
        process.wait.side_effect = [run_l1.ExecuteWorkDeadline(), 0]
        with (
            patch.object(run_l1.signal, "pthread_sigmask", return_value=set()),
            patch.object(run_l1, "_kill_process_group") as kill,
            self.assertRaises(run_l1.ExecuteWorkDeadline),
        ):
            run_l1._kill_and_reap_process_group(process)
        kill.assert_called_once_with(process)
        self.assertEqual(process.wait.call_count, 2)
        process.wait.assert_called_with(timeout=1.0)

    def test_hard_alarm_after_kill_only_attempts_a_nonblocking_reap(self) -> None:
        for exception_type in (
            run_l1.ExecuteHardDeadline,
            run_l1.FinalizationHardDeadline,
        ):
            with self.subTest(exception_type=exception_type):
                process = Mock(pid=1234, stdin=None)
                with (
                    patch.object(
                        run_l1.signal,
                        "pthread_sigmask",
                        side_effect=[set(), exception_type()],
                    ),
                    patch.object(run_l1, "_kill_process_group") as kill,
                    self.assertRaises(exception_type),
                ):
                    run_l1._kill_and_reap_process_group(process)
                kill.assert_called_once_with(process)
                process.wait.assert_called_once_with(timeout=0)

    def test_already_active_hard_cutoff_only_attempts_a_nonblocking_reap(self) -> None:
        process = Mock(pid=1234, stdin=None)
        with (
            patch.object(run_l1.signal, "pthread_sigmask", return_value=set()),
            patch.object(run_l1, "_kill_process_group") as kill,
        ):
            run_l1._kill_and_reap_process_group(
                process,
                hard_cutoff_active=True,
            )
        kill.assert_called_once_with(process)
        process.wait.assert_called_once_with(timeout=0)

    def test_finalization_alarm_during_reap_never_waits_again(self) -> None:
        process = Mock(pid=1234, stdin=None)
        process.wait.side_effect = [
            run_l1.FinalizationHardDeadline(),
            subprocess.TimeoutExpired("reap", 0),
        ]
        with (
            patch.object(run_l1.signal, "pthread_sigmask", return_value=set()),
            patch.object(run_l1, "_kill_process_group") as kill,
            self.assertRaises(run_l1.FinalizationHardDeadline),
        ):
            run_l1._kill_and_reap_process_group(process)
        kill.assert_called_once_with(process)
        self.assertEqual(
            [call.kwargs["timeout"] for call in process.wait.call_args_list],
            [1.0, 0],
        )

    def test_hard_execution_deadline_reports_incomplete_terminal_evidence(self) -> None:
        stderr = io.StringIO()
        deadline = Mock()
        deadline.restore_blocked.return_value = False
        with (
            patch.object(run_l1, "_acquire_execution_lock", return_value=1234),
            patch.object(run_l1, "ExecutionDeadline", return_value=deadline),
            patch.object(
                run_l1, "_execute_locked", side_effect=run_l1.ExecuteHardDeadline()
            ),
            patch.object(run_l1.signal, "pthread_sigmask", return_value=set()),
            patch.object(run_l1.os, "close") as close,
            redirect_stderr(stderr),
        ):
            self.assertEqual(run_l1.execute("a" * 40), 2)
        deadline.install.assert_called_once_with()
        deadline.abort.assert_called_once_with()
        deadline.restore_blocked.assert_called_once_with()
        close.assert_called_once_with(1234)
        recovery = json.loads(stderr.getvalue())
        self.assertEqual(recovery["status"], "Inconclusive")
        self.assertEqual(recovery["recovery"], "human_required")
        self.assertEqual(recovery["terminal_evidence"], "incomplete")

    def test_execute_restore_hard_cutoff_overrides_an_ordinary_failure(self) -> None:
        stderr = io.StringIO()
        deadline = Mock()
        deadline.restore_blocked.side_effect = run_l1.ExecuteHardDeadline()
        with (
            patch.object(run_l1, "_acquire_execution_lock", return_value=1234),
            patch.object(run_l1, "ExecutionDeadline", return_value=deadline),
            patch.object(run_l1, "_execute_locked", side_effect=ValueError("ordinary")),
            patch.object(run_l1.signal, "pthread_sigmask", return_value=set()),
            patch.object(run_l1.os, "close") as close,
            redirect_stderr(stderr),
        ):
            self.assertEqual(run_l1.execute("a" * 40), 2)
        recovery = json.loads(stderr.getvalue())
        self.assertEqual(recovery["recovery"], "human_required")
        self.assertEqual(recovery["terminal_evidence"], "incomplete")
        close.assert_called_once_with(1234)

    def test_execution_deadline_restore_orders_handler_before_timer(self) -> None:
        deadline = run_l1.ExecutionDeadline()
        deadline._installed = True
        deadline.phase = deadline.COMPLETE
        deadline._previous_handler = signal.SIG_DFL
        deadline._previous_timer = (0.0, 0.0)
        deadline._previous_mask = set()
        events: list[tuple[str, object]] = []

        with (
            patch.object(
                run_l1.signal,
                "setitimer",
                side_effect=lambda *args: events.append(("timer", args)),
            ),
            patch.object(
                deadline,
                "_drain_pending_alarm",
                side_effect=lambda: events.append(("drain", None)) or False,
            ),
            patch.object(
                run_l1.signal,
                "signal",
                side_effect=lambda _signum, handler: events.append(("handler", handler)),
            ),
            patch.object(run_l1.time, "monotonic", return_value=0.0),
        ):
            self.assertFalse(deadline.restore_blocked())
        self.assertEqual(
            events,
            [
                ("timer", (signal.ITIMER_REAL, 0)),
                ("drain", None),
                ("handler", signal.SIG_DFL),
                ("timer", (signal.ITIMER_REAL, 0.0, 0.0)),
            ],
        )

    def test_execute_closes_the_lock_before_unmasking_sigalrm(self) -> None:
        events: list[str] = []
        deadline = Mock()
        deadline.restore_blocked.side_effect = lambda: events.append("restore") or False

        def mask(how: int, _signals: set[signal.Signals]) -> set[signal.Signals]:
            events.append("block" if how == signal.SIG_BLOCK else "unmask")
            return set()

        with (
            patch.object(run_l1, "_acquire_execution_lock", return_value=1234),
            patch.object(run_l1, "ExecutionDeadline", return_value=deadline),
            patch.object(run_l1, "_execute_locked", return_value=0),
            patch.object(run_l1.signal, "pthread_sigmask", side_effect=mask),
            patch.object(
                run_l1.os,
                "close",
                side_effect=lambda _descriptor: events.append("close"),
            ),
        ):
            self.assertEqual(run_l1.execute("a" * 40), 0)
        self.assertEqual(events, ["block", "restore", "close", "unmask"])

    def test_evidence_cap_reserves_capacity_for_closure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary) / "evidence"
            evidence.mkdir()
            (evidence / "payload").write_bytes(b"x" * 80)
            with (
                patch.object(run_l1, "RETAINED_EVIDENCE_MAX_BYTES", 100),
                patch.object(run_l1, "EVIDENCE_CLOSURE_RESERVE_BYTES", 20),
            ):
                run_l1._require_evidence_capacity(evidence, 0)
                with self.assertRaises(run_l1.Inconclusive):
                    run_l1._require_evidence_capacity(evidence, 1)
                run_l1._require_evidence_capacity(
                    evidence,
                    20,
                    reserve_closure=False,
                )

    def test_nonempty_evidence_blocks_before_lima_preflight(self) -> None:
        run_l1.EVIDENCE_ROOT.mkdir()
        (run_l1.EVIDENCE_ROOT / "existing-run").mkdir()
        with patch.object(run_l1, "_preflight_lima_records") as lima_records:
            with self.assertRaisesRegex(RuntimeError, "human recovery is required"):
                run_l1._assert_no_orphaned_run()
        lima_records.assert_not_called()

    def test_evaluator_residue_unknown_blocks_a_new_run(self) -> None:
        with (
            patch.object(
                run_l1,
                "_preflight_lima_records",
                return_value=[{"name": "q1-l1-evaluator", "status": "Running"}],
            ),
            patch.object(run_l1, "_preflight_evaluator_orphans", return_value=None),
        ):
            with self.assertRaisesRegex(RuntimeError, "review is required"):
                run_l1._assert_no_orphaned_run()

    def test_stopped_evaluator_is_a_preparation_fault(self) -> None:
        with patch.object(
            run_l1,
            "_preflight_lima_records",
            return_value=[{"name": "q1-l1-evaluator", "status": "Stopped"}],
        ):
            with self.assertRaisesRegex(RuntimeError, "prepared and Running"):
                run_l1._assert_no_orphaned_run()

    def test_run_scoped_candidate_vm_is_not_setup_cleanup(self) -> None:
        with patch.object(
            run_l1,
            "_preflight_lima_records",
            return_value=[
                {
                    "name": "q1-l1-candidate-20260101t000000z-deadbeef",
                    "status": "Running",
                },
                {"name": "q1-l1-evaluator", "status": "Running"},
            ],
        ):
            with self.assertRaisesRegex(RuntimeError, "review is required"):
                run_l1._assert_no_orphaned_run()

    def test_candidate_namespace_excludes_the_dedicated_evaluator(self) -> None:
        self.assertIsNone(run_l1.INSTANCE_PATTERN.fullmatch(run_l1.EVALUATOR_INSTANCE))
        self.assertIsNotNone(
            run_l1.INSTANCE_PATTERN.fullmatch(
                "q1-l1-candidate-20260101t000000z-deadbeef"
            )
        )

    def test_empty_evidence_symlink_blocks_a_new_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "outside"
            target.mkdir()
            evidence = root / "evidence"
            evidence.symlink_to(target, target_is_directory=True)
            with patch.object(run_l1, "EVIDENCE_ROOT", evidence):
                with self.assertRaisesRegex(RuntimeError, "not a real directory"):
                    run_l1._assert_no_orphaned_run()

    def test_boundary_report_writer_does_not_follow_the_old_fixed_temp_name(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = root / "candidate-boundary-validation.json"
            victim = root / "victim"
            victim.write_text("unchanged", encoding="utf-8")
            old_temporary = root / ".candidate-boundary-validation.json.tmp"
            old_temporary.symlink_to(victim)
            verify_candidate_boundary._write_report(report, {"passed": True})
            self.assertEqual(victim.read_text(encoding="utf-8"), "unchanged")
            self.assertTrue(old_temporary.is_symlink())
            self.assertEqual(
                json.loads(report.read_text(encoding="utf-8")),
                {"passed": True},
            )

    def test_evaluator_residue_report_discloses_only_zero_counts(self) -> None:
        empty = {key: 0 for key in ("cgroups", "loops", "mounts", "processes", "roots")}
        self.assertEqual(
            json.loads(
                run_l1._normalized_evaluator_orphans(
                    json.dumps({"counts": empty, "passed": True, "version": 1})
                )
            ),
            {"counts": {key: 0 for key in sorted(empty)}, "passed": True, "version": 1},
        )
        with self.assertRaises(ValueError):
            run_l1._normalized_evaluator_orphans(
                json.dumps(
                    {
                        "counts": {**empty, "roots": 1},
                        "passed": False,
                        "version": 1,
                    }
                )
            )

    def test_evaluator_residue_process_match_includes_environment_only_root(self) -> None:
        root = b"/tmp/q1-l1-run-20260101T000000Z-deadbeef"
        self.assertTrue(
            evaluator_residue_probe._payload_matches(
                b"/usr/bin/python3\0service.py\0",
                b"Q1_L1_CANDIDATE_ROOT=" + root + b"/candidate\0",
                b"/work",
                b"/",
                run_root=root,
            )
        )
        self.assertTrue(
            evaluator_residue_probe._mountinfo_matches(
                b"1 2 0:3 / /tmp/q1-l1-run-test rw - ext4 /dev/loop0 rw\n",
                run_root=root,
            )
        )

    def test_evaluator_residue_covers_every_q1_l1_resource_root(self) -> None:
        for prefix in evaluator_residue_probe.ENCODED_RESOURCE_ROOT_PREFIXES:
            path = prefix + b"owned"
            with self.subTest(path=path):
                self.assertTrue(evaluator_residue_probe._resource_path_matches(path))
                self.assertTrue(
                    evaluator_residue_probe._payload_matches(
                        b"/usr/bin/python3\0",
                        b"",
                        path,
                        b"/",
                        run_root=None,
                    )
                )
                self.assertTrue(
                    evaluator_residue_probe._mountinfo_matches(
                        b"1 2 0:3 / " + path + b" rw - ext4 /dev/loop0 rw\n",
                        run_root=None,
                    )
                )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            names = tuple(
                prefix.removeprefix("/tmp/") + "owned"
                for prefix in evaluator_residue_probe.RESOURCE_ROOT_PREFIXES
            )
            for name in (*names, "q1-unrelated"):
                (root / name).mkdir()
            self.assertEqual(
                evaluator_residue_probe._count_prefixed_entries(
                    root,
                    tuple(
                        prefix.removeprefix("/tmp/")
                        for prefix in evaluator_residue_probe.RESOURCE_ROOT_PREFIXES
                    ),
                    recursive=False,
                ),
                len(names),
            )

    def test_evaluator_residue_covers_q1_l1_cgroups(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            nested = root / "nested"
            nested.mkdir()
            for prefix in evaluator_residue_probe.CGROUP_PREFIXES:
                (nested / f"{prefix}owned").mkdir()
            (nested / "q1-unrelated").mkdir()
            self.assertEqual(
                evaluator_residue_probe._count_prefixed_entries(
                    root,
                    evaluator_residue_probe.CGROUP_PREFIXES,
                    recursive=True,
                ),
                len(evaluator_residue_probe.CGROUP_PREFIXES),
            )

    def test_evaluator_residue_ignores_retired_global_names(self) -> None:
        self.assertFalse(
            evaluator_residue_probe._payload_matches(
                b"python3 verify_dispatch.py\0",
                b"CT_CANDIDATE_ROOT=/tmp/envelope-old/candidate\0",
                b"/tmp/envelope-old",
                b"/",
                run_root=None,
            )
        )
        self.assertFalse(
            evaluator_residue_probe._mountinfo_matches(
                b"1 2 0:3 / /tmp/envelope-old rw - ext4 /dev/loop0 rw\n",
                run_root=None,
            )
        )
        self.assertFalse(
            evaluator_residue_probe._payload_matches(
                b"python3 verify_evaluator.py\0",
                b"ErrorEnvelope=unchanged\0",
                b"/tmp/q1-unrelated",
                b"/",
                run_root=None,
            )
        )

    def test_isolation_validator_temp_root_is_residue_scoped(self) -> None:
        source = (ROOT / "reproduction" / "verify_isolated_runtime.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('prefix="q1-l1-isolation-validation-"', source)

    def test_evaluator_run_parents_are_traversable_but_not_listable(self) -> None:
        self.assertEqual(run_l1.EVALUATOR_RUN_DIRECTORY_MODE, 0o711)

    def test_evaluator_fixture_cannot_write_bytecode(self) -> None:
        argv = shlex.split(verify_evaluator.DEFAULT_FIXTURE_COMMAND)
        self.assertEqual(argv[:4], ["/usr/bin/python3", "-B", "-I", "-c"])
        self.assertEqual(argv[-1], "evaluator.fixtures.service")

    def test_repeated_service_mount_attestations_must_all_match(self) -> None:
        marker = verify_isolated_runtime.SERVICE_MOUNT_MARKER
        valid = json.dumps(
            {
                "/state": list(verify_isolated_runtime.APPROVED_MOUNT_OPTIONS),
                "/tmp": list(verify_isolated_runtime.APPROVED_MOUNT_OPTIONS),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        self.assertTrue(
            verify_isolated_runtime._service_mount_options_valid(
                f"{marker}{valid}\n{marker}{valid}\n"
            )
        )
        self.assertFalse(
            verify_isolated_runtime._service_mount_options_valid(
                f'{marker}{valid}\n{marker}{{"/state":[],"/tmp":[]}}\n'
            )
        )

    def test_stopped_evaluator_is_rejected_before_guest_collection(self) -> None:
        with self.assertRaisesRegex(ValueError, "not already running"):
            run_l1._normalized_evaluator_lima(
                json.dumps({"name": "q1-l1-evaluator", "status": "Stopped"})
            )

    def test_pending_index_covers_evidence_and_result_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence = root / "evidence"
            evidence.mkdir()
            run_l1._write_json(
                evidence / "setup" / run_l1.API_AUTHENTICATION_REPORT,
                {
                    "category": "api_authentication",
                    "duration_seconds": 0.25,
                    "status": 200,
                },
            )
            (evidence / "record.json").write_text("{}\n", encoding="utf-8")
            result = root / "RESULT.md"
            result.write_text("# result\n", encoding="utf-8")
            (evidence / "pending-RESULT.md").write_text("# result\n", encoding="utf-8")
            with patch.object(run_l1, "RESULT_PATH", result):
                index = run_l1._evidence_index(evidence)
                self.assertGreaterEqual(index["inventory_scan_hash_elapsed_seconds"], 0)
                self.assertEqual(index["artifact_self_recording_tail_seconds"], "unknown")
                self.assertNotIn("generation_duration_seconds", index)
                run_l1._write_json(
                    evidence / "evidence-index.json",
                    index,
                )
                run_l1._verify_pending_index(evidence, require_completion=False)
                (evidence / "unindexed.txt").write_text("new\n", encoding="utf-8")
                with self.assertRaises(ValueError):
                    run_l1._verify_pending_index(evidence, require_completion=False)

    def test_nested_index_named_file_is_not_omitted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence = root / "evidence"
            evidence.mkdir()
            run_l1._write_json(
                evidence / "setup" / run_l1.API_AUTHENTICATION_REPORT,
                {
                    "category": "api_authentication",
                    "duration_seconds": 0.25,
                    "status": 200,
                },
            )
            nested = evidence / "candidate" / "evidence-index.json"
            nested.parent.mkdir()
            nested.write_text("nested\n", encoding="utf-8")
            (evidence / "pending-RESULT.md").write_text("pending\n", encoding="utf-8")
            result = root / "RESULT.md"
            result.write_text("pending\n", encoding="utf-8")
            with patch.object(run_l1, "RESULT_PATH", result):
                index = run_l1._evidence_index(evidence)
                self.assertIn(
                    "candidate/evidence-index.json",
                    {record["path"] for record in index["files"]},
                )
                run_l1._write_json(evidence / "evidence-index.json", index)
                run_l1._verify_pending_index(evidence, require_completion=False)
                nested.write_text("changed\n", encoding="utf-8")
                with self.assertRaises(ValueError):
                    run_l1._verify_pending_index(evidence, require_completion=False)

    def test_preexisting_terminal_evidence_requires_human_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence, result, state = self._pending_generation(root)
            pending_index = run_l1._read_json(evidence / "evidence-index.json")
            pending_hashes = {
                record["path"]: record["sha256"] for record in pending_index["files"]
            }
            attestation = {
                "active_minutes": 3,
                "approved_boundary_exceptions": [],
                "decision": "Affirmative",
                "findings": [],
                "reviewed_candidate_identity_sha256": state[
                    "final_candidate_identity_sha256"
                ],
                "reviewed_manifest_sha256": state["final_manifest_sha256"],
            }
            settlement = run_l1._settlement_value(
                evidence=evidence,
                run_id=state["run_id"],
                contract_commit=state["contract_commit"],
                pending_state=state,
                pending_valid=True,
                pending_detail=None,
                attestation=attestation,
                received_at="2026-01-01T00:02:00+00:00",
                finalization_elapsed_lower_bound_seconds=1.25,
            )
            with patch.object(run_l1, "RESULT_PATH", result):
                self._write_finalization_marker(evidence, state)
                run_l1._atomic_write_new(
                    evidence / "settlement.json",
                    (json.dumps(settlement, indent=2, sort_keys=True) + "\n").encode(),
                )
                run_l1._close_terminal_evidence(evidence, settlement)
                run_l1._write_completion_receipt(
                    evidence,
                    kind="finalization",
                    run_id=state["run_id"],
                    contract_commit=state["contract_commit"],
                )
                observed = run_l1._verify_terminal_index(
                    evidence,
                    run_id=state["run_id"],
                    contract_commit=state["contract_commit"],
                )
                self.assertEqual(observed["status"], "Accepted")
                self.assertEqual(
                    observed["terminal_state"][
                        "finalization_elapsed_lower_bound_seconds"
                    ],
                    1.25,
                )
                self.assertEqual(
                    observed["accounting"]["trusted_machine"][
                        "finalization_elapsed_lower_bound_seconds"
                    ],
                    1.25,
                )
                terminal_index = run_l1._read_json(
                    evidence / "terminal-evidence-index.json"
                )
                self.assertEqual(
                    terminal_index["artifact_self_recording_tail_seconds"],
                    "unknown",
                )
                self.assertIn(
                    run_l1.FINALIZATION_ATTEMPT_NAME,
                    {record["path"] for record in terminal_index["files"]},
                )
                first_result = result.read_bytes()
                with self.assertRaisesRegex(
                    ValueError,
                    "pre-existing terminal evidence requires human recovery",
                ):
                    run_l1._close_terminal_evidence(evidence, settlement)
                self.assertEqual(result.read_bytes(), first_result)
            for relative, digest in pending_hashes.items():
                self.assertEqual(run_l1._sha256(evidence / relative), digest)

    def test_finalization_attempt_marker_is_a_one_shot_pending_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence, result, state = self._pending_generation(root)
            pending_index = run_l1._read_json(evidence / "evidence-index.json")
            pending_hashes = {
                record["path"]: record["sha256"] for record in pending_index["files"]
            }
            evidence_root = root / "runs"
            evidence_root.mkdir()
            run_evidence = evidence_root / state["run_id"]
            evidence.rename(run_evidence)
            with (
                patch.object(run_l1, "EVIDENCE_ROOT", evidence_root),
                patch.object(run_l1, "RESULT_PATH", result),
            ):
                run_l1._begin_finalization_attempt(
                    state["run_id"],
                    state["contract_commit"],
                )
                marker = run_l1._validate_finalization_attempt(
                    run_evidence,
                    run_id=state["run_id"],
                    contract_commit=state["contract_commit"],
                )
                self.assertEqual(marker["version"], 1)
                run_l1._verify_pending_index(run_evidence, allow_terminal=True)
                snapshot = {
                    path.relative_to(run_evidence).as_posix(): path.read_bytes()
                    for path in run_evidence.rglob("*")
                    if path.is_file()
                }
                with self.assertRaisesRegex(ValueError, "human recovery"):
                    run_l1._begin_finalization_attempt(
                        state["run_id"],
                        state["contract_commit"],
                    )
                self.assertEqual(
                    snapshot,
                    {
                        path.relative_to(run_evidence).as_posix(): path.read_bytes()
                        for path in run_evidence.rglob("*")
                        if path.is_file()
                    },
                )
            for relative, digest in pending_hashes.items():
                self.assertEqual(run_l1._sha256(run_evidence / relative), digest)

    def test_finalization_attempt_rejects_partial_terminal_temp_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence, result, state = self._pending_generation(root)
            evidence_root = root / "runs"
            evidence_root.mkdir()
            run_evidence = evidence_root / state["run_id"]
            evidence.rename(run_evidence)
            (run_evidence / ".settlement.json.interrupted.tmp").write_bytes(b"partial")
            with (
                patch.object(run_l1, "EVIDENCE_ROOT", evidence_root),
                patch.object(run_l1, "RESULT_PATH", result),
                self.assertRaisesRegex(ValueError, "human recovery"),
            ):
                run_l1._begin_finalization_attempt(
                    state["run_id"],
                    state["contract_commit"],
                )
            self.assertFalse(
                (run_evidence / run_l1.FINALIZATION_ATTEMPT_NAME).exists()
            )

    def test_missing_execution_receipt_stops_before_finalization_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence, result, state = self._pending_generation(root)
            evidence_root = root / "runs"
            evidence_root.mkdir()
            run_evidence = evidence_root / state["run_id"]
            evidence.rename(run_evidence)
            (run_evidence / run_l1.EXECUTION_COMPLETION_NAME).unlink()
            with (
                patch.object(run_l1, "EVIDENCE_ROOT", evidence_root),
                patch.object(run_l1, "RESULT_PATH", result),
                patch.object(run_l1, "_checkout_guard"),
                patch.object(run_l1, "_acquire_execution_lock", return_value=1234),
                patch.object(run_l1.signal, "pthread_sigmask", return_value=set()),
                patch.object(run_l1.os, "close"),
                self.assertRaisesRegex(ValueError, "human recovery"),
            ):
                run_l1.finalize(
                    state["run_id"],
                    root / "attestation.json",
                    state["contract_commit"],
                )
            self.assertFalse(
                (run_evidence / run_l1.FINALIZATION_ATTEMPT_NAME).exists()
            )

    def test_checkout_guard_runs_before_finalization_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence, result, state = self._pending_generation(root)
            evidence_root = root / "runs"
            evidence_root.mkdir()
            run_evidence = evidence_root / state["run_id"]
            evidence.rename(run_evidence)
            with (
                patch.object(run_l1, "EVIDENCE_ROOT", evidence_root),
                patch.object(run_l1, "RESULT_PATH", result),
                patch.object(
                    run_l1,
                    "_checkout_guard",
                    side_effect=RuntimeError("wrong checkout"),
                ),
                patch.object(run_l1, "_acquire_execution_lock", return_value=1234),
                patch.object(run_l1.signal, "pthread_sigmask", return_value=set()),
                patch.object(run_l1.os, "close"),
                self.assertRaisesRegex(RuntimeError, "wrong checkout"),
            ):
                run_l1.finalize(
                    state["run_id"],
                    root / "attestation.json",
                    state["contract_commit"],
                )
            self.assertFalse(
                (run_evidence / run_l1.FINALIZATION_ATTEMPT_NAME).exists()
            )

    def test_finalization_installs_the_full_300_second_timer(self) -> None:
        deadline = run_l1.FinalizationDeadline()
        with (
            patch.object(run_l1.signal, "pthread_sigmask", return_value=set()),
            patch.object(run_l1.signal, "getitimer", return_value=(0.0, 0.0)),
            patch.object(run_l1.signal, "sigpending", return_value=set()),
            patch.object(run_l1.signal, "getsignal", return_value=signal.SIG_DFL),
            patch.object(run_l1.signal, "signal"),
            patch.object(run_l1.signal, "setitimer") as timer,
            patch.object(run_l1.time, "monotonic", return_value=100.0),
        ):
            deadline.install()
        self.assertEqual(deadline.deadline, 400.0)
        timer.assert_called_once_with(signal.ITIMER_REAL, 300)

    def test_finalization_hard_cutoff_writes_only_the_attempt_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence, result, state = self._pending_generation(root)
            evidence_root = root / "runs"
            evidence_root.mkdir()
            run_evidence = evidence_root / state["run_id"]
            evidence.rename(run_evidence)
            before = {
                path.relative_to(run_evidence).as_posix(): path.read_bytes()
                for path in run_evidence.rglob("*")
                if path.is_file()
            }
            result_before = result.read_bytes()
            deadline = Mock()
            deadline.restore_blocked.return_value = True
            stderr = io.StringIO()
            with (
                patch.object(run_l1, "EVIDENCE_ROOT", evidence_root),
                patch.object(run_l1, "RESULT_PATH", result),
                patch.object(run_l1, "_acquire_execution_lock", return_value=1234),
                patch.object(run_l1, "_checkout_guard"),
                patch.object(run_l1, "FinalizationDeadline", return_value=deadline),
                patch.object(
                    run_l1,
                    "_finalize_locked",
                    side_effect=run_l1.FinalizationHardDeadline(),
                ),
                patch.object(run_l1.signal, "pthread_sigmask", return_value=set()),
                patch.object(run_l1.os, "close") as close,
                redirect_stderr(stderr),
            ):
                self.assertEqual(
                    run_l1.finalize(
                        state["run_id"],
                        root / "attestation.json",
                        state["contract_commit"],
                    ),
                    2,
                )
            after = {
                path.relative_to(run_evidence).as_posix(): path.read_bytes()
                for path in run_evidence.rglob("*")
                if path.is_file()
            }
            marker = after.pop(run_l1.FINALIZATION_ATTEMPT_NAME)
            self.assertTrue(marker)
            self.assertEqual(after, before)
            self.assertEqual(result.read_bytes(), result_before)
            self.assertFalse((run_evidence / "settlement.json").exists())
            self.assertFalse((run_evidence / "terminal-evidence-index.json").exists())
            self.assertEqual(
                stderr.getvalue(),
                '{"failure_stage":"finalization_deadline","recovery":"human_required",'
                '"status":"Inconclusive","terminal_evidence":"incomplete"}\n',
            )
            deadline.install.assert_called_once_with()
            deadline.restore_blocked.assert_called_once_with()
            self.assertEqual(
                sum(call.args == (1234,) for call in close.call_args_list),
                1,
            )

    def test_finalization_alarm_is_hard_and_cancels_the_timer(self) -> None:
        deadline = run_l1.FinalizationDeadline()
        with (
            patch.object(run_l1.signal, "setitimer") as timer,
            self.assertRaises(run_l1.FinalizationHardDeadline),
        ):
            deadline._handle_alarm(signal.SIGALRM, None)
        self.assertTrue(deadline.hard_observed)
        timer.assert_called_once_with(signal.ITIMER_REAL, 0)

    def test_finalization_restore_preserves_pending_deadline_precedence(self) -> None:
        deadline = run_l1.FinalizationDeadline()
        deadline._installed = True
        deadline.deadline = 200.0
        deadline._previous_handler = signal.SIG_DFL
        deadline._previous_timer = (0.0, 0.0)
        events: list[tuple[str, object]] = []
        with (
            patch.object(
                run_l1.signal,
                "setitimer",
                side_effect=lambda *args: events.append(("timer", args)),
            ),
            patch.object(
                deadline,
                "_drain_pending_alarm",
                side_effect=lambda: events.append(("drain", None)) or True,
            ),
            patch.object(run_l1.time, "monotonic", return_value=100.0),
            patch.object(
                run_l1.signal,
                "signal",
                side_effect=lambda _signum, handler: events.append(("handler", handler)),
            ),
        ):
            self.assertTrue(deadline.restore_blocked())
        self.assertEqual(
            events,
            [
                ("timer", (signal.ITIMER_REAL, 0)),
                ("drain", None),
                ("handler", signal.SIG_DFL),
                ("timer", (signal.ITIMER_REAL, 0.0, 0.0)),
            ],
        )

    def test_finalization_completion_barrier_owns_the_unmeasured_receipt_tail(self) -> None:
        deadline = run_l1.FinalizationDeadline()
        deadline._installed = True
        deadline.completed = True
        deadline.deadline = 200.0
        deadline._previous_handler = signal.SIG_DFL
        deadline._previous_timer = (0.0, 0.0)
        with (
            patch.object(run_l1.signal, "setitimer"),
            patch.object(deadline, "_drain_pending_alarm", return_value=False),
            patch.object(run_l1.time, "monotonic", return_value=300.0),
            patch.object(run_l1.signal, "signal"),
        ):
            self.assertFalse(deadline.restore_blocked())

    def test_finalization_hard_restore_overrides_an_ordinary_failure(self) -> None:
        deadline = Mock()
        deadline.restore_blocked.return_value = True
        stderr = io.StringIO()
        with (
            patch.object(run_l1, "_acquire_execution_lock", return_value=1234),
            patch.object(run_l1, "_checkout_guard"),
            patch.object(run_l1, "_validate_completion_receipt"),
            patch.object(run_l1, "_begin_finalization_attempt"),
            patch.object(run_l1, "FinalizationDeadline", return_value=deadline),
            patch.object(run_l1, "_finalize_locked", side_effect=ValueError("invalid")),
            patch.object(run_l1.signal, "pthread_sigmask", return_value=set()),
            patch.object(run_l1.os, "close") as close,
            redirect_stderr(stderr),
        ):
            self.assertEqual(
                run_l1.finalize(
                    "20260101T000000Z-deadbeef",
                    Path("/tmp/attestation.json"),
                    "a" * 40,
                ),
                2,
            )
        self.assertEqual(json.loads(stderr.getvalue())["status"], "Inconclusive")
        close.assert_called_once_with(1234)

    def test_existing_settlement_cannot_bypass_human_attestation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence, _result, state = self._pending_generation(Path(temporary))
            attestation = {
                "active_minutes": 1,
                "approved_boundary_exceptions": [],
                "decision": "Affirmative",
                "findings": [],
                "reviewed_candidate_identity_sha256": state[
                    "final_candidate_identity_sha256"
                ],
                "reviewed_manifest_sha256": state["final_manifest_sha256"],
            }
            settlement = run_l1._settlement_value(
                evidence=evidence,
                run_id=state["run_id"],
                contract_commit=state["contract_commit"],
                pending_state=state,
                pending_valid=True,
                pending_detail=None,
                attestation=attestation,
                received_at="2026-01-01T00:02:00+00:00",
            )
            settlement["attestation"] = None
            with self.assertRaises(ValueError):
                run_l1._validate_settlement(
                    settlement,
                    evidence=evidence,
                    run_id=state["run_id"],
                    contract_commit=state["contract_commit"],
                )

    def test_pending_evidence_loss_can_close_inconclusive_without_rewriting_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence, result, state = self._pending_generation(root)
            (evidence / "run.json").write_text("{\"changed\":true}\n", encoding="utf-8")
            settlement = run_l1._settlement_value(
                evidence=evidence,
                run_id=state["run_id"],
                contract_commit=state["contract_commit"],
                pending_state=run_l1._minimal_invalid_pending_state(
                    state["run_id"],
                    state["contract_commit"],
                    "2026-01-01T00:02:00+00:00",
                ),
                pending_valid=False,
                pending_detail=run_l1.PENDING_INTEGRITY_FAILURE_DETAIL,
                attestation=None,
                received_at="2026-01-01T00:02:00+00:00",
            )
            with patch.object(run_l1, "RESULT_PATH", result):
                self._write_finalization_marker(evidence, state)
                run_l1._atomic_write_new(
                    evidence / "settlement.json",
                    (json.dumps(settlement, indent=2, sort_keys=True) + "\n").encode(),
                )
                run_l1._close_terminal_evidence(evidence, settlement)
                run_l1._write_completion_receipt(
                    evidence,
                    kind="finalization",
                    run_id=state["run_id"],
                    contract_commit=state["contract_commit"],
                )
                observed = run_l1._verify_terminal_index(
                    evidence,
                    run_id=state["run_id"],
                    contract_commit=state["contract_commit"],
                )
            self.assertEqual(observed["status"], "Inconclusive")
            self.assertEqual((evidence / "run.json").read_text(encoding="utf-8"), '{"changed":true}\n')

    def test_corrupt_pending_status_can_still_settle_inconclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence, result, state = self._pending_generation(root)
            run_evidence = root / state["run_id"]
            evidence.rename(run_evidence)
            damaged = run_l1._read_json(run_evidence / "run.json")
            damaged["status"] = "PendingHumanReviex"
            run_l1._write_json(run_evidence / "run.json", damaged)
            attestation = root / "attestation.json"
            attestation.write_text("{}\n", encoding="utf-8")
            with (
                patch.object(run_l1, "EVIDENCE_ROOT", root),
                patch.object(run_l1, "RESULT_PATH", result),
                patch.object(run_l1, "_checkout_guard"),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(
                    run_l1.finalize(
                        state["run_id"],
                        attestation,
                        state["contract_commit"],
                    ),
                    0,
                )
            settlement = run_l1._read_json(run_evidence / "settlement.json")
            self.assertEqual(settlement["status"], "Inconclusive")
            self.assertEqual(settlement["pending_evidence"]["verification"], "invalid")

    def test_verified_automatic_terminal_generation_cannot_be_human_settled(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence, result, state = self._pending_generation(root)
            state.pop("review_requested_at")
            state["status"] = "Rejected"
            state["disposition_reason"] = "The final non-human gate failed."
            (evidence / run_l1.EXECUTION_COMPLETION_NAME).unlink()
            run_l1._write_json(evidence / "run.json", state)
            rendered = run_l1._render_result(state)
            (evidence / "pending-RESULT.md").write_text(rendered, encoding="utf-8")
            result.write_text(rendered, encoding="utf-8")
            run_l1._write_json(
                evidence / "evidence-index.json",
                run_l1._evidence_index(evidence),
            )
            run_l1._write_completion_receipt(
                evidence,
                kind="execution",
                run_id=state["run_id"],
                contract_commit=state["contract_commit"],
            )
            with patch.object(run_l1, "RESULT_PATH", result):
                self.assertTrue(
                    run_l1._verified_automatic_terminal_generation(
                        evidence,
                        state["run_id"],
                        state["contract_commit"],
                        state,
                    )
                )
            run_evidence = root / state["run_id"]
            evidence.rename(run_evidence)
            before = {
                path.relative_to(run_evidence).as_posix(): path.read_bytes()
                for path in run_evidence.rglob("*")
                if path.is_file()
            }
            attestation = root / "attestation.json"
            attestation.write_text("{}\n", encoding="utf-8")
            with (
                patch.object(run_l1, "EVIDENCE_ROOT", root),
                patch.object(run_l1, "RESULT_PATH", result),
                patch.object(run_l1, "_checkout_guard"),
                self.assertRaises(ValueError),
            ):
                run_l1.finalize(
                    state["run_id"],
                    attestation,
                    state["contract_commit"],
                )
            self.assertFalse((run_evidence / "settlement.json").exists())
            self.assertFalse(
                (run_evidence / run_l1.FINALIZATION_ATTEMPT_NAME).exists()
            )
            self.assertEqual(
                before,
                {
                    path.relative_to(run_evidence).as_posix(): path.read_bytes()
                    for path in run_evidence.rglob("*")
                    if path.is_file()
                },
            )

    def test_identity_bearing_host_path_is_redacted_and_forces_inconclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence = root / "evidence"
            source = evidence / "candidate" / "attempt-1" / "source" / "service.py"
            source.parent.mkdir(parents=True)
            source.write_text(f"HOST_PATH = {str(ROOT)!r}\n", encoding="utf-8")
            result = root / "RESULT.md"
            result.write_text("# result\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                run_l1._assert_public_safe_terminal(evidence, result)
            records = run_l1._public_safety_redact(evidence, result, ())
            self.assertTrue(run_l1._redactions_require_inconclusive(records))
            self.assertEqual(
                run_l1._redaction_inconclusive_reason(records),
                "public-safety redaction changed identity-bearing evidence",
            )
            self.assertNotIn(str(ROOT), source.read_text(encoding="utf-8"))
            self.assertIn("[HOST_REPOSITORY]", source.read_text(encoding="utf-8"))
            run_l1._assert_public_safe_terminal(evidence, result)

    def test_masked_openai_fingerprint_is_redacted_before_stream_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary) / "evidence"
            evidence.mkdir()
            recorder = run_l1.Recorder(evidence)
            fingerprint = "sk-proj-" + ("*" * 116) + "Ab1-"

            sanitized = recorder._sanitize(
                f'{{"error":"{fingerprint}"}}\n',
                sequence=1,
                stream="stdout",
            )

            self.assertNotIn(fingerprint, sanitized)
            self.assertIn("[REDACTED:OPENAI_KEY_FINGERPRINT]", sanitized)
            self.assertEqual(
                recorder.redactions,
                [
                    {
                        "count": 1,
                        "item": "OPENAI_KEY_FINGERPRINT",
                        "sequence": 1,
                        "stream": "stdout",
                    }
                ],
            )

    def test_terminal_masked_fingerprint_escape_fails_closed_before_indexing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence = root / "evidence"
            events = evidence / "agent" / "attempt-1" / "events.jsonl"
            events.parent.mkdir(parents=True)
            fingerprint = b"sk-proj-" + (b"*" * 116) + b"Ab1_"
            events.write_bytes(b'{"error":"' + fingerprint + b'"}\n')
            result = root / "RESULT.md"
            result.write_text("# result\n", encoding="utf-8")

            with self.assertRaises(ValueError):
                run_l1._assert_public_safe_terminal(evidence, result)
            records = run_l1._public_safety_redact(evidence, result, ())
            self.assertEqual(
                records,
                [
                    {
                        "count": 1,
                        "item": "OPENAI_KEY_FINGERPRINT",
                        "path": "agent/attempt-1/events.jsonl",
                        "reason": "credential-shaped bytes are not public-safe evidence",
                    }
                ],
            )
            sanitized = events.read_bytes()
            self.assertNotIn(fingerprint, sanitized)
            self.assertIn(b"[REDACTED:OPENAI_KEY_FINGERPRINT]", sanitized)
            self.assertTrue(run_l1._redactions_require_inconclusive(records))
            self.assertEqual(
                run_l1._redaction_inconclusive_reason(records),
                "public-safety redaction changed identity-bearing evidence",
            )
            run_l1._assert_public_safe_terminal(evidence, result)
            index = run_l1._evidence_index(evidence)
            record = next(
                item
                for item in index["files"]
                if item["path"] == "agent/attempt-1/events.jsonl"
            )
            self.assertEqual(record["sha256"], run_l1._sha256(events))
            self.assertEqual(record["size"], events.stat().st_size)

    def test_masked_openai_fingerprint_pattern_is_narrow(self) -> None:
        for suffix in (b"Ab1-", b"Ab1_", b"Ab12"):
            with self.subTest(suffix=suffix):
                valid = b"sk-svcacct-" + (b"*" * 20) + suffix
                self.assertEqual(
                    run_l1._public_safety_labels(valid, check_host_paths=False),
                    {"OPENAI_KEY_FINGERPRINT"},
                )
        for value in (
            b"sk-proj-" + (b"*" * 19) + b"Ab1_",
            b"pk-proj-" + (b"*" * 20) + b"Ab1_",
            b"sk-proj-" + (b"*" * 20) + b"Ab1",
            b"xsk-proj-" + (b"*" * 20) + b"Ab12",
            b"sk-proj-" + (b"*" * 20) + b"Ab12-",
            b"sk-proj-" + (b"*" * 20) + b"Ab12_",
            b"sk-proj-" + (b"*" * 20) + b"Ab1_x",
            b"[REDACTED:OPENAI_KEY_FINGERPRINT]",
        ):
            with self.subTest(value=value):
                self.assertEqual(
                    run_l1._public_safety_labels(value, check_host_paths=False),
                    set(),
                )

    def test_mode_zero_evidence_is_scanned_and_indexed_without_mode_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence = root / "evidence"
            evidence.mkdir()
            opaque = evidence / "candidate" / "attempt-1" / "source" / "opaque"
            opaque.parent.mkdir(parents=True)
            opaque.write_bytes(b"\x00\xffpublic-safe")
            opaque.chmod(0)
            result = root / "RESULT.md"
            result.write_text("# result\n", encoding="utf-8")
            with patch.object(run_l1, "RESULT_PATH", result):
                self.assertEqual(run_l1._public_safety_redact(evidence, result, ()), [])
                index = run_l1._evidence_index(evidence)
            self.assertEqual(opaque.stat().st_mode & 0o7777, 0)
            self.assertIn(
                "candidate/attempt-1/source/opaque",
                {record["path"] for record in index["files"]},
            )

    def test_candidate_manifest_public_safety_read_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, patch.object(
            run_l1,
            "TRANSFER_MANIFEST_MAX_BYTES",
            32,
        ):
            manifest = Path(temporary) / "manifest.json"
            manifest.write_bytes(b" " * 33)
            with self.assertRaises(run_l1.Inconclusive):
                run_l1._assert_public_safe_candidate_manifest(manifest)

    def test_elapsed_execution_deadline_stops_before_closure_writes(self) -> None:
        recorder = Mock()
        writer = Mock()
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.object(run_l1.time, "monotonic", return_value=10.0),
            patch.object(run_l1, "_write_json", writer),
            self.assertRaises(run_l1.ExecuteHardDeadline),
        ):
            run_l1._write_run_outputs(
                Path(temporary),
                {
                    "run_started_at": "2026-01-01T00:00:00+00:00",
                    "status": "PendingHumanReview",
                },
                recorder=recorder,
                final_phase_deadline=10.0,
                automated_phase_deadline=20.0,
            )
        writer.assert_not_called()

    def test_finalization_completion_barrier_rejects_pending_or_elapsed_deadline(
        self,
    ) -> None:
        cases = ((True, 100.0), (False, 200.0))
        for pending, now in cases:
            with self.subTest(pending=pending, now=now):
                deadline = run_l1.FinalizationDeadline()
                deadline._installed = True
                deadline.deadline = 200.0
                with (
                    patch.object(run_l1.signal, "pthread_sigmask", return_value=set()),
                    patch.object(run_l1.signal, "setitimer"),
                    patch.object(deadline, "_drain_pending_alarm", return_value=pending),
                    patch.object(run_l1.time, "monotonic", return_value=now),
                    self.assertRaises(run_l1.FinalizationHardDeadline),
                ):
                    deadline.complete()
                self.assertTrue(deadline.hard_observed)

    def test_finalization_alarm_after_normal_return_requires_human_recovery(self) -> None:
        deadline = Mock()
        deadline.complete.side_effect = run_l1.FinalizationHardDeadline()
        deadline.restore_blocked.return_value = False
        stderr = io.StringIO()
        with (
            patch.object(run_l1, "_acquire_execution_lock", return_value=1234),
            patch.object(run_l1, "_checkout_guard"),
            patch.object(run_l1, "_validate_completion_receipt"),
            patch.object(run_l1, "_begin_finalization_attempt"),
            patch.object(run_l1, "FinalizationDeadline", return_value=deadline),
            patch.object(run_l1, "_finalize_locked", return_value="Accepted"),
            patch.object(run_l1, "_write_completion_receipt") as receipt,
            patch.object(run_l1.signal, "pthread_sigmask", return_value=set()),
            patch.object(run_l1.os, "close") as close,
            redirect_stderr(stderr),
        ):
            self.assertEqual(
                run_l1.finalize(
                    "20260101T000000Z-deadbeef",
                    Path("/tmp/attestation.json"),
                    "a" * 40,
                ),
                2,
            )
        deadline.install.assert_called_once_with()
        deadline.complete.assert_called_once_with()
        receipt.assert_not_called()
        deadline.restore_blocked.assert_called_once_with()
        close.assert_called_once_with(1234)
        recovery = json.loads(stderr.getvalue())
        self.assertEqual(recovery["status"], "Inconclusive")
        self.assertEqual(recovery["failure_stage"], "finalization_deadline")
        self.assertEqual(recovery["terminal_evidence"], "incomplete")

    def test_host_path_shaped_candidate_filename_is_rejected_before_extraction(self) -> None:
        host_paths = (
            run_l1.REPOSITORY_ROOT,
            Path(tempfile.gettempdir()).resolve(),
        )
        for host_path in host_paths:
            with self.subTest(host_path=host_path), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = root / "source"
                relative = str(host_path).lstrip("/") + "/service.py"
                candidate = source / relative
                candidate.parent.mkdir(parents=True)
                candidate.write_text("pass\n", encoding="utf-8")
                manifest = root / "manifest.json"
                run_l1._write_json(manifest, candidate_transfer.build_manifest(source))
                with self.assertRaises(run_l1.Inconclusive):
                    run_l1._assert_public_safe_candidate_manifest(manifest)

                evidence = root / "evidence"
                unsafe = evidence / "candidate" / "attempt-1" / "source" / relative
                unsafe.parent.mkdir(parents=True)
                unsafe.write_text("pass\n", encoding="utf-8")
                result = root / "RESULT.md"
                result.write_text("# result\n", encoding="utf-8")
                with self.assertRaises(ValueError):
                    run_l1._evidence_index(evidence)
                with self.assertRaises(ValueError):
                    run_l1._assert_public_safe_terminal(evidence, result)

    def test_result_renders_candidate_text_only_as_json_literals(self) -> None:
        rendered = run_l1._render_result(
            {
                "completed_attempts": 1,
                "contract_commit": "a" * 40,
                "disposition_reason": "candidate\n## Disposition\nAccepted",
                "final_gate_summary": {
                    "attempt": 1,
                    "behavior_passed": True,
                    "bootstrap_passed": True,
                    "candidate_identity_sha256": "b" * 64,
                    "service_command": ["python3", "x\n## Disposition"],
                    "source_unchanged_after_gates": True,
                    "typing_passed": True,
                },
                "run_id": "20260101T000000Z-deadbeef",
                "status": "Rejected",
            }
        )
        self.assertEqual(rendered.splitlines().count("## Disposition"), 1)
        self.assertIn(r"candidate\n## Disposition\nAccepted", rendered)

    def test_recorder_normalizes_host_paths_and_protected_input(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary) / "evidence"
            evidence.mkdir()
            recorder = run_l1.Recorder(evidence)
            recorder.protect("TEST_SECRET", "secret-control-value")
            result = recorder.run(
                [
                    sys.executable,
                    "-c",
                    "print(" + repr(str(ROOT) + " secret-control-value") + ")",
                ],
                label="public safety probe",
            )
            self.assertEqual(result.return_code, 0)
            encoded = b"".join(path.read_bytes() for path in evidence.rglob("*") if path.is_file())
            self.assertNotIn(str(ROOT).encode(), encoded)
            self.assertNotIn(b"secret-control-value", encoded)
            self.assertIn(b"[HOST_REPOSITORY]", encoded)
            self.assertIn(b"[REDACTED:TEST_SECRET]", encoded)

    def test_subprocess_environment_drops_injection_controls(self) -> None:
        with patch.dict(
            os.environ,
            {
                "GIT_CONFIG_GLOBAL": "/attacker/gitconfig",
                "OPENAI_API_KEY": "secret-control-value",
                "PATH": "/attacker/bin",
                "PYTHONPATH": "/attacker/python",
            },
            clear=False,
        ):
            environment = run_l1._safe_environment()
        self.assertNotIn("OPENAI_API_KEY", environment)
        self.assertNotIn("PYTHONPATH", environment)
        self.assertNotIn("/attacker", json.dumps(environment))
        self.assertEqual(environment["GIT_CONFIG_GLOBAL"], "/dev/null")

    def test_child_does_not_inherit_the_alarm_handoff_mask(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary) / "evidence"
            evidence.mkdir()
            result = run_l1.Recorder(evidence).run(
                [
                    sys.executable,
                    "-c",
                    (
                        "import signal;"
                        "print(int(signal.SIGALRM in "
                        "signal.pthread_sigmask(signal.SIG_BLOCK,set())))"
                    ),
                ],
                label="child alarm mask probe",
            )
            self.assertEqual(result.return_code, 0)
            self.assertEqual((evidence / result.stdout_path).read_text(), "0\n")

    def test_lima_list_filter_records_names_only(self) -> None:
        raw = json.dumps(
            {
                "name": "q1-l1-evaluator",
                "sshAddress": "/Users/private/.lima/q1-l1-evaluator/sock",
                "sshLocalPort": 54321,
                "pid": 1234,
            }
        )
        self.assertEqual(run_l1._allowlisted_lima_names(raw), '{"name": "q1-l1-evaluator"}\n')

    def test_created_candidate_lima_runtime_is_bound_to_reviewed_authority(self) -> None:
        instance = "q1-l1-candidate-20260101t000000z-deadbeef"
        image = {
            "arch": "aarch64",
            "digest": "sha256:" + "a" * 64,
            "location": "https://example.invalid/candidate.img",
        }
        config = {
            "arch": "aarch64",
            "audio": {"device": ""},
            "caCerts": {"removeDefaults": False},
            "containerd": {
                "archives": list(run_l1.CANDIDATE_CONTAINERD_ARCHIVES),
                "system": False,
                "user": False,
            },
            "cpus": 4,
            "disk": "40GiB",
            "firmware": {"legacyBIOS": False},
            "guestInstallPrefix": "/usr/local",
            "hostResolver": {"enabled": True, "ipv6": False},
            "images": [image],
            "memory": "8GiB",
            "minimumLimaVersion": "2.1.4",
            "mountInotify": False,
            "mountType": "virtiofs",
            "nestedVirtualization": False,
            "os": "Linux",
            "plain": False,
            "propagateProxyEnv": False,
            "ssh": {
                "forwardAgent": False,
                "forwardX11": False,
                "forwardX11Trusted": False,
                "loadDotSSHPubKeys": False,
                "localPort": 0,
                "overVsock": True,
            },
            "timezone": "America/Denver",
            "upgradePackages": False,
            "user": run_l1._expected_lima_user(),
            "video": {"display": "none"},
            "vmOpts": {
                "vz": {
                    "diskImageFormat": "raw",
                    "rosetta": {"binfmt": False, "enabled": False},
                },
            },
            "vmType": "vz",
        }
        self.assertEqual(set(config), run_l1.CANDIDATE_LIMA_CONFIG_FIELDS)
        instance_root = run_l1.HOST_HOME / ".lima" / instance
        record = {
            "HostArch": "aarch64",
            "HostOS": "darwin",
            "IdentityFile": str(run_l1.HOST_HOME / ".lima" / "_config" / "user"),
            "LimaHome": str(run_l1.HOST_HOME / ".lima"),
            "arch": "aarch64",
            "config": config,
            "cpus": 4,
            "dir": str(instance_root),
            "disk": 40 * 1024**3,
            "driverPID": 1234,
            "errors": [],
            "hostAgentPID": 1234,
            "hostname": f"lima-{instance}",
            "limaVersion": "2.1.4",
            "memory": 8 * 1024**3,
            "name": instance,
            "protected": False,
            "sshAddress": "127.0.0.1",
            "sshConfigFile": str(instance_root / "ssh.config"),
            "sshLocalPort": 61234,
            "status": "Running",
            "vmType": "vz",
        }
        authority = {
            "configured_image_digest": image["digest"],
            "configured_image_location": image["location"],
            "configured_mounts": [],
        }
        observed = json.loads(
            run_l1._normalized_candidate_lima(json.dumps(record), instance, authority)
        )
        self.assertEqual(observed["base_image"]["digest"], image["digest"])
        self.assertEqual(observed["config"]["mounts"], [])
        self.assertEqual(observed["config"]["parameters"], {})
        self.assertEqual(observed["config"]["port_forwards"], [])
        self.assertEqual(set(observed["config"]["vm_options"]), {"vz"})
        without_errors = json.loads(json.dumps(record))
        del without_errors["errors"]
        run_l1._normalized_candidate_lima(
            json.dumps(without_errors),
            instance,
            authority,
        )
        with_errors = json.loads(json.dumps(record))
        with_errors["errors"] = ["failed"]
        with self.assertRaises(ValueError):
            run_l1._normalized_candidate_lima(
                json.dumps(with_errors),
                instance,
                authority,
            )
        for field in sorted(run_l1.CANDIDATE_LIMA_CONFIG_FIELDS):
            with self.subTest(field=field):
                drifted = json.loads(json.dumps(record))
                drifted["config"][field] = {"unexpected": True}
                with self.assertRaises(ValueError):
                    run_l1._normalized_candidate_lima(
                        json.dumps(drifted),
                        instance,
                        authority,
                    )
        extra = json.loads(json.dumps(record))
        extra["config"]["futureBoundary"] = True
        with self.assertRaises(ValueError):
            run_l1._normalized_candidate_lima(json.dumps(extra), instance, authority)
        for omitted_field in ("mounts", "param"):
            with self.subTest(omitted_field=omitted_field):
                invented = json.loads(json.dumps(record))
                invented["config"][omitted_field] = [] if omitted_field == "mounts" else {}
                with self.assertRaises(ValueError):
                    run_l1._normalized_candidate_lima(
                        json.dumps(invented),
                        instance,
                        authority,
                    )
        invented_instance_parameter = json.loads(json.dumps(record))
        invented_instance_parameter["param"] = {"internal_netplanOptional": "true"}
        with self.assertRaises(ValueError):
            run_l1._normalized_candidate_lima(
                json.dumps(invented_instance_parameter),
                instance,
                authority,
            )
        invented_inactive_backend = json.loads(json.dumps(record))
        invented_inactive_backend["config"]["vmOpts"]["qemu"] = {
            "cpuType": None,
            "minimumVersion": None,
        }
        with self.assertRaises(ValueError):
            run_l1._normalized_candidate_lima(
                json.dumps(invented_inactive_backend),
                instance,
                authority,
            )
        stopped = json.loads(json.dumps(record))
        stopped["status"] = "Stopped"
        with self.assertRaises(ValueError):
            run_l1._normalized_candidate_lima(json.dumps(stopped), instance, authority)
        extra_instance = json.loads(json.dumps(record))
        extra_instance["futureBoundary"] = True
        with self.assertRaises(ValueError):
            run_l1._normalized_candidate_lima(
                json.dumps(extra_instance),
                instance,
                authority,
            )

    def test_candidate_teardown_attempts_logout_and_delete_after_inspection_failure(self) -> None:
        recorder = Mock()
        recorder.run.return_value = Mock(return_code=0)
        with patch.object(
            run_l1,
            "_listed_instances",
            side_effect=[(None, "inspection failed"), (set(), None)],
        ):
            failures = run_l1._cleanup_candidate(
                recorder,
                "q1-l1-candidate-20260101t000000z-deadbeef",
                True,
            )
        self.assertEqual(failures, ["inspection failed"])
        labels = [call.kwargs["label"] for call in recorder.run.call_args_list]
        self.assertEqual(
            labels,
            ["remove candidate Codex authentication", "delete candidate VM"],
        )

    def test_candidate_teardown_records_only_a_verified_present_lower_bound(self) -> None:
        instance = "q1-l1-candidate-20260101t000000z-deadbeef"
        recorder = Mock()
        recorder.run.return_value = Mock(return_code=0, limit_breach=None)
        verification: dict[str, bool | float] = {}
        with (
            patch.object(
                run_l1,
                "_listed_instances",
                side_effect=[({instance}, None), (set(), None)],
            ),
            patch.object(run_l1.time, "monotonic", return_value=42.0),
        ):
            self.assertEqual(
                run_l1._cleanup_candidate(
                    recorder,
                    instance,
                    False,
                    cleanup_deadline_monotonic=1_000.0,
                    verification=verification,
                ),
                [],
            )
        self.assertEqual(verification["last_verified_present_monotonic"], 42.0)
        self.assertTrue(verification["absent"])

    def test_outer_typing_timeout_is_infrastructure_not_candidate_failure(self) -> None:
        recorder = Mock()
        recorder.run.return_value = Mock(sequence=7, timed_out=True, return_code=124)
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary)
            with self.assertRaises(run_l1.Inconclusive):
                run_l1._typing_gate(
                    recorder,
                    evidence,
                    "/tmp/candidate",
                    "20260101T000000Z-deadbeef",
                    1,
                )
            report = json.loads(
                (evidence / "gates" / "attempt-1" / "typing.json").read_text(
                    encoding="utf-8"
                )
            )
        self.assertTrue(report["infrastructure_failure"])
        self.assertFalse(report["passed"])

    def test_outer_typing_stream_breach_overrides_candidate_exit(self) -> None:
        recorder = Mock()
        recorder.run.return_value = Mock(
            sequence=7,
            timed_out=False,
            return_code=1,
            limit_breach="stdout_size",
        )
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary)
            with self.assertRaisesRegex(run_l1.Inconclusive, "stdout_size"):
                run_l1._typing_gate(
                    recorder,
                    evidence,
                    "/tmp/candidate",
                    "20260101T000000Z-deadbeef",
                    1,
                )
            report = json.loads(
                (evidence / "gates" / "attempt-1" / "typing.json").read_text(
                    encoding="utf-8"
                )
            )
        self.assertTrue(report["infrastructure_failure"])
        self.assertEqual(report["limit_breach"], "stdout_size")

    def test_typing_candidate_failure_requires_trusted_wrapper_completion(self) -> None:
        recorder = Mock()
        recorder.run.return_value = Mock(
            sequence=7,
            timed_out=False,
            return_code=1,
            limit_breach=None,
            stderr_path="logs/typing.stderr",
        )
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary)
            (evidence / "logs").mkdir()
            stderr = evidence / "logs" / "typing.stderr"
            stderr.write_text("mypy failed\n", encoding="utf-8")
            with self.assertRaisesRegex(run_l1.Inconclusive, "completion marker"):
                run_l1._typing_gate(
                    recorder,
                    evidence,
                    "/tmp/candidate",
                    "20260101T000000Z-deadbeef",
                    1,
                )
            stderr.write_text(
                "mypy failed\n" + run_l1.ISOLATED_COMMAND_COMPLETION_MARKER + "\n",
                encoding="utf-8",
            )
            report = run_l1._typing_gate(
                recorder,
                evidence,
                "/tmp/candidate",
                "20260101T000000Z-deadbeef",
                1,
            )
        self.assertFalse(report["infrastructure_failure"])
        self.assertFalse(report["passed"])
        self.assertTrue(report["wrapper_completed"])

    def test_behavioral_candidate_failure_requires_the_full_trusted_schema(self) -> None:
        command = ["python3", "service.py"]
        report = {
            "base_url": "http://127.0.0.1:18766",
            "candidate_service_command": command,
            "contract_version": "1.0.0",
            "duration_ms": 10,
            "evaluator_version": "0.1.0",
            "failure_class": "candidate_failure",
            "infrastructure_failure": False,
            "layers": {},
            "limits": {
                "request_timeout_seconds": 3.0,
                "shutdown_timeout_seconds": 1.5,
                "startup_timeout_seconds": 8.0,
                "suite_timeout_seconds": 45.0,
            },
            "passed": False,
            "service_command": "trusted isolation wrapper",
            "service_log_tail": "",
            "shutdowns": [],
            "started_at": "2026-01-01T00:00:00+00:00",
            "startup_error": "candidate executable was missing",
            "startup_failure_origin": "candidate",
            "startup_return_code": 127,
            "tests": [],
        }
        self.assertEqual(
            run_l1._validated_behavior_report(
                report,
                expected_candidate_command=command,
            ),
            report,
        )
        with self.assertRaises(ValueError):
            run_l1._validated_behavior_report(
                {"passed": False},
                expected_candidate_command=command,
            )
        with self.assertRaises(ValueError):
            run_l1._validated_behavior_report(
                {**report, "failure_class": None},
                expected_candidate_command=command,
            )

    def test_required_evidence_includes_every_evaluated_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary)
            required = {
                path.relative_to(evidence).as_posix()
                for path in run_l1._required_evidence(
                    evidence,
                    {
                        "agent_attempts_invoked": 2,
                        "behavior_attempts": [1, 2],
                        "bootstrap_attempts": [1, 2],
                        "candidate_boundary_validated": True,
                        "completed_attempts": 2,
                        "evaluated_attempts": [1, 2],
                        "identified_attempts": [1, 2],
                        "transferred_attempts": [1, 2],
                        "transfer_attempts_started": [1, 2],
                        "typing_attempts": [1, 2],
                    },
                )
            }
            self.assertIn("gates/attempt-1/summary.json", required)
            self.assertIn("gates/attempt-2/summary.json", required)
            self.assertIn("agent/attempt-2/feedback.json", required)
            self.assertIn("boundary-validation.json", required)
            self.assertIn("candidate/attempt-1/transfer-status.json", required)
            self.assertIn("authorities/QUESTION.md", required)
            self.assertIn(
                f"setup/{run_l1.API_AUTHENTICATION_REPORT}",
                required,
            )

    def test_all_copied_run_authorities_are_public_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence_root = Path(temporary) / "evidence"
            evidence = evidence_root / "20260101T000000Z-deadbeef"
            evidence.mkdir(parents=True)
            with patch.object(run_l1, "EVIDENCE_ROOT", evidence_root):
                run_l1._copy_run_authorities(evidence)
            unsafe = {
                path.relative_to(evidence).as_posix(): sorted(
                    run_l1._public_safety_labels(
                        path.read_bytes(),
                        check_host_paths=True,
                    )
                )
                for path in evidence.rglob("*")
                if path.is_file()
                and run_l1._public_safety_labels(
                    path.read_bytes(),
                    check_host_paths=True,
                )
            }
        self.assertEqual(unsafe, {})

    def test_validated_evaluator_requires_fingerprint_and_residue_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary)
            required = {
                path.relative_to(evidence).as_posix()
                for path in run_l1._required_evidence(
                    evidence,
                    {"agent_attempts_invoked": 0, "evaluator_validated": True},
                )
            }
        self.assertTrue(
            {
                "evaluator-boundary-validation.json",
                "evaluator-environment.json",
                "evaluator-residue-validation.json",
            }.issubset(required)
        )

    def test_accounting_keeps_resources_separate_and_candidate_right_censored(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary)
            (evidence / "commands.jsonl").write_text(
                "\n".join(
                    json.dumps(record)
                    for record in (
                        {"duration_seconds": 2.0, "resources": ["trusted_machine"]},
                        {
                            "duration_seconds": 3.0,
                            "resources": ["evaluator", "trusted_machine"],
                        },
                    )
                )
                + "\n",
                encoding="utf-8",
            )
            accounting = run_l1._accounting(
                evidence,
                run_started_at="2026-01-01T00:00:00+00:00",
                finished_at="2026-01-01T00:00:10+00:00",
                review_requested_at="2026-01-01T00:00:06+00:00",
                review_received_at="2026-01-01T00:00:10+00:00",
                candidate_vm_provisioning_started_at="2026-01-01T00:00:02+00:00",
                candidate_vm_observed_existing_at="2026-01-01T00:00:03+00:00",
                candidate_vm_teardown_finished_at="2026-01-01T00:00:09+00:00",
                candidate_vm_teardown_verified=False,
                candidate_vm_observed_interval_lower_bound_seconds=4.0,
                execute_elapsed_lower_bound_seconds=9.5,
                finalization_elapsed_lower_bound_seconds=1.25,
            )
        self.assertEqual(accounting["trusted_machine"]["execute_recorded_active_seconds"], 5.0)
        self.assertEqual(
            accounting["trusted_machine"]["execute_elapsed_lower_bound_seconds"], 9.5
        )
        self.assertEqual(
            accounting["trusted_machine"]["finalization_elapsed_lower_bound_seconds"],
            1.25,
        )
        self.assertEqual(
            accounting["trusted_machine"]["artifact_self_recording_tail_seconds"],
            "unknown",
        )
        self.assertNotIn("total_recorded_active_seconds", accounting["trusted_machine"])
        self.assertNotIn("execute_process_elapsed_seconds", accounting["trusted_machine"])
        self.assertNotIn("finalization_active_seconds", accounting["trusted_machine"])
        self.assertEqual(accounting["evaluator"]["workload_seconds"], 3.0)
        self.assertEqual(accounting["candidate_vm"]["lifetime_seconds"], "unknown")
        self.assertEqual(
            accounting["candidate_vm"]["observed_interval_lower_bound_seconds"],
            4.0,
        )
        self.assertTrue(accounting["candidate_vm"]["right_censored"])
        self.assertTrue(accounting["overlap"]["nonexclusive"])
        self.assertEqual(accounting["human"]["review_wait_upper_bound_seconds"], 4.0)
        self.assertEqual(accounting["wall"]["elapsed_lower_bound_seconds"], 10.0)
        self.assertEqual(
            accounting["wall"]["recorded_cutoff_at"], "2026-01-01T00:00:10+00:00"
        )
        self.assertEqual(accounting["wall"]["post_cutoff_tail_seconds"], "unknown")

    def test_unavailable_cost_evidence_names_cache_write_gap(self) -> None:
        unavailable = run_l1._unavailable({"status": "Inconclusive"})
        self.assertIn(
            {
                "observation": "agent cache-write token usage",
                "reason": "pinned codex exec JSONL does not report cache-write tokens",
            },
            unavailable,
        )

    def test_unobserved_candidate_vm_never_claims_a_lifetime_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            accounting = run_l1._accounting(
                Path(temporary),
                run_started_at="2026-01-01T00:00:00+00:00",
                finished_at="2026-01-01T00:00:10+00:00",
                candidate_vm_provisioning_started_at="2026-01-01T00:00:02+00:00",
                candidate_vm_teardown_finished_at="2026-01-01T00:00:09+00:00",
                candidate_vm_teardown_verified=True,
            )
        self.assertEqual(accounting["candidate_vm"]["lifetime_seconds"], "unknown")
        self.assertEqual(
            accounting["candidate_vm"]["observed_interval_lower_bound_seconds"],
            "unknown",
        )
        self.assertEqual(accounting["candidate_vm"]["right_censored"], "unknown")

    def test_candidate_vm_timestamps_do_not_invent_an_observed_interval(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            accounting = run_l1._accounting(
                Path(temporary),
                run_started_at="2026-01-01T00:00:00+00:00",
                finished_at="2026-01-01T00:00:10+00:00",
                candidate_vm_observed_existing_at="2026-01-01T00:00:03+00:00",
                candidate_vm_teardown_finished_at="2026-01-01T00:00:09+00:00",
                candidate_vm_teardown_verified=True,
            )
        self.assertEqual(
            accounting["candidate_vm"]["observed_interval_lower_bound_seconds"],
            "unknown",
        )
        self.assertFalse(accounting["candidate_vm"]["right_censored"])

    def test_remote_hash_output_must_cover_exact_requested_paths(self) -> None:
        expected = ("/tmp/a", "/tmp/b")
        observed = run_l1._sha256sum_output(
            f"{'a' * 64}  /tmp/a\n{'b' * 64}  /tmp/b\n",
            expected,
        )
        self.assertEqual(observed, {"/tmp/a": "a" * 64, "/tmp/b": "b" * 64})
        with self.assertRaises(ValueError):
            run_l1._sha256sum_output(f"{'a' * 64}  /tmp/a\n", expected)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-report", type=Path)
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromModule(__import__(__name__))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    report = {
        "errors": len(result.errors),
        "failures": len(result.failures),
        "output": stream.getvalue(),
        "passed": result.wasSuccessful(),
        "tests_run": result.testsRun,
    }
    if args.json_report is not None:
        args.json_report.parent.mkdir(parents=True, exist_ok=True)
        args.json_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
