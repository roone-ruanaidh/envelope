"""Execute one approved loop over the frozen Q1 lease-service workload."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
import pwd
import re
import selectors
import signal
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Sequence, cast


@dataclass(frozen=True)
class WorkloadContext:
    workload_id: str
    authority_root: Path
    resource_namespace: str
    evaluator_instance: str
    model: str
    reasoning_effort: str
    codex_version: str


@dataclass(frozen=True)
class LoopContext:
    loop_id: str
    root: Path
    intervention: str
    launcher: Path | None = None
    prior_loop_id: str | None = None
    prior_run_id: str | None = None
    prior_result_commit: str | None = None
    candidate_qualification_root: Path | None = None


WORKLOAD = WorkloadContext(
    workload_id="q1-lease-service-v1",
    authority_root=Path(__file__).resolve().parents[1],
    resource_namespace="q1-l1",
    evaluator_instance="q1-l1-evaluator",
    model="gpt-5.6-luna",
    reasoning_effort="max",
    codex_version="codex-cli 0.144.6",
)
ROOT = WORKLOAD.authority_root
REPOSITORY_ROOT = ROOT.parents[2]
REPRODUCTION = ROOT / "reproduction"
QUESTION_PATH = ROOT.parent / "QUESTION.md"
if str(REPRODUCTION) not in sys.path:
    sys.path.insert(0, str(REPRODUCTION))

DEFAULT_LOOP = LoopContext(
    loop_id="Q1/L1",
    root=ROOT,
    intervention="baseline",
)
ACTIVE_LOOP = DEFAULT_LOOP
LOOP_ROOT = ACTIVE_LOOP.root
LOOP_PATH = LOOP_ROOT / "LOOP.md"
LOOP_AUTHORITY_PATHS: tuple[Path, ...] = ()
LOOP_CANDIDATE_QUALIFICATION_ROOT: Path | None = None
EVIDENCE_ROOT = LOOP_ROOT / "evidence"
RESULT_PATH = LOOP_ROOT / "RESULT.md"
HOST_HOME = Path(pwd.getpwuid(os.getuid()).pw_dir).resolve()
EVALUATOR_INSTANCE = WORKLOAD.evaluator_instance
EVALUATOR_RUN_DIRECTORY_MODE = 0o711
MODEL = WORKLOAD.model
REASONING_EFFORT = WORKLOAD.reasoning_effort
CODEX_VERSION = WORKLOAD.codex_version
AGENT_TIMEOUT_SECONDS = 30 * 60
AGENT_OUTER_TIMEOUT_SECONDS = 31 * 60
REMOTE_AGENT_TIMEOUT = "30m"
DEFAULT_COMMAND_TIMEOUT_SECONDS = 10 * 60
PROVISION_TIMEOUT_SECONDS = 30 * 60
CLEANUP_TIMEOUT_SECONDS = 5 * 60
FINALIZATION_TIMEOUT_SECONDS = 5 * 60
FINALIZATION_ATTEMPT_NAME = "finalization-attempt.json"
QUALIFICATION_REPORT_NAME = "qualification.json"
QUALIFICATION_INDEX_NAME = "qualification-evidence-index.json"
QUALIFICATION_COMPLETION_NAME = "qualification-completion.json"
EXECUTION_COMPLETION_NAME = "execution-completion.json"
FINALIZATION_COMPLETION_NAME = "finalization-completion.json"
AUTOMATED_PHASE_TIMEOUT_SECONDS = 3 * 60 * 60
COMMAND_STREAM_MAX_BYTES = 32 * 1024 * 1024
RETAINED_EVIDENCE_MAX_BYTES = 512 * 1024 * 1024
EVIDENCE_CLOSURE_RESERVE_BYTES = 64 * 1024 * 1024
CONTROL_DOCUMENT_MAX_BYTES = 1024 * 1024
TRANSFER_MANIFEST_MAX_BYTES = 8 * 1024 * 1024
ARGV_MAX_ENTRIES = 128
ARGV_MAX_ENTRY_BYTES = 8 * 1024
ARGV_MAX_AGGREGATE_BYTES = 64 * 1024
EXECUTION_LOCK_PATH = Path(tempfile.gettempdir()) / "q1-l1-execute.lock"
RUN_ID_PATTERN = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$")
INSTANCE_PATTERN = re.compile(
    r"^q1-l1-candidate-[0-9]{8}t[0-9]{6}z-[0-9a-f]{8}$"
)
EXPECTED_CANDIDATE_BOUNDARY = {
    "external_command_network": "blocked",
    "home_codex_control": "unreadable_and_unwritable",
    "host_workspace": "absent",
    "outside_workspace": "unreadable_and_unwritable",
    "privilege_escalation": "blocked",
    "protected_candidate_paths": "read_only",
    "workspace": "writable",
}
TOKEN_FIELDS = (
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
)
BEHAVIOR_TEST_LAYERS = (
    ("protocol_and_schema", "protocol"),
    ("sequential_transitions", "state_model"),
    ("idempotent_submission", "idempotency"),
    ("concurrent_idempotent_replay", "idempotency"),
    ("frozen_clock_and_ttl_boundary", "temporal"),
    ("renewal_from_current_time", "temporal"),
    ("stale_and_cross_job_authority", "authority"),
    ("concurrent_single_claim", "concurrency"),
    ("concurrent_expired_reclaim", "concurrency"),
    ("concurrent_multi_job_claims", "concurrency"),
    ("graceful_and_abrupt_persistence", "persistence"),
    ("bounded_cleanup", "cleanup"),
)
REDACTED_HOST_REPOSITORY = "[HOST_REPOSITORY]"
REDACTED_HOST_HOME = "[HOST_HOME]"
REDACTED_HOST_TEMP = "[HOST_TEMP]"
PUBLIC_SECRET_PATTERNS = (
    (
        "PRIVATE_KEY",
        re.compile(
            rb"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
            re.DOTALL,
        ),
    ),
    ("OPENAI_KEY_PATTERN", re.compile(rb"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}\b")),
    (
        "BEARER_TOKEN",
        re.compile(rb"(?i:authorization\s*:\s*bearer\s+)[A-Za-z0-9._~+/=-]{12,}"),
    ),
)
HUMAN_REVIEW_CLAUSES = frozenset({"1", "2", "3", "4"})
ISOLATED_COMMAND_COMPLETION_MARKER = "q1-l1-isolated-command-completed-v1"


def configure_loop(context: LoopContext) -> None:
    """Select one Q1 loop without changing the frozen workload identity."""

    match = re.fullmatch(r"Q1/L([1-9][0-9]*)", context.loop_id)
    root = context.root.resolve()
    if match is None or root.parent != ROOT.parent:
        raise ValueError("loop context must identify a direct Q1 loop directory")
    if not root.name.startswith(f"l{match.group(1)}-"):
        raise ValueError("loop ID and directory name disagree")
    if not context.intervention or re.fullmatch(
        r"[a-z0-9]+(?:_[a-z0-9]+)*", context.intervention
    ) is None:
        raise ValueError("loop intervention must be a lowercase identifier")
    if root != ROOT and context.launcher is None:
        raise ValueError("a derived loop requires its reviewed launcher")
    launcher_paths: tuple[Path, ...] = ()
    if context.launcher is not None:
        launcher = context.launcher.resolve()
        expected = root / "reproduction" / f"run_l{match.group(1)}.py"
        if launcher != expected:
            raise ValueError("loop launcher does not match the selected loop")
        launcher_paths = (launcher,)
    provenance = (
        context.prior_loop_id,
        context.prior_run_id,
        context.prior_result_commit,
    )
    if any(value is None for value in provenance) != all(
        value is None for value in provenance
    ):
        raise ValueError("prior-loop provenance must be complete or absent")
    if context.prior_loop_id is not None:
        if re.fullmatch(r"Q1/L[1-9][0-9]*", context.prior_loop_id) is None:
            raise ValueError("prior loop ID is invalid")
        if RUN_ID_PATTERN.fullmatch(cast(str, context.prior_run_id)) is None:
            raise ValueError("prior run ID is invalid")
        _validate_contract_commit(cast(str, context.prior_result_commit))

    qualification_root: Path | None = None
    if context.candidate_qualification_root is not None:
        qualification_root = context.candidate_qualification_root.absolute()
        expected_qualification_root = (
            root / "build" / "candidate-boundary-qualification"
        ).absolute()
        if qualification_root != expected_qualification_root:
            raise ValueError("candidate qualification root is not owned by the loop")

    global ACTIVE_LOOP, LOOP_ROOT, LOOP_PATH, LOOP_AUTHORITY_PATHS
    global LOOP_CANDIDATE_QUALIFICATION_ROOT
    global EVIDENCE_ROOT, RESULT_PATH
    ACTIVE_LOOP = LoopContext(
        loop_id=context.loop_id,
        root=root,
        intervention=context.intervention,
        launcher=launcher_paths[0] if launcher_paths else None,
        prior_loop_id=context.prior_loop_id,
        prior_run_id=context.prior_run_id,
        prior_result_commit=context.prior_result_commit,
        candidate_qualification_root=qualification_root,
    )
    LOOP_ROOT = root
    LOOP_PATH = root / "LOOP.md"
    LOOP_AUTHORITY_PATHS = launcher_paths
    LOOP_CANDIDATE_QUALIFICATION_ROOT = qualification_root
    EVIDENCE_ROOT = root / "evidence"
    RESULT_PATH = root / "RESULT.md"


def _run_context_record() -> dict[str, Any]:
    record: dict[str, Any] = {
        "loop": {
            "id": ACTIVE_LOOP.loop_id,
            "intervention": ACTIVE_LOOP.intervention,
        },
        "schema_version": 1,
        "workload": {
            "id": WORKLOAD.workload_id,
            "resource_namespace": WORKLOAD.resource_namespace,
            "source_loop": DEFAULT_LOOP.loop_id,
        },
    }
    if ACTIVE_LOOP.prior_loop_id is not None:
        record["prior_loop"] = {
            "loop_id": ACTIVE_LOOP.prior_loop_id,
            "result_commit": ACTIVE_LOOP.prior_result_commit,
            "run_id": ACTIVE_LOOP.prior_run_id,
        }
    if LOOP_CANDIDATE_QUALIFICATION_ROOT is not None:
        record["setup"] = {
            "candidate_boundary_qualification": {
                "included_in_evidence": True,
                "measured_as_task_cost": False,
            }
        }
    return record
LIMA_CONFIG_FIELDS = frozenset(
    {
        "arch",
        "audio",
        "caCerts",
        "containerd",
        "cpus",
        "disk",
        "firmware",
        "guestInstallPrefix",
        "hostResolver",
        "images",
        "memory",
        "minimumLimaVersion",
        "mountInotify",
        "mountType",
        "mounts",
        "nestedVirtualization",
        "os",
        "param",
        "plain",
        "propagateProxyEnv",
        "ssh",
        "timezone",
        "upgradePackages",
        "user",
        "video",
        "vmOpts",
        "vmType",
    }
)
CANDIDATE_LIMA_CONFIG_FIELDS = LIMA_CONFIG_FIELDS - {"mounts", "param"}
LIMA_INSTANCE_FIELDS = frozenset(
    {
        "HostArch",
        "HostOS",
        "IdentityFile",
        "LimaHome",
        "arch",
        "config",
        "cpus",
        "dir",
        "disk",
        "driverPID",
        "errors",
        "hostAgentPID",
        "hostname",
        "limaVersion",
        "memory",
        "name",
        "param",
        "protected",
        "sshAddress",
        "sshConfigFile",
        "sshLocalPort",
        "status",
        "vmType",
    }
)
CANDIDATE_CONTAINERD_ARCHIVES = (
    {
        "arch": "x86_64",
        "digest": "sha256:40a80a6eec6fc4f225473a87946c2098821b6ec31becef0120c8a50d7b4e432c",
        "location": (
            "https://github.com/containerd/nerdctl/releases/download/v2.3.4/"
            "nerdctl-full-2.3.4-linux-amd64.tar.gz"
        ),
    },
    {
        "arch": "aarch64",
        "digest": "sha256:117d65c3992e67fc4449dd501c8fba19c1d9cbf5a01fd63d68e778888f2f46e0",
        "location": (
            "https://github.com/containerd/nerdctl/releases/download/v2.3.4/"
            "nerdctl-full-2.3.4-linux-arm64.tar.gz"
        ),
    },
)
PENDING_INTEGRITY_FAILURE_DETAIL = (
    "pending integrity or source verification failed"
)
TRUSTED_MODULE_RUNNER = (
    'import runpy,sys;sys.path.insert(0,".");'
    'module=sys.argv.pop(1);runpy.run_module(module,run_name="__main__")'
)
TransferError: type[Exception]
extract_candidate: Callable[[Path, Path, Path], dict[str, Any]]
verify_candidate: Callable[[Path, Path], dict[str, Any]]
_CANDIDATE_TRANSFER_LOADED = False


def _load_candidate_transfer() -> None:
    """Load reviewed local code only after the checkout guard has succeeded."""

    global TransferError, extract_candidate, verify_candidate, _CANDIDATE_TRANSFER_LOADED
    if _CANDIDATE_TRANSFER_LOADED:
        return
    from candidate_transfer import (
        TransferError as CandidateTransferError,
        extract_candidate as candidate_extract,
        verify_candidate as candidate_verify,
    )

    TransferError = CandidateTransferError
    extract_candidate = candidate_extract
    verify_candidate = candidate_verify
    _CANDIDATE_TRANSFER_LOADED = True


class Inconclusive(RuntimeError):
    """The run cannot receive a checked acceptance or rejection."""

    def __init__(self, stage: str, detail: str) -> None:
        super().__init__(detail)
        self.stage = stage
        self.detail = detail


class ExecuteWorkDeadline(BaseException):
    """The automated work window ended and its cleanup reserve must begin."""


class ExecuteHardDeadline(BaseException):
    """The absolute automated deadline ended; only human recovery remains."""


class ExecuteEvidenceIncomplete(BaseException):
    """Automated evidence could not be verified before completion."""


class FinalizationHardDeadline(BaseException):
    """The human-finalization wall deadline elapsed."""


class FinalizationDeadline:
    """Own the non-resumable wall alarm for one human finalization attempt."""

    def __init__(self) -> None:
        self.deadline: float | None = None
        self.completed = False
        self.hard_observed = False
        self._installed = False
        self._previous_handler: Any = None
        self._previous_timer = (0.0, 0.0)
        self._previous_mask: set[signal.Signals] = set()

    @staticmethod
    def _drain_pending_alarm() -> bool:
        observed = False
        while signal.SIGALRM in signal.sigpending():
            signal.sigwait({signal.SIGALRM})
            observed = True
        return observed

    def _handle_alarm(self, _signum: int, _frame: object) -> None:
        if self.completed:
            return
        self.hard_observed = True
        signal.setitimer(signal.ITIMER_REAL, 0)
        raise FinalizationHardDeadline()

    def install(self) -> None:
        if self._installed:
            raise RuntimeError("finalization deadline is already installed")
        previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM})
        try:
            if signal.SIGALRM in previous_mask:
                raise RuntimeError("pre-existing blocked SIGALRM prevents deadline ownership")
            previous_timer = signal.getitimer(signal.ITIMER_REAL)
            if (
                previous_timer != (0.0, 0.0)
                or signal.SIGALRM in signal.sigpending()
            ):
                raise RuntimeError("pre-existing SIGALRM state prevents deadline ownership")
            previous_handler = signal.getsignal(signal.SIGALRM)
            signal.signal(signal.SIGALRM, self._handle_alarm)
            try:
                self.deadline = time.monotonic() + FINALIZATION_TIMEOUT_SECONDS
                signal.setitimer(signal.ITIMER_REAL, FINALIZATION_TIMEOUT_SECONDS)
            except BaseException:
                signal.signal(signal.SIGALRM, previous_handler)
                raise
            self._previous_handler = previous_handler
            self._previous_timer = previous_timer
            self._previous_mask = previous_mask
            self._installed = True
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)

    def complete(self) -> None:
        if not self._installed or self.deadline is None:
            raise RuntimeError("finalization deadline is not installed")
        previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM})
        hard_won = False
        try:
            signal.setitimer(signal.ITIMER_REAL, 0)
            hard_won = (
                self._drain_pending_alarm()
                or self.hard_observed
                or time.monotonic() >= self.deadline
            )
            self.hard_observed = hard_won
            self.completed = not hard_won
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        if hard_won:
            raise FinalizationHardDeadline()

    def restore_blocked(self) -> bool:
        """Restore owned signal state while the caller keeps SIGALRM blocked."""

        if not self._installed:
            return self.hard_observed
        try:
            signal.setitimer(signal.ITIMER_REAL, 0)
            pending = self._drain_pending_alarm()
            if pending or self.hard_observed or (
                not self.completed
                and self.deadline is not None
                and time.monotonic() >= self.deadline
            ):
                self.hard_observed = True
            signal.signal(signal.SIGALRM, self._previous_handler)
            signal.setitimer(signal.ITIMER_REAL, *self._previous_timer)
        finally:
            self._installed = False
        return self.hard_observed


class ExecutionDeadline:
    """Own one phase-aware alarm for automated work, cleanup, and closure."""

    IDLE = "idle"
    WORK = "work"
    CLEANUP_PENDING = "cleanup_pending"
    CLEANUP = "cleanup"
    COMPLETE = "complete"
    HARD = "hard"

    def __init__(self) -> None:
        self.phase = self.IDLE
        self.work_deadline: float | None = None
        self.absolute_deadline: float | None = None
        self.hard_deadline: float | None = None
        self.work_observed = False
        self.hard_observed = False
        self._installed = False
        self._previous_handler: Any = None
        self._previous_timer = (0.0, 0.0)
        self._previous_mask: set[signal.Signals] = set()

    @staticmethod
    def _drain_pending_alarm() -> bool:
        observed = False
        while signal.SIGALRM in signal.sigpending():
            signal.sigwait({signal.SIGALRM})
            observed = True
        return observed

    @staticmethod
    def _arm(deadline_monotonic: float) -> None:
        signal.setitimer(
            signal.ITIMER_REAL,
            max(0.000001, deadline_monotonic - time.monotonic()),
        )

    def _handle_alarm(self, _signum: int, _frame: object) -> None:
        if self.phase in {self.IDLE, self.COMPLETE, self.HARD}:
            return
        now = time.monotonic()
        if (
            self.phase == self.WORK
            and self.absolute_deadline is not None
            and now < self.absolute_deadline
        ):
            self.phase = self.CLEANUP_PENDING
            self.work_observed = True
            self.hard_deadline = self.absolute_deadline
            self._arm(self.absolute_deadline)
            raise ExecuteWorkDeadline()
        self.phase = self.HARD
        self.hard_observed = True
        signal.setitimer(signal.ITIMER_REAL, 0)
        raise ExecuteHardDeadline()

    def install(self) -> None:
        if self._installed:
            raise RuntimeError("execution deadline is already installed")
        previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM})
        try:
            if signal.SIGALRM in previous_mask:
                raise RuntimeError("pre-existing blocked SIGALRM prevents deadline ownership")
            previous_timer = signal.getitimer(signal.ITIMER_REAL)
            if (
                previous_timer != (0.0, 0.0)
                or signal.SIGALRM in signal.sigpending()
            ):
                raise RuntimeError("pre-existing SIGALRM state prevents deadline ownership")
            self._previous_handler = signal.getsignal(signal.SIGALRM)
            self._previous_timer = previous_timer
            self._previous_mask = previous_mask
            signal.signal(signal.SIGALRM, self._handle_alarm)
            self._installed = True
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)

    def start(self, work_deadline: float, absolute_deadline: float) -> None:
        if (
            not self._installed
            or self.phase != self.IDLE
            or not math.isfinite(work_deadline)
            or not math.isfinite(absolute_deadline)
            or work_deadline >= absolute_deadline
        ):
            raise RuntimeError("execution deadline cannot start from this state")
        previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM})
        pending_exception: BaseException | None = None
        try:
            self.work_deadline = work_deadline
            self.absolute_deadline = absolute_deadline
            now = time.monotonic()
            if now >= absolute_deadline:
                self.phase = self.HARD
                self.hard_observed = True
                pending_exception = ExecuteHardDeadline()
            elif now >= work_deadline:
                self.phase = self.CLEANUP_PENDING
                self.work_observed = True
                self.hard_deadline = absolute_deadline
                self._arm(absolute_deadline)
                pending_exception = ExecuteWorkDeadline()
            else:
                self.phase = self.WORK
                self._arm(work_deadline)
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        if pending_exception is not None:
            raise pending_exception

    def begin_cleanup(self) -> bool:
        if not self._installed or self.work_deadline is None or self.absolute_deadline is None:
            raise RuntimeError("execution deadline has not started")
        previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM})
        pending_exception: BaseException | None = None
        try:
            signal.setitimer(signal.ITIMER_REAL, 0)
            pending = self._drain_pending_alarm()
            now = time.monotonic()
            if (
                self.phase == self.HARD
                or self.hard_observed
                or now >= self.absolute_deadline
                or (self.phase == self.CLEANUP and pending)
            ):
                self.phase = self.HARD
                self.hard_observed = True
                pending_exception = ExecuteHardDeadline()
            else:
                self.work_observed = (
                    self.work_observed
                    or pending
                    or self.phase == self.CLEANUP_PENDING
                    or now >= self.work_deadline
                )
                if self.phase != self.CLEANUP:
                    self.hard_deadline = min(
                        self.absolute_deadline,
                        now + CLEANUP_TIMEOUT_SECONDS,
                    )
                if self.hard_deadline is None or now >= self.hard_deadline:
                    self.phase = self.HARD
                    self.hard_observed = True
                    pending_exception = ExecuteHardDeadline()
                else:
                    self.phase = self.CLEANUP
                    self._arm(self.hard_deadline)
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        if pending_exception is not None:
            raise pending_exception
        return self.work_observed

    def complete(self) -> None:
        if not self._installed or self.phase != self.CLEANUP or self.hard_deadline is None:
            raise RuntimeError("execution deadline cannot complete from this state")
        previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM})
        hard_won = False
        try:
            signal.setitimer(signal.ITIMER_REAL, 0)
            pending = self._drain_pending_alarm()
            hard_won = (
                pending
                or self.hard_observed
                or time.monotonic() >= self.hard_deadline
            )
            self.phase = self.HARD if hard_won else self.COMPLETE
            self.hard_observed = hard_won
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        if hard_won:
            raise ExecuteHardDeadline()

    def abort(self) -> None:
        if not self._installed:
            return
        previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM})
        try:
            signal.setitimer(signal.ITIMER_REAL, 0)
            self._drain_pending_alarm()
            self.phase = self.HARD
            self.hard_observed = True
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)

    def restore_blocked(self) -> bool:
        """Restore owned signal state while the caller keeps SIGALRM blocked."""

        if not self._installed:
            return self.hard_observed
        try:
            signal.setitimer(signal.ITIMER_REAL, 0)
            pending = self._drain_pending_alarm()
            now = time.monotonic()
            if (
                self.phase == self.HARD
                or self.hard_observed
                or (
                    self.phase == self.CLEANUP
                    and self.hard_deadline is not None
                    and (pending or now >= self.hard_deadline)
                )
                or (
                    self.phase in {self.WORK, self.CLEANUP_PENDING}
                    and self.absolute_deadline is not None
                    and now >= self.absolute_deadline
                )
            ):
                self.phase = self.HARD
                self.hard_observed = True
            signal.signal(signal.SIGALRM, self._previous_handler)
            signal.setitimer(signal.ITIMER_REAL, *self._previous_timer)
        finally:
            self._installed = False
        return self.hard_observed


@dataclass(frozen=True)
class CommandResult:
    sequence: int
    label: str
    category: str
    argv: list[str]
    started_at: str
    finished_at: str
    duration_seconds: float
    return_code: int
    timed_out: bool
    limit_breach: str | None
    resources: list[str]
    stdout_path: str
    stderr_path: str


@dataclass(frozen=True)
class CapturedProcess:
    return_code: int
    stdout: bytes
    stderr: bytes
    timed_out: bool
    breaches: tuple[str, ...]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime | None = None) -> str:
    return (value or _utc_now()).isoformat()


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    hard_deadline = False
    try:
        with temporary.open("xb", buffering=0) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except (ExecuteHardDeadline, FinalizationHardDeadline):
        hard_deadline = True
        raise
    finally:
        if not hard_deadline:
            temporary.unlink(missing_ok=True)


def _atomic_write_new(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"refusing to replace append-only file: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    hard_deadline = False
    try:
        with temporary.open("xb", buffering=0) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except (ExecuteHardDeadline, FinalizationHardDeadline):
        hard_deadline = True
        raise
    finally:
        if not hard_deadline:
            temporary.unlink(missing_ok=True)


def _evidence_generation_for(path: Path) -> Path | None:
    if LOOP_CANDIDATE_QUALIFICATION_ROOT is not None:
        qualification = LOOP_CANDIDATE_QUALIFICATION_ROOT.absolute()
        absolute = path.absolute()
        if absolute != qualification and absolute.is_relative_to(qualification):
            return qualification
    try:
        relative = path.absolute().relative_to(EVIDENCE_ROOT.absolute())
    except ValueError:
        return None
    if not relative.parts:
        return None
    return EVIDENCE_ROOT / relative.parts[0]


def _write_json(
    path: Path,
    value: Any,
    *,
    reserve_closure: bool = True,
    deadline_guard: Callable[[], None] | None = None,
) -> None:
    encoded = (
        json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    evidence = _evidence_generation_for(path)
    if evidence is not None:
        _require_evidence_capacity(
            evidence,
            len(encoded),
            replacing=path,
            reserve_closure=reserve_closure,
        )
    if deadline_guard is not None:
        deadline_guard()
    _atomic_write(path, encoded)


def _read_json(path: Path) -> Any:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate JSON member: {key}")
            value[key] = item
        return value

    def invalid_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON number: {value}")

    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=unique_object,
        parse_constant=invalid_constant,
    )


def _read_bounded_json(path: Path, *, maximum_bytes: int) -> Any:
    """Read one stable regular JSON file without following a final symlink."""

    flags = os.O_RDONLY | os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ValueError(f"cannot open bounded JSON document: {path.name}") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum_bytes:
            raise ValueError(f"JSON document exceeds {maximum_bytes} bytes or is not regular")
        chunks = []
        remaining = maximum_bytes + 1
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        encoded = b"".join(chunks)
        after = os.fstat(descriptor)
        if len(encoded) > maximum_bytes:
            raise ValueError(f"JSON document exceeds {maximum_bytes} bytes")
        if (
            before.st_dev != after.st_dev
            or before.st_ino != after.st_ino
            or before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
            or before.st_ctime_ns != after.st_ctime_ns
        ):
            raise ValueError("JSON document changed while it was read")
    finally:
        os.close(descriptor)

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate JSON member: {key}")
            value[key] = item
        return value

    def invalid_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON number: {value}")

    try:
        return json.loads(
            encoded.decode("utf-8"),
            object_pairs_hook=unique_object,
            parse_constant=invalid_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("bounded JSON document is not canonical UTF-8 JSON") from exc


def _validate_argv(argv: Sequence[str]) -> list[str]:
    values = list(argv)
    if not values or len(values) > ARGV_MAX_ENTRIES:
        raise ValueError(f"argv must contain 1..{ARGV_MAX_ENTRIES} entries")
    aggregate = 0
    for argument in values:
        if not isinstance(argument, str) or "\0" in argument:
            raise ValueError("argv entries must be NUL-free strings")
        try:
            encoded = argument.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError("argv entries must be valid UTF-8 strings") from exc
        if len(encoded) > ARGV_MAX_ENTRY_BYTES:
            raise ValueError(f"argv entry exceeds {ARGV_MAX_ENTRY_BYTES} UTF-8 bytes")
        aggregate += len(encoded) + 1
    if aggregate > ARGV_MAX_AGGREGATE_BYTES:
        raise ValueError(f"argv exceeds {ARGV_MAX_AGGREGATE_BYTES} aggregate UTF-8 bytes")
    return values


def _evidence_size(evidence: Path) -> int:
    total = 0
    if not evidence.exists():
        return 0
    for path in evidence.rglob("*"):
        if path.is_symlink():
            raise Inconclusive("evidence_safety", "evidence contains a symbolic link")
        if path.is_file():
            total += path.stat().st_size
    return total


def _require_evidence_capacity(
    evidence: Path,
    additional_bytes: int,
    *,
    replacing: Path | None = None,
    reserve_closure: bool = True,
) -> None:
    if additional_bytes < 0:
        raise ValueError("evidence capacity request cannot be negative")
    current = _evidence_size(evidence)
    if replacing is not None and replacing.is_file() and not replacing.is_symlink():
        current -= replacing.stat().st_size
    reserve = EVIDENCE_CLOSURE_RESERVE_BYTES if reserve_closure else 0
    if current + additional_bytes + reserve > RETAINED_EVIDENCE_MAX_BYTES:
        raise Inconclusive(
            "evidence_limit",
            f"retained evidence would exceed {RETAINED_EVIDENCE_MAX_BYTES} bytes",
        )


def _copy_bounded_into_evidence(
    source: Path,
    destination: Path,
    *,
    maximum_bytes: int = CONTROL_DOCUMENT_MAX_BYTES,
) -> None:
    try:
        descriptor = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as exc:
        raise Inconclusive("evidence_capture", f"cannot open {source.name}") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum_bytes:
            raise Inconclusive(
                "evidence_limit",
                f"{source.name} exceeds {maximum_bytes} bytes or is not regular",
            )
        chunks = []
        remaining = maximum_bytes + 1
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        after = os.fstat(descriptor)
        if len(data) > maximum_bytes:
            raise Inconclusive("evidence_limit", f"{source.name} exceeds {maximum_bytes} bytes")
        if (
            before.st_dev != after.st_dev
            or before.st_ino != after.st_ino
            or before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
            or before.st_ctime_ns != after.st_ctime_ns
        ):
            raise Inconclusive("evidence_capture", f"{source.name} changed during capture")
    finally:
        os.close(descriptor)
    evidence = _evidence_generation_for(destination)
    if evidence is None:
        raise ValueError("bounded evidence destination is outside an evidence owner")
    _require_evidence_capacity(evidence, len(data), replacing=destination)
    _atomic_write(destination, data)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(_read_regular_bytes_preserving_mode(path))
    return digest.hexdigest()


def _completion_spec(kind: str) -> tuple[str, str]:
    if kind == "qualification":
        return QUALIFICATION_COMPLETION_NAME, QUALIFICATION_INDEX_NAME
    if kind == "execution":
        return EXECUTION_COMPLETION_NAME, "evidence-index.json"
    if kind == "finalization":
        return FINALIZATION_COMPLETION_NAME, "terminal-evidence-index.json"
    raise ValueError("completion receipt kind is invalid")


def _validate_completion_receipt(
    evidence: Path,
    *,
    kind: str,
    run_id: str,
    contract_commit: str,
    verify_index: bool = True,
) -> dict[str, Any]:
    receipt_name, index_name = _completion_spec(kind)
    value = _read_bounded_json(
        evidence / receipt_name,
        maximum_bytes=CONTROL_DOCUMENT_MAX_BYTES,
    )
    if (
        not isinstance(value, dict)
        or set(value)
        != {
            "artifact_self_recording_tail_seconds",
            "completed_at",
            "contract_commit",
            "index_path",
            "index_sha256",
            "kind",
            "run_id",
            "version",
        }
        or value.get("version") != 1
        or value.get("kind") != kind
        or value.get("run_id") != run_id
        or value.get("contract_commit") != contract_commit
        or value.get("index_path") != index_name
        or value.get("artifact_self_recording_tail_seconds") != "unknown"
        or re.fullmatch(r"[0-9a-f]{64}", str(value.get("index_sha256"))) is None
        or not isinstance(value.get("completed_at"), str)
    ):
        raise ValueError(f"{kind} completion receipt is invalid")
    try:
        completed_at = datetime.fromisoformat(value["completed_at"])
    except ValueError as exc:
        raise ValueError(f"{kind} completion timestamp is invalid") from exc
    if completed_at.tzinfo is None:
        raise ValueError(f"{kind} completion timestamp must include a UTC offset")
    index_path = evidence / index_name
    if verify_index and (
        not index_path.is_file()
        or index_path.is_symlink()
        or _sha256(index_path) != value["index_sha256"]
    ):
        raise ValueError(f"{kind} completion receipt does not bind its index")
    return cast(dict[str, Any], value)


def _write_completion_receipt(
    evidence: Path,
    *,
    kind: str,
    run_id: str,
    contract_commit: str,
) -> None:
    receipt_name, index_name = _completion_spec(kind)
    index_path = evidence / index_name
    if not index_path.is_file() or index_path.is_symlink():
        raise ValueError(f"{kind} completion index is unavailable")
    value = {
        "artifact_self_recording_tail_seconds": "unknown",
        "completed_at": _timestamp(),
        "contract_commit": contract_commit,
        "index_path": index_name,
        "index_sha256": _sha256(index_path),
        "kind": kind,
        "run_id": run_id,
        "version": 1,
    }
    encoded = (
        json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    if _public_safety_labels(encoded, check_host_paths=True):
        raise ValueError(f"{kind} completion receipt is not public-safe")
    _require_evidence_capacity(evidence, len(encoded), reserve_closure=False)
    _atomic_write_new(evidence / receipt_name, encoded)
    _validate_completion_receipt(
        evidence,
        kind=kind,
        run_id=run_id,
        contract_commit=contract_commit,
    )


def _read_regular_bytes_preserving_mode(path: Path) -> bytes:
    """Read an owned evidence file without changing its admitted final mode."""

    try:
        observed = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise ValueError(f"cannot inspect regular evidence file: {path.name}") from exc
    if not stat.S_ISREG(observed.st_mode):
        raise ValueError(f"evidence path is not a regular file: {path.name}")
    original_mode = stat.S_IMODE(observed.st_mode)
    changed_mode = False
    hard_deadline = False
    descriptor: int | None = None
    try:
        try:
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        except PermissionError:
            path.chmod(original_mode | stat.S_IRUSR, follow_symlinks=False)
            changed_mode = True
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        opened = os.fstat(descriptor)
        if (
            opened.st_dev != observed.st_dev
            or opened.st_ino != observed.st_ino
            or not stat.S_ISREG(opened.st_mode)
            or opened.st_size > RETAINED_EVIDENCE_MAX_BYTES
        ):
            raise ValueError("evidence file changed before it was opened")
        chunks = []
        remaining = RETAINED_EVIDENCE_MAX_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        finished_descriptor = os.fstat(descriptor)
        if len(data) > RETAINED_EVIDENCE_MAX_BYTES or (
            finished_descriptor.st_dev != opened.st_dev
            or finished_descriptor.st_ino != opened.st_ino
            or finished_descriptor.st_size != opened.st_size
            or finished_descriptor.st_mtime_ns != opened.st_mtime_ns
        ):
            raise ValueError("evidence file changed while it was read")
    except (ExecuteHardDeadline, FinalizationHardDeadline):
        hard_deadline = True
        raise
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if changed_mode and not hard_deadline:
            path.chmod(original_mode, follow_symlinks=False)
    finished = path.stat(follow_symlinks=False)
    if (
        finished.st_dev != observed.st_dev
        or finished.st_ino != observed.st_ino
        or finished.st_size != observed.st_size
        or finished.st_mtime_ns != observed.st_mtime_ns
        or stat.S_IMODE(finished.st_mode) != original_mode
    ):
        raise ValueError("evidence file identity or mode changed while it was read")
    return data


def _sha256sum_output(value: str, expected_paths: Sequence[str]) -> dict[str, str]:
    observed: dict[str, str] = {}
    for line in value.splitlines():
        fields = line.split(maxsplit=1)
        if len(fields) != 2:
            raise ValueError("sha256sum output is malformed")
        digest, path = fields[0], fields[1].lstrip(" *")
        if (
            re.fullmatch(r"[0-9a-f]{64}", digest) is None
            or path not in expected_paths
            or path in observed
        ):
            raise ValueError("sha256sum output is not the requested file set")
        observed[path] = digest
    if set(observed) != set(expected_paths):
        raise ValueError("sha256sum output is incomplete")
    return observed


def _candidate_identity(manifest_path: Path, completion_path: Path) -> dict[str, Any]:
    completion = _read_json(completion_path)
    command = _validate_completion(completion)["service_command"]
    value = {
        "manifest_sha256": _sha256(manifest_path),
        "service_command": command,
    }
    encoded = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return {
        **value,
        "candidate_identity_sha256": hashlib.sha256(encoded).hexdigest(),
        "scheme": "sha256(canonical-json(manifest_sha256,service_command))",
    }


def _relative(path: Path, base: Path) -> str:
    return path.resolve().relative_to(base.resolve()).as_posix()


def _run_id() -> str:
    return f"{_utc_now().strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"


def _instance_name(run_id: str) -> str:
    value = f"q1-l1-candidate-{run_id.lower()}"
    if INSTANCE_PATTERN.fullmatch(value) is None:
        raise ValueError("invalid candidate instance name")
    return value


def _evaluator_run_root(run_id: str) -> str:
    if RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise ValueError("invalid run ID for evaluator root")
    return f"/tmp/q1-l1-run-{run_id}"


def _evaluator_attempt_root(run_id: str, attempt: int) -> str:
    if attempt not in {1, 2}:
        raise ValueError("invalid evaluator attempt")
    return f"{_evaluator_run_root(run_id)}/attempt-{attempt}"


def _safe_environment() -> dict[str, str]:
    return {
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "HOME": str(HOST_HOME),
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        "TMPDIR": "/tmp",
    }


def _prepare_child_process() -> None:
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGALRM})


def _kill_process_group(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _kill_and_reap_process_group(
    process: subprocess.Popen[bytes],
    *,
    hard_cutoff_active: bool = False,
) -> None:
    """Kill before exposing an alarm, then reap without crossing the hard cutoff."""

    def reap_without_wait() -> None:
        try:
            process.wait(timeout=0)
        except Exception:
            pass

    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM})
    deferred_alarm: BaseException | None = None
    cleanup_failure: Exception | None = None
    try:
        try:
            _kill_process_group(process)
        except Exception as exc:
            cleanup_failure = exc
        if process.stdin is not None:
            try:
                process.stdin.close()
            except Exception as exc:
                if cleanup_failure is None:
                    cleanup_failure = exc
            process.stdin = None
    finally:
        try:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        except (
            ExecuteWorkDeadline,
            ExecuteHardDeadline,
            FinalizationHardDeadline,
        ) as exc:
            deferred_alarm = exc
    if isinstance(
        deferred_alarm,
        (ExecuteHardDeadline, FinalizationHardDeadline),
    ):
        reap_without_wait()
        raise deferred_alarm
    if hard_cutoff_active:
        reap_without_wait()
        return
    if cleanup_failure is not None:
        if deferred_alarm is not None:
            raise deferred_alarm
        raise cleanup_failure
    try:
        process.wait(timeout=1.0)
    except ExecuteWorkDeadline as exc:
        deferred_alarm = exc
        try:
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired as reap_exc:
            raise RuntimeError("killed command process could not be reaped") from reap_exc
    except FinalizationHardDeadline:
        reap_without_wait()
        raise
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("killed command process could not be reaped") from exc
    if deferred_alarm is not None:
        raise deferred_alarm


def _communicate_bounded(
    process: subprocess.Popen[bytes],
    *,
    input_bytes: bytes | None,
    timeout_seconds: float,
) -> CapturedProcess:
    """Drain process pipes without imposing stream limits on child-created files."""

    if process.stdout is None or process.stderr is None:
        raise RuntimeError("bounded process capture requires stdout and stderr pipes")
    if input_bytes is not None and process.stdin is None:
        raise RuntimeError("bounded process input requires a stdin pipe")

    selector = selectors.DefaultSelector()
    stdout = bytearray()
    stderr = bytearray()
    buffers = {"stdout": stdout, "stderr": stderr}
    deadline = time.monotonic() + timeout_seconds
    input_offset = 0
    timed_out = False
    breaches: list[str] = []

    def close_stream(stream: Any) -> None:
        try:
            selector.unregister(stream)
        except (KeyError, ValueError):
            pass
        try:
            stream.close()
        except OSError:
            pass
        if process.stdin is stream:
            process.stdin = None

    def close_all_streams() -> None:
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None:
                close_stream(stream)

    try:
        for stream, name in ((process.stdout, "stdout"), (process.stderr, "stderr")):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        if process.stdin is not None:
            if input_bytes:
                os.set_blocking(process.stdin.fileno(), False)
                selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")
            else:
                close_stream(process.stdin)

        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                break
            events = selector.select(remaining)
            if not events:
                continue
            for key, _mask in events:
                stream = key.fileobj
                if key.data == "stdin":
                    try:
                        written = os.write(
                            key.fd,
                            cast(bytes, input_bytes)[input_offset : input_offset + 64 * 1024],
                        )
                    except BrokenPipeError:
                        close_stream(stream)
                        continue
                    except BlockingIOError:
                        continue
                    if written == 0:
                        raise RuntimeError("bounded process input made no progress")
                    input_offset += written
                    if input_offset >= len(cast(bytes, input_bytes)):
                        close_stream(stream)
                    continue

                try:
                    chunk = os.read(key.fd, 64 * 1024)
                except BlockingIOError:
                    continue
                if not chunk:
                    close_stream(stream)
                    continue
                buffer = buffers[cast(str, key.data)]
                available = COMMAND_STREAM_MAX_BYTES - len(buffer)
                if len(chunk) > available:
                    if available > 0:
                        buffer.extend(chunk[:available])
                    breaches.append(f"{key.data}_size")
                    break
                buffer.extend(chunk)
            if breaches:
                break

        if breaches or timed_out:
            _kill_and_reap_process_group(process)
        else:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                _kill_and_reap_process_group(process)
            else:
                try:
                    process.wait(timeout=remaining)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    _kill_and_reap_process_group(process)
    finally:
        close_all_streams()
        selector.close()

    if process.returncode is None:
        raise RuntimeError("bounded process was not reaped")
    return CapturedProcess(
        return_code=process.returncode,
        stdout=bytes(stdout),
        stderr=bytes(stderr),
        timed_out=timed_out,
        breaches=tuple(breaches),
    )


def _run_bounded_process(
    command: Sequence[str],
    *,
    environment: dict[str, str],
    input_bytes: bytes | None,
    timeout_seconds: float,
) -> CapturedProcess:
    process: subprocess.Popen[bytes] | None = None
    try:
        previous_mask = signal.pthread_sigmask(
            signal.SIG_BLOCK,
            {signal.SIGALRM},
        )
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=environment,
                start_new_session=True,
                preexec_fn=_prepare_child_process,
            )
        finally:
            signal.pthread_sigmask(
                signal.SIG_SETMASK,
                previous_mask,
            )
    except BaseException as exc:
        if process is not None:
            _kill_and_reap_process_group(
                process,
                hard_cutoff_active=isinstance(
                    exc,
                    (ExecuteHardDeadline, FinalizationHardDeadline),
                ),
            )
        raise
    try:
        return _communicate_bounded(
            process,
            input_bytes=input_bytes,
            timeout_seconds=timeout_seconds,
        )
    except BaseException as exc:
        _kill_and_reap_process_group(
            process,
            hard_cutoff_active=isinstance(
                exc,
                (ExecuteHardDeadline, FinalizationHardDeadline),
            ),
        )
        raise


def _truncate_utf8(value: str, maximum: int) -> str:
    encoded = value.encode("utf-8")
    if len(encoded) <= maximum:
        return value
    return encoded[:maximum].decode("utf-8", errors="ignore")


class Recorder:
    def __init__(self, evidence: Path, *, deadline_monotonic: float | None = None) -> None:
        self.evidence = evidence
        self.logs = evidence / "logs"
        self.logs.mkdir(parents=True)
        self.records_path = evidence / "commands.jsonl"
        self.sequence = 0
        self.environment = _safe_environment()
        self._protected_values: list[tuple[str, str]] = []
        self.redactions: list[dict[str, Any]] = []
        self._path_replacements = _host_path_replacements()
        self.deadline_monotonic = deadline_monotonic

    def protect(self, label: str, value: str) -> None:
        if value:
            self._protected_values.append((label, value))

    def clear_protected_values(self) -> None:
        self._protected_values.clear()

    def protected_values(self) -> tuple[tuple[str, str], ...]:
        return tuple(self._protected_values)

    def _sanitize(self, value: str, *, sequence: int, stream: str) -> str:
        sanitized = value
        for label, protected in self._protected_values:
            occurrences = sanitized.count(protected)
            if occurrences:
                sanitized = sanitized.replace(protected, f"[REDACTED:{label}]")
                self.redactions.append(
                    {
                        "count": occurrences,
                        "item": label,
                        "sequence": sequence,
                        "stream": stream,
                    }
                )
        for path, replacement in self._path_replacements:
            occurrences = sanitized.count(path)
            if occurrences:
                sanitized = sanitized.replace(path, replacement)
                self.redactions.append(
                    {
                        "count": occurrences,
                        "item": replacement.strip("[]"),
                        "sequence": sequence,
                        "stream": stream,
                    }
                )
        return sanitized

    def _sanitize_value(self, value: Any, *, sequence: int, stream: str) -> Any:
        if isinstance(value, str):
            return self._sanitize(value, sequence=sequence, stream=stream)
        if isinstance(value, list):
            return [
                self._sanitize_value(item, sequence=sequence, stream=stream) for item in value
            ]
        if isinstance(value, dict):
            return {
                key: self._sanitize_value(item, sequence=sequence, stream=stream)
                for key, item in value.items()
            }
        return value

    def _record(
        self,
        record: dict[str, Any],
        *,
        deadline_guard: Callable[[], None] | None = None,
    ) -> None:
        sequence = record.get("sequence")
        if not isinstance(sequence, int) or isinstance(sequence, bool):
            raise ValueError("command record lacks a valid sequence")
        safe_record = self._sanitize_value(record, sequence=sequence, stream="record")
        encoded = (
            json.dumps(safe_record, allow_nan=False, sort_keys=True) + "\n"
        ).encode("utf-8")
        _require_evidence_capacity(self.evidence, len(encoded))
        if deadline_guard is not None:
            deadline_guard()
        with self.records_path.open("ab", buffering=0) as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())

    def run(
        self,
        argv: Sequence[str],
        *,
        label: str,
        category: str = "machine",
        resources: Sequence[str] | None = None,
        input_text: str | None = None,
        timeout_seconds: float | None = None,
        deadline_reserve_seconds: float = CLEANUP_TIMEOUT_SECONDS,
        stdout_transform: Callable[[str], str] | None = None,
        stdout_destination: Path | None = None,
        stderr_destination: Path | None = None,
        stdout_observer: Callable[[bytes], None] | None = None,
    ) -> CommandResult:
        self.sequence += 1
        sequence = self.sequence
        safe_label = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
        stdout_path = stdout_destination or self.logs / f"{sequence:03d}-{safe_label}.stdout"
        stderr_path = stderr_destination or self.logs / f"{sequence:03d}-{safe_label}.stderr"
        for destination in (stdout_path, stderr_path):
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.parent.resolve().is_relative_to(self.evidence.resolve()):
                raise ValueError("command stream destination must be inside run evidence")
        started_wall = _utc_now()
        started = time.monotonic()
        timed_out = False
        breaches: list[str] = []
        try:
            command = _validate_argv(argv)
        except ValueError as exc:
            command = ["[argv rejected by control envelope]"]
            breaches.append("argv")
            return_code = 125
            stdout = ""
            stderr = f"trusted argv envelope rejected command: {exc}\n"
        else:
            input_bytes: bytes | None = None
            if input_text is not None:
                try:
                    input_bytes = input_text.encode("utf-8")
                except UnicodeEncodeError as exc:
                    breaches.append("control_document")
                    return_code = 125
                    stdout = ""
                    stderr = f"trusted input is not UTF-8: {exc}\n"
                else:
                    if len(input_bytes) > CONTROL_DOCUMENT_MAX_BYTES:
                        breaches.append("control_document")
                        return_code = 125
                        stdout = ""
                        stderr = (
                            "trusted input exceeds "
                            f"{CONTROL_DOCUMENT_MAX_BYTES} bytes\n"
                        )
            if not breaches:
                requested_timeout = (
                    DEFAULT_COMMAND_TIMEOUT_SECONDS
                    if timeout_seconds is None
                    else float(timeout_seconds)
                )
                if not math.isfinite(requested_timeout) or requested_timeout <= 0:
                    breaches.append("command_deadline")
                    return_code = 125
                    stdout = ""
                    stderr = "trusted command timeout must be finite and positive\n"
                else:
                    effective_timeout = requested_timeout
                    clipped_by_automated_deadline = False
                    if self.deadline_monotonic is not None:
                        available = (
                            self.deadline_monotonic
                            - time.monotonic()
                            - max(0.0, deadline_reserve_seconds)
                        )
                        if available <= 0:
                            breaches.append("automated_phase_deadline")
                            return_code = 124
                            timed_out = True
                            stdout = ""
                            stderr = "automated phase deadline left no command budget\n"
                        elif available < effective_timeout:
                            effective_timeout = available
                            clipped_by_automated_deadline = True
                    if not breaches:
                        try:
                            captured = _run_bounded_process(
                                command,
                                environment=self.environment,
                                input_bytes=input_bytes,
                                timeout_seconds=effective_timeout,
                            )
                        except OSError as exc:
                            return_code = 125
                            raw_stdout = b""
                            raw_stderr = (
                                f"trusted command launch failed: {type(exc).__name__}\n"
                            ).encode("ascii")
                        else:
                            return_code = captured.return_code
                            raw_stdout = captured.stdout
                            raw_stderr = captured.stderr
                            timed_out = captured.timed_out
                            breaches.extend(captured.breaches)
                        if timed_out:
                            return_code = 124
                            breaches.append(
                                "automated_phase_deadline"
                                if clipped_by_automated_deadline
                                else "command_deadline"
                            )
                        if stdout_observer is not None and not any(
                            breach in {"stdout_size", "stderr_size"}
                            for breach in breaches
                        ):
                            stdout_observer(raw_stdout)
                        stdout = raw_stdout.decode("utf-8", errors="replace")
                        stderr = raw_stderr.decode("utf-8", errors="replace")
                        if breaches and return_code == 0:
                            return_code = 125
        if stdout_transform is not None and not any(
            breach in {"stdout_size", "stderr_size"} for breach in breaches
        ):
            try:
                stdout = stdout_transform(stdout)
            except Exception as exc:
                return_code = 125
                stdout = ""
                stderr += f"\ntrusted stdout filter failed: {type(exc).__name__}\n"
        finished_wall = _utc_now()
        duration = time.monotonic() - started
        safe_stdout = _truncate_utf8(
            self._sanitize(stdout, sequence=sequence, stream="stdout"),
            COMMAND_STREAM_MAX_BYTES,
        )
        safe_stderr = _truncate_utf8(
            self._sanitize(stderr, sequence=sequence, stream="stderr"),
            COMMAND_STREAM_MAX_BYTES,
        )
        encoded_stdout = safe_stdout.encode("utf-8")
        encoded_stderr = safe_stderr.encode("utf-8")
        try:
            _require_evidence_capacity(
                self.evidence,
                len(encoded_stdout) + len(encoded_stderr),
            )
        except Inconclusive:
            breaches.append("retained_evidence")
            return_code = 125
            encoded_stdout = b""
            encoded_stderr = b"retained evidence limit rejected command streams\n"
            _require_evidence_capacity(
                self.evidence,
                len(encoded_stderr),
            )
        _atomic_write(stdout_path, encoded_stdout)
        _atomic_write(stderr_path, encoded_stderr)
        memberships = set(resources or ())
        memberships.add("trusted_machine")
        if category == "agent":
            memberships.update(("agent", "candidate_vm"))
        elif category == "evaluator":
            memberships.add("evaluator")
        elif category == "candidate_vm":
            memberships.add("candidate_vm")
        if command and command[0] == "limactl":
            if any(
                argument == EVALUATOR_INSTANCE
                or argument.startswith(f"{EVALUATOR_INSTANCE}:")
                for argument in command[1:]
            ):
                memberships.add("evaluator")
            if any(
                INSTANCE_PATTERN.fullmatch(argument.split(":", 1)[0]) is not None
                for argument in command[1:]
            ):
                memberships.add("candidate_vm")
        result = CommandResult(
            sequence=sequence,
            label=label,
            category=category,
            argv=command,
            started_at=_timestamp(started_wall),
            finished_at=_timestamp(finished_wall),
            duration_seconds=duration,
            return_code=return_code,
            timed_out=timed_out,
            limit_breach=",".join(dict.fromkeys(breaches)) or None,
            resources=sorted(memberships),
            stdout_path=_relative(stdout_path, self.evidence),
            stderr_path=_relative(stderr_path, self.evidence),
        )
        self._record({"kind": "command", **asdict(result)})
        return result

    def internal(
        self,
        *,
        label: str,
        started_wall: datetime,
        started_monotonic: float,
        detail: dict[str, Any],
        resources: Sequence[str] = ("trusted_machine",),
        deadline_guard: Callable[[], None] | None = None,
    ) -> None:
        self.sequence += 1
        finished = _utc_now()
        self._record(
            {
                "category": "machine",
                "detail": detail,
                "duration_seconds": time.monotonic() - started_monotonic,
                "finished_at": _timestamp(finished),
                "kind": "internal",
                "label": label,
                "resources": sorted(set(resources) | {"trusted_machine"}),
                "sequence": self.sequence,
                "started_at": _timestamp(started_wall),
            },
            deadline_guard=deadline_guard,
        )


def _command_breach(result: CommandResult) -> str | None:
    value = getattr(result, "limit_breach", None)
    return value if isinstance(value, str) and value else None


def _require_success(result: CommandResult, stage: str) -> None:
    breach = _command_breach(result)
    if breach is not None:
        raise Inconclusive(
            "execution_envelope",
            f"{result.label} breached {breach}",
        )
    if result.return_code != 0:
        raise Inconclusive(stage, f"{result.label} exited {result.return_code}")


def _limactl_shell(instance: str, *command: str, workdir: str | None = None) -> list[str]:
    argv = ["limactl", "shell", "--tty=false"]
    if workdir is not None:
        argv.extend(("--workdir", workdir))
    argv.append(instance)
    argv.extend(command)
    return argv


def _trusted_module_argv(module: str, *arguments: str) -> tuple[str, ...]:
    return (
        "/usr/bin/python3",
        "-B",
        "-I",
        "-c",
        TRUSTED_MODULE_RUNNER,
        module,
        *arguments,
    )


def _allowlisted_lima_names(raw: str) -> str:
    names = []
    for line in raw.splitlines():
        value = json.loads(line)
        if not isinstance(value, dict) or not isinstance(value.get("name"), str):
            raise ValueError("Lima instance record has no name")
        name = value["name"]
        if not name or "\0" in name or "\n" in name:
            raise ValueError("Lima instance name is invalid")
        names.append(name)
    return "".join(json.dumps({"name": name}, sort_keys=True) + "\n" for name in names)


def _binary_size(value: str) -> int:
    match = re.fullmatch(r"([1-9][0-9]*)(KiB|MiB|GiB|TiB)", value)
    if match is None:
        raise ValueError("Lima size is not a canonical binary quantity")
    return int(match.group(1)) * {
        "KiB": 1024,
        "MiB": 1024**2,
        "GiB": 1024**3,
        "TiB": 1024**4,
    }[match.group(2)]


def _expected_lima_user() -> dict[str, Any]:
    host_user = pwd.getpwuid(os.getuid())
    return {
        "comment": host_user.pw_gecos,
        "home": f"/home/{host_user.pw_name}.guest",
        "name": host_user.pw_name,
        "shell": "/bin/bash",
        "uid": os.getuid(),
    }


def _validate_lima_instance_record(
    value: dict[str, Any],
    instance: str,
    *,
    expected_parameters: dict[str, str] | None,
) -> None:
    instance_root = HOST_HOME / ".lima" / instance
    positive_int_fields = ("driverPID", "hostAgentPID", "sshLocalPort")
    expected_fields = (
        LIMA_INSTANCE_FIELDS
        if expected_parameters is not None
        else LIMA_INSTANCE_FIELDS - {"param"}
    )
    if set(value) not in {
        expected_fields,
        expected_fields - {"errors"},
    }:
        raise ValueError("Lima inspection has an unmapped instance field")
    if any(
        not isinstance(value.get(field), int)
        or isinstance(value.get(field), bool)
        or value[field] <= 0
        for field in positive_int_fields
    ):
        raise ValueError("Lima inspection has an invalid dynamic process or port field")
    if (
        value.get("hostname") != f"lima-{instance}"
        or value.get("dir") != str(instance_root)
        or value.get("sshConfigFile") != str(instance_root / "ssh.config")
        or value.get("errors", []) != []
        or value.get("sshAddress") != "127.0.0.1"
        or not isinstance(value.get("protected"), bool)
        or not isinstance(value.get("limaVersion"), str)
        or not value["limaVersion"]
        or (
            value.get("param") != expected_parameters
            if expected_parameters is not None
            else "param" in value
        )
        or value.get("HostOS") != "darwin"
        or value.get("HostArch") != "aarch64"
        or value.get("LimaHome") != str(HOST_HOME / ".lima")
        or value.get("IdentityFile") != str(HOST_HOME / ".lima" / "_config" / "user")
    ):
        raise ValueError("Lima inspection dynamic instance boundary drifted")


def _normalized_evaluator_lima(raw: str) -> str:
    lines = [line for line in raw.splitlines() if line]
    if len(lines) != 1:
        raise ValueError("q1-l1-evaluator Lima inspection did not return exactly one instance")
    value = json.loads(lines[0])
    if not isinstance(value, dict) or value.get("name") != EVALUATOR_INSTANCE:
        raise ValueError("q1-l1-evaluator Lima inspection returned the wrong instance")
    if value.get("status") != "Running":
        raise ValueError("q1-l1-evaluator is not already running")
    _validate_lima_instance_record(
        value,
        EVALUATOR_INSTANCE,
        expected_parameters={"internal_netplanOptional": "true"},
    )
    config = value.get("config")
    if not isinstance(config, dict) or set(config) != LIMA_CONFIG_FIELDS:
        raise ValueError("q1-l1-evaluator has an unmapped Lima config field")
    if "dns" in config or "portForwards" in config:
        raise ValueError("q1-l1-evaluator DNS or port-forward config is not approved")
    if (
        config.get("arch") != value.get("arch")
        or config.get("cpus") != value.get("cpus")
        or config.get("vmType") != value.get("vmType")
        or not isinstance(config.get("memory"), str)
        or not isinstance(config.get("disk"), str)
        or _binary_size(config["memory"]) != value.get("memory")
        or _binary_size(config["disk"]) != value.get("disk")
    ):
        raise ValueError("q1-l1-evaluator effective and configured Lima resources disagree")
    mounts = config.get("mounts")
    workspace_parent = str(REPOSITORY_ROOT.parent.resolve())
    if (
        not isinstance(mounts, list)
        or len(mounts) != 1
        or not isinstance(mounts[0], dict)
        or set(mounts[0]) != {"9p", "location", "mountPoint", "sshfs", "writable"}
        or mounts[0].get("location") != workspace_parent
        or mounts[0].get("mountPoint") != workspace_parent
        or mounts[0].get("writable") is not True
    ):
        raise ValueError("q1-l1-evaluator workspace-parent mount does not match the reviewed role")
    sshfs = mounts[0].get("sshfs")
    nine_p = mounts[0].get("9p")
    if (
        not isinstance(sshfs, dict)
        or set(sshfs) != {"cache", "followSymlinks", "sftpDriver"}
        or not isinstance(nine_p, dict)
        or set(nine_p) != {"cache", "msize", "protocolVersion", "securityModel"}
    ):
        raise ValueError("q1-l1-evaluator inactive mount defaults are invalid")
    images = config.get("images")
    if not isinstance(images, list):
        raise ValueError("q1-l1-evaluator image config is invalid")
    selected_images = []
    for image in images:
        if not isinstance(image, dict) or set(image) - {"arch", "digest", "location"}:
            raise ValueError("q1-l1-evaluator image config is invalid")
        if image.get("arch") == value.get("arch"):
            normalized = {
                "architecture": image.get("arch"),
                "location": image.get("location"),
            }
            if "digest" in image:
                normalized["digest"] = image["digest"]
            selected_images.append(normalized)
    if not selected_images or "digest" not in selected_images[0]:
        raise ValueError("q1-l1-evaluator selected base image is not digest-pinned")
    containerd = config.get("containerd")
    if not isinstance(containerd, dict) or set(containerd) != {"archives", "system", "user"}:
        raise ValueError("q1-l1-evaluator containerd config is invalid")
    archives = containerd.get("archives")
    if not isinstance(archives, list):
        raise ValueError("q1-l1-evaluator containerd archive config is invalid")
    matching_archives = [
        archive
        for archive in archives
        if isinstance(archive, dict) and archive.get("arch") == value.get("arch")
    ]
    if len(matching_archives) != 1 or set(matching_archives[0]) != {
        "arch",
        "digest",
        "location",
    }:
        raise ValueError("q1-l1-evaluator selected containerd archive is invalid")
    vm_options = config.get("vmOpts")
    if (
        not isinstance(vm_options, dict)
        or set(vm_options) != {"qemu", "vz"}
        or not isinstance(vm_options.get("qemu"), dict)
        or set(vm_options["qemu"]) != {"cpuType", "minimumVersion"}
        or not isinstance(vm_options.get("vz"), dict)
    ):
        raise ValueError("q1-l1-evaluator VM options are invalid")
    vz = vm_options["vz"]
    if set(vz) != {"diskImageFormat", "rosetta"} or not isinstance(vz["rosetta"], dict):
        raise ValueError("q1-l1-evaluator VZ options are invalid")
    ssh = config.get("ssh")
    firmware = config.get("firmware")
    audio = config.get("audio")
    video = config.get("video")
    resolver = config.get("hostResolver")
    certificates = config.get("caCerts")
    parameters = config.get("param")
    user = config.get("user")
    if not all(
        isinstance(item, dict)
        for item in (ssh, firmware, audio, video, resolver, certificates, parameters, user)
    ):
        raise ValueError("q1-l1-evaluator normalized Lima subconfig is invalid")
    expected_nested_keys = (
        (ssh, {"forwardAgent", "forwardX11", "forwardX11Trusted", "loadDotSSHPubKeys", "localPort", "overVsock"}),
        (firmware, {"legacyBIOS"}),
        (audio, {"device"}),
        (video, {"display"}),
        (resolver, {"enabled", "ipv6"}),
        (certificates, {"removeDefaults"}),
        (parameters, {"internal_netplanOptional"}),
        (vz["rosetta"], {"binfmt", "enabled"}),
    )
    if any(set(item) != expected for item, expected in expected_nested_keys):
        raise ValueError("q1-l1-evaluator has an unmapped nested Lima config field")
    if user != _expected_lima_user():
        raise ValueError("q1-l1-evaluator Lima user mapping drifted")
    observation = {
        "base_image": selected_images[0],
        "base_image_candidates": selected_images,
        "config": {
            "absent_fields": ["dns", "port_forwards"],
            "audio": {"device": audio.get("device")},
            "ca_certificates": {"remove_defaults": certificates.get("removeDefaults")},
            "containerd": {
                "archive": {
                    "architecture": matching_archives[0].get("arch"),
                    "digest": matching_archives[0].get("digest"),
                    "location": matching_archives[0].get("location"),
                },
                "system": containerd.get("system"),
                "user": containerd.get("user"),
            },
            "firmware": {"legacy_bios": firmware.get("legacyBIOS")},
            "guest_install_prefix": config.get("guestInstallPrefix"),
            "host_resolver": {
                "enabled": resolver.get("enabled"),
                "ipv6": resolver.get("ipv6"),
            },
            "inactive_backend_defaults": {
                "mount": {
                    "nine_p": {
                        "cache": nine_p.get("cache"),
                        "msize": nine_p.get("msize"),
                        "protocol_version": nine_p.get("protocolVersion"),
                        "security_model": nine_p.get("securityModel"),
                    },
                    "sshfs": {
                        "cache": sshfs.get("cache"),
                        "follow_symlinks": sshfs.get("followSymlinks"),
                        "sftp_driver": sshfs.get("sftpDriver"),
                    },
                },
                "vm_options": {
                    "qemu": {
                        "cpu_type": vm_options["qemu"].get("cpuType"),
                        "minimum_version": vm_options["qemu"].get("minimumVersion"),
                    }
                },
            },
            "minimum_lima_version": config.get("minimumLimaVersion"),
            "mount_inotify": config.get("mountInotify"),
            "mount_type": config.get("mountType"),
            "mounts": [{"role": "workspace-parent", "writable": True}],
            "nested_virtualization": config.get("nestedVirtualization"),
            "os": config.get("os"),
            "parameters": {
                "internal_netplan_optional": parameters.get("internal_netplanOptional")
            },
            "plain": config.get("plain"),
            "propagate_proxy_env": config.get("propagateProxyEnv"),
            "ssh": {
                "forward_agent": ssh.get("forwardAgent"),
                "forward_x11": ssh.get("forwardX11"),
                "forward_x11_trusted": ssh.get("forwardX11Trusted"),
                "load_dot_ssh_pub_keys": ssh.get("loadDotSSHPubKeys"),
                "local_port": ssh.get("localPort"),
                "over_vsock": ssh.get("overVsock"),
            },
            "timezone": config.get("timezone"),
            "upgrade_packages": config.get("upgradePackages"),
            "video": {"display": video.get("display")},
            "vm_options": {
                "vz": {
                    "disk_image_format": vz.get("diskImageFormat"),
                    "rosetta": {
                        "binfmt": vz["rosetta"].get("binfmt"),
                        "enabled": vz["rosetta"].get("enabled"),
                    },
                }
            },
        },
        "instance": {
            "architecture": value.get("arch"),
            "cpus": value.get("cpus"),
            "disk_bytes": value.get("disk"),
            "lima_version": value.get("limaVersion"),
            "memory_bytes": value.get("memory"),
            "name": value.get("name"),
            "protected": value.get("protected"),
            "status": value.get("status"),
            "vm_type": value.get("vmType"),
        },
    }
    return json.dumps(observation, ensure_ascii=True, sort_keys=True) + "\n"


def _normalized_candidate_lima(
    raw: str,
    instance: str,
    configured_lima: dict[str, Any],
) -> str:
    lines = [line for line in raw.splitlines() if line]
    if len(lines) != 1:
        raise ValueError("candidate Lima inspection did not return exactly one instance")
    value = json.loads(lines[0])
    if (
        not isinstance(value, dict)
        or value.get("name") != instance
        or INSTANCE_PATTERN.fullmatch(instance) is None
    ):
        raise ValueError("candidate Lima inspection returned the wrong instance")
    if value.get("status") != "Running":
        raise ValueError("candidate Lima instance is not running")
    _validate_lima_instance_record(value, instance, expected_parameters=None)
    config = value.get("config")
    if not isinstance(config, dict) or frozenset(config) not in {
        CANDIDATE_LIMA_CONFIG_FIELDS,
        CANDIDATE_LIMA_CONFIG_FIELDS | {"portForwards"},
    }:
        raise ValueError("candidate Lima instance has an unmapped config field")
    if "dns" in config or config.get("portForwards", []) != []:
        raise ValueError("candidate Lima instance has unapproved DNS or port forwards")
    if (
        config.get("arch") != "aarch64"
        or config.get("arch") != value.get("arch")
        or config.get("vmType") != "vz"
        or config.get("vmType") != value.get("vmType")
        or config.get("cpus") != 4
        or config.get("cpus") != value.get("cpus")
        or config.get("memory") != "8GiB"
        or value.get("memory") != 8 * 1024**3
        or config.get("disk") != "40GiB"
        or value.get("disk") != 40 * 1024**3
        or config.get("minimumLimaVersion") != "2.1.4"
        or config.get("mountInotify") is not False
        or config.get("propagateProxyEnv") is not False
        or config.get("timezone") != "America/Denver"
    ):
        raise ValueError("candidate Lima resources or confidentiality boundary drifted")
    expected_image = {
        "arch": "aarch64",
        "digest": configured_lima.get("configured_image_digest"),
        "location": configured_lima.get("configured_image_location"),
    }
    if (
        configured_lima.get("configured_mounts") != []
        or not isinstance(expected_image["digest"], str)
        or not isinstance(expected_image["location"], str)
        or config.get("images") != [expected_image]
    ):
        raise ValueError("candidate Lima selected image does not match its reviewed authority")
    ssh = config.get("ssh")
    resolver = config.get("hostResolver")
    containerd = config.get("containerd")
    expected_defaults = {
        "audio": {"device": ""},
        "caCerts": {"removeDefaults": False},
        "firmware": {"legacyBIOS": False},
        "guestInstallPrefix": "/usr/local",
        "mountType": "virtiofs",
        "nestedVirtualization": False,
        "os": "Linux",
        "plain": False,
        "upgradePackages": False,
        "video": {"display": "none"},
        "vmOpts": {
            "vz": {
                "diskImageFormat": "raw",
                "rosetta": {"binfmt": False, "enabled": False},
            },
        },
    }
    if (
        not isinstance(ssh, dict)
        or set(ssh)
        != {
            "forwardAgent",
            "forwardX11",
            "forwardX11Trusted",
            "loadDotSSHPubKeys",
            "localPort",
            "overVsock",
        }
        or ssh.get("forwardAgent") is not False
        or ssh.get("forwardX11") is not False
        or ssh.get("forwardX11Trusted") is not False
        or ssh.get("loadDotSSHPubKeys") is not False
        or ssh.get("overVsock") is not True
        or ssh.get("localPort") != 0
        or resolver != {"enabled": True, "ipv6": False}
        or not isinstance(containerd, dict)
        or set(containerd) != {"archives", "system", "user"}
        or containerd.get("system") is not False
        or containerd.get("user") is not False
        or containerd.get("archives") != list(CANDIDATE_CONTAINERD_ARCHIVES)
        or config.get("user") != _expected_lima_user()
        or any(config.get(field) != expected for field, expected in expected_defaults.items())
    ):
        raise ValueError("candidate Lima forwarding or guest-service boundary drifted")
    safe_config = {
        "audio": {"device": config["audio"]["device"]},
        "arch": config["arch"],
        "ca_certificates": {"remove_defaults": config["caCerts"]["removeDefaults"]},
        "containerd": {
            "archives": containerd["archives"],
            "system": containerd["system"],
            "user": containerd["user"],
        },
        "cpus": config["cpus"],
        "disk_bytes": value["disk"],
        "firmware": {"legacy_bios": config["firmware"]["legacyBIOS"]},
        "guest_install_prefix": config["guestInstallPrefix"],
        "host_resolver": resolver,
        "memory_bytes": value["memory"],
        "minimum_lima_version": config["minimumLimaVersion"],
        "mount_inotify": config["mountInotify"],
        "mount_type": config["mountType"],
        "mounts": [],
        "nested_virtualization": config["nestedVirtualization"],
        "os": config["os"],
        "parameters": {},
        "plain": config["plain"],
        "port_forwards": [],
        "propagate_proxy_env": config["propagateProxyEnv"],
        "ssh": {
            "forward_agent": ssh["forwardAgent"],
            "forward_x11": ssh["forwardX11"],
            "forward_x11_trusted": ssh["forwardX11Trusted"],
            "load_dot_ssh_pub_keys": ssh["loadDotSSHPubKeys"],
            "over_vsock": ssh["overVsock"],
        },
        "timezone": config["timezone"],
        "upgrade_packages": config["upgradePackages"],
        "user_mapping": "reviewed_host_identity",
        "video": {"display": config["video"]["display"]},
        "vm_type": config["vmType"],
        "vm_options": {
            "vz": {
                "disk_image_format": config["vmOpts"]["vz"]["diskImageFormat"],
                "rosetta": {
                    "binfmt": config["vmOpts"]["vz"]["rosetta"]["binfmt"],
                    "enabled": config["vmOpts"]["vz"]["rosetta"]["enabled"],
                },
            },
        },
    }
    observation = {
        "base_image": {
            "architecture": expected_image["arch"],
            "digest": expected_image["digest"],
            "location": expected_image["location"],
        },
        "config": safe_config,
        "instance": {
            "architecture": value["arch"],
            "cpus": value["cpus"],
            "disk_bytes": value["disk"],
            "lima_version": value.get("limaVersion"),
            "memory_bytes": value["memory"],
            "name": value["name"],
            "protected": value.get("protected"),
            "status": value["status"],
            "vm_type": value["vmType"],
        },
    }
    if (
        not isinstance(observation["instance"]["lima_version"], str)
        or not observation["instance"]["lima_version"]
        or not isinstance(observation["instance"]["protected"], bool)
    ):
        raise ValueError("candidate Lima dynamic instance fields are invalid")
    return json.dumps(observation, allow_nan=False, ensure_ascii=True, sort_keys=True) + "\n"


def _validate_contract_commit(value: str) -> str:
    if re.fullmatch(r"[0-9a-f]{40,64}", value) is None:
        raise ValueError("contract commit must be a full lowercase Git object ID")
    return value


def _checkout_guard(
    expected_commit: str,
    *,
    allowed_untracked: tuple[Path, ...] = (),
    recorder: Recorder | None = None,
) -> None:
    expected_commit = _validate_contract_commit(expected_commit)
    git_prefix = ["git", "-C", str(REPOSITORY_ROOT)]

    def checked_output(arguments: Sequence[str], label: str) -> bytes:
        argv = [*git_prefix, *arguments]
        if recorder is None:
            return_code, stdout, _stderr, timed_out = _bounded_preflight_command(argv)
            if timed_out or return_code != 0:
                raise RuntimeError(f"checkout guard command failed: {label}")
            return stdout
        captured = bytearray()
        result = recorder.run(
            argv,
            label=label,
            stdout_observer=captured.extend,
            deadline_reserve_seconds=0,
        )
        if _command_breach(result) is not None or result.return_code != 0:
            raise RuntimeError(f"checkout guard command failed: {label}")
        return bytes(captured)

    branch = checked_output(
        ["branch", "--show-current"],
        "verify approved checkout branch",
    ).decode("utf-8").strip()
    if branch != "main":
        raise RuntimeError(f"{ACTIVE_LOOP.loop_id} must execute sequentially on main")
    head = checked_output(
        ["rev-parse", "HEAD"],
        "verify approved checkout commit",
    ).decode("utf-8").strip()
    if head != expected_commit:
        raise RuntimeError("checked-out HEAD is not the explicitly approved contract commit")
    tracked = checked_output(
        ["status", "--porcelain", "--untracked-files=no"],
        "verify approved tracked checkout",
    )
    if tracked:
        raise RuntimeError("tracked files differ from the approved contract commit")
    untracked = checked_output(
        ["ls-files", "--others", "--exclude-standard", "-z"],
        "verify approved untracked checkout",
    ).split(b"\0")
    allowed = tuple(path.resolve() for path in allowed_untracked)
    for raw in untracked:
        if not raw:
            continue
        path = (REPOSITORY_ROOT / os.fsdecode(raw)).resolve()
        if not any(path == root or path.is_relative_to(root) for root in allowed):
            raise RuntimeError(f"unrelated untracked path exists: {os.fsdecode(raw)}")
    ignored = checked_output(
        ["ls-files", "--others", "--ignored", "--exclude-standard", "-z"],
        "verify ignored checkout paths",
    ).split(b"\0")
    executable_suffixes = {".dylib", ".py", ".pyc", ".pyo", ".pth", ".so"}
    controlling_names = {"GNUmakefile", "Makefile", "makefile", "sitecustomize.py", "usercustomize.py"}
    inert_ignored_roots = {".mypy_cache", ".typing-venv", "build"}
    for raw in ignored:
        if not raw:
            continue
        decoded = os.fsdecode(raw)
        relative = PurePosixPath(decoded)
        lexical_path = REPOSITORY_ROOT / decoded
        try:
            loop_relative = lexical_path.relative_to(ROOT)
        except ValueError:
            loop_relative = None
        if (
            loop_relative is not None
            and loop_relative.parts
            and loop_relative.parts[0] in inert_ignored_roots
        ):
            inert_root = ROOT / loop_relative.parts[0]
            try:
                root_metadata = inert_root.lstat()
                item_metadata = lexical_path.lstat()
            except OSError as exc:
                raise RuntimeError(
                    f"ignored inert path cannot be inspected: {decoded}"
                ) from exc
            if (
                stat.S_ISLNK(root_metadata.st_mode)
                or not stat.S_ISDIR(root_metadata.st_mode)
                or stat.S_ISLNK(item_metadata.st_mode)
            ):
                raise RuntimeError(f"ignored inert path is not a real local path: {decoded}")
            continue
        path = lexical_path.resolve()
        if any(path == root or path.is_relative_to(root) for root in allowed):
            continue
        try:
            executable = bool(lexical_path.stat().st_mode & 0o111)
        except OSError:
            executable = True
        if (
            relative.name in controlling_names
            or relative.suffix.lower() in executable_suffixes
            or executable
        ):
            raise RuntimeError(f"ignored execution-affecting path exists: {decoded}")


def _acquire_execution_lock() -> int:
    descriptor = os.open(EXECUTION_LOCK_PATH, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        os.close(descriptor)
        raise RuntimeError(
            f"another {WORKLOAD.workload_id} execution or finalization owns the process lock"
        ) from exc
    return descriptor


def _bounded_preflight_command(argv: Sequence[str]) -> tuple[int, bytes, bytes, bool]:
    """Run one pre-evidence inspection under the normal command envelope."""

    command = _validate_argv(argv)
    try:
        captured = _run_bounded_process(
            command,
            environment=_safe_environment(),
            input_bytes=None,
            timeout_seconds=DEFAULT_COMMAND_TIMEOUT_SECONDS,
        )
    except OSError as exc:
        raise RuntimeError("preflight command could not start") from exc
    if captured.breaches:
        raise RuntimeError(
            "preflight command exceeded its output limit: "
            + ",".join(captured.breaches)
        )
    return (
        captured.return_code,
        captured.stdout,
        captured.stderr,
        captured.timed_out,
    )


def _preflight_lima_records() -> list[dict[str, Any]]:
    try:
        return_code, stdout, _stderr, timed_out = _bounded_preflight_command(
            ["limactl", "list", "--json"]
        )
    except (RuntimeError, ValueError) as exc:
        raise RuntimeError("Lima orphan inspection failed; human recovery is required") from exc
    if timed_out:
        raise RuntimeError("Lima orphan inspection timed out; human recovery is required")
    if return_code != 0:
        raise RuntimeError("Lima orphan inspection failed; human recovery is required")
    records = []
    try:
        for line in stdout.decode("utf-8").splitlines():
            value = json.loads(line)
            if not isinstance(value, dict) or not isinstance(value.get("name"), str):
                raise ValueError("invalid Lima record")
            records.append(value)
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError("Lima orphan inspection returned invalid JSON") from exc
    return records


def _parse_evaluator_orphans(raw: str) -> dict[str, int]:
    value = json.loads(raw)
    keys = {"cgroups", "loops", "mounts", "processes", "roots"}
    if (
        not isinstance(value, dict)
        or set(value) != {"counts", "passed", "version"}
        or value.get("version") != 1
        or not isinstance(value.get("counts"), dict)
        or set(value["counts"]) != keys
    ):
        raise ValueError("evaluator residue report has the wrong fields")
    if not all(
        isinstance(value["counts"][key], int)
        and not isinstance(value["counts"][key], bool)
        and value["counts"][key] >= 0
        for key in keys
    ):
        raise ValueError("evaluator residue report is invalid")
    passed = not any(value["counts"].values())
    if value.get("passed") is not passed:
        raise ValueError("evaluator residue report disposition is invalid")
    return cast(dict[str, int], value["counts"])


def _normalized_evaluator_orphans(raw: str) -> str:
    value = _parse_evaluator_orphans(raw)
    if any(value.values()):
        raise ValueError("q1-l1-evaluator contains run-scoped residue")
    return json.dumps(
        {"counts": {key: 0 for key in sorted(value)}, "passed": True, "version": 1},
        sort_keys=True,
    ) + "\n"


def _evaluator_orphan_probe_argv(
    *,
    run_root: str | None = None,
    probe_path: Path | None = None,
) -> list[str]:
    argv = _limactl_shell(
        EVALUATOR_INSTANCE,
        "sudo",
        "/usr/bin/python3.14",
        "-B",
        "-I",
        str(probe_path or (REPRODUCTION / "evaluator_residue_probe.py")),
    )
    if run_root is not None:
        argv.extend(("--run-root", run_root))
    return argv


def _preflight_evaluator_orphans() -> dict[str, int] | None:
    try:
        return_code, stdout, _stderr, timed_out = _bounded_preflight_command(
            _evaluator_orphan_probe_argv()
        )
    except (RuntimeError, ValueError):
        return None
    if (
        timed_out
        or return_code != 0
        or len(stdout) > CONTROL_DOCUMENT_MAX_BYTES
    ):
        return None
    try:
        return _parse_evaluator_orphans(stdout.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
        return None


def _assert_no_orphaned_run() -> None:
    try:
        evidence_metadata = EVIDENCE_ROOT.lstat()
    except FileNotFoundError:
        pass
    else:
        if stat.S_ISLNK(evidence_metadata.st_mode) or not stat.S_ISDIR(
            evidence_metadata.st_mode
        ):
            raise RuntimeError(
                f"{ACTIVE_LOOP.loop_id} evidence root is not a real directory; "
                "human recovery is required"
            )
        if any(EVIDENCE_ROOT.iterdir()):
            raise RuntimeError(
                f"unfinished or prior {ACTIVE_LOOP.loop_id} evidence exists; "
                "human recovery is required"
            )
    records = _preflight_lima_records()
    candidate_instances = sorted(
        value["name"]
        for value in records
        if INSTANCE_PATTERN.fullmatch(value["name"]) is not None
    )
    if candidate_instances:
        raise RuntimeError(
            "prior Q1/L1 candidate VM exists; review is required"
        )
    evaluator = [value for value in records if value["name"] == EVALUATOR_INSTANCE]
    if len(evaluator) != 1 or evaluator[0].get("status") != "Running":
        raise RuntimeError(
            "Q1/L1 evaluator must be prepared and Running before execution"
        )
    orphans = _preflight_evaluator_orphans()
    if orphans is None:
        raise RuntimeError(
            "Q1/L1 evaluator residue cannot be attributed safely; review is required"
        )
    if any(orphans.values()):
        raise RuntimeError(
            "Q1/L1 evaluator residue exists; inspect ownership before execution"
        )


def _preflight(expected_commit: str) -> str:
    _checkout_guard(expected_commit)
    if LOOP_CANDIDATE_QUALIFICATION_ROOT is not None:
        require_candidate_boundary_qualification(
            LOOP_CANDIDATE_QUALIFICATION_ROOT,
            expected_commit,
        )
    if RESULT_PATH.exists():
        raise RuntimeError(f"{ACTIVE_LOOP.loop_id} already has RESULT.md")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY must be supplied out of band before execution")
    _assert_no_orphaned_run()
    return api_key


def _copy_run_authorities(evidence: Path) -> None:
    destination = evidence / "authorities"
    destination.mkdir(parents=True)
    paths = (
        QUESTION_PATH,
        LOOP_PATH,
        REPRODUCTION / "candidate-lima.yaml",
        REPRODUCTION / "candidate-apt-packages.txt",
        REPRODUCTION / "candidate-codex-config.toml",
        REPRODUCTION / "candidate-codex-requirements.toml",
        REPRODUCTION / "agent-completion.schema.json",
        REPRODUCTION / "agent-initial-prompt.md",
        REPRODUCTION / "agent-remediation-prompt.md",
        REPRODUCTION / "HUMAN_REVIEW.md",
        REPRODUCTION / "prepare-candidate-lima.sh",
        REPRODUCTION / "bootstrap-candidate-lima.sh",
        REPRODUCTION / "candidate_boundary_probe.py",
        REPRODUCTION / "candidate_snapshot.py",
        REPRODUCTION / "candidate_transfer.py",
        REPRODUCTION / "verify_candidate_boundary.py",
    )
    for path in paths:
        _copy_bounded_into_evidence(
            path,
            destination / path.name,
            maximum_bytes=16 * 1024 * 1024,
        )
    _copy_bounded_into_evidence(
        ROOT / "Makefile",
        destination / "Makefile",
        maximum_bytes=16 * 1024 * 1024,
    )
    if LOOP_ROOT != ROOT:
        workload_destination = destination / "workload"
        workload_destination.mkdir()
        _copy_bounded_into_evidence(
            ROOT / "LOOP.md",
            workload_destination / "LOOP.md",
            maximum_bytes=16 * 1024 * 1024,
        )
    if LOOP_AUTHORITY_PATHS:
        loop_destination = destination / "loop"
        loop_destination.mkdir()
        for path in LOOP_AUTHORITY_PATHS:
            _copy_bounded_into_evidence(
                path,
                loop_destination / path.name,
                maximum_bytes=16 * 1024 * 1024,
            )
    if LOOP_CANDIDATE_QUALIFICATION_ROOT is not None:
        setup_destination = (
            evidence / "setup" / "candidate-boundary-qualification"
        )
        setup_destination.mkdir(parents=True)
        for path in sorted(LOOP_CANDIDATE_QUALIFICATION_ROOT.rglob("*")):
            relative = path.relative_to(LOOP_CANDIDATE_QUALIFICATION_ROOT)
            target = setup_destination / relative
            if path.is_symlink():
                raise Inconclusive(
                    "evidence_capture",
                    "candidate qualification contains a symbolic link",
                )
            if path.is_dir():
                target.mkdir(exist_ok=True)
            elif path.is_file() and not path.is_symlink():
                _copy_bounded_into_evidence(
                    path,
                    target,
                    maximum_bytes=COMMAND_STREAM_MAX_BYTES,
                )
            else:
                raise Inconclusive(
                    "evidence_capture",
                    "candidate qualification contains a non-regular path",
                )
    for source_root, name in (
        (REPRODUCTION, "reproduction"),
        (ROOT / "evaluator", "evaluator"),
    ):
        target_root = destination / name
        target_root.mkdir()
        for path in sorted(source_root.rglob("*")):
            relative = path.relative_to(source_root)
            if "__pycache__" in relative.parts:
                continue
            target = target_root / relative
            if path.is_symlink():
                raise Inconclusive("evidence_capture", "run authority contains a symbolic link")
            if path.is_dir():
                target.mkdir(exist_ok=True)
            elif path.is_file() and not path.is_symlink():
                _copy_bounded_into_evidence(
                    path,
                    target,
                    maximum_bytes=16 * 1024 * 1024,
                )
            else:
                raise Inconclusive("evidence_capture", "run authority contains a non-regular path")
    contract_destination = destination / "public-contract"
    contract_destination.mkdir()
    for path in sorted((ROOT / "public" / "contract").rglob("*")):
        relative = path.relative_to(ROOT / "public" / "contract")
        target = contract_destination / relative
        if path.is_symlink():
            raise Inconclusive("evidence_capture", "public contract contains a symbolic link")
        if path.is_dir():
            target.mkdir()
        elif path.is_file() and not path.is_symlink():
            _copy_bounded_into_evidence(
                path,
                target,
                maximum_bytes=16 * 1024 * 1024,
            )
        else:
            raise Inconclusive("evidence_capture", "public contract contains a non-regular path")


def _validate_evaluator(
    recorder: Recorder,
    evidence: Path,
    run_id: str,
    state: dict[str, Any],
) -> None:
    host_observation: dict[str, Any] = {}
    guest_observation: dict[str, Any] = {}

    def capture_host_observation(raw: str) -> str:
        normalized = _normalized_evaluator_lima(raw)
        value = json.loads(normalized)
        if not isinstance(value, dict):
            raise ValueError("normalized Lima observation is not an object")
        host_observation.update(value)
        return '{"collected":true,"scope":"lima"}\n'

    def capture_guest_observation(raw: str) -> str:
        if len(raw.encode("utf-8")) > CONTROL_DOCUMENT_MAX_BYTES:
            raise ValueError("normalized guest observation exceeds one MiB")

        def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            value: dict[str, Any] = {}
            for key, item in pairs:
                if key in value:
                    raise ValueError("normalized guest observation has a duplicate member")
                value[key] = item
            return value

        value = json.loads(raw, object_pairs_hook=unique_object)
        if not isinstance(value, dict):
            raise ValueError("normalized guest observation is not an object")
        guest_observation.update(value)
        return '{"collected":true,"scope":"guest"}\n'

    lima = recorder.run(
        ["limactl", "list", "--json", EVALUATOR_INSTANCE],
        label="inspect reviewed evaluator Lima configuration",
        category="evaluator",
        stdout_transform=capture_host_observation,
    )
    _require_success(lima, "evaluator_validation")
    residue = recorder.run(
        _evaluator_orphan_probe_argv(
            probe_path=evidence
            / "authorities"
            / "reproduction"
            / "evaluator_residue_probe.py"
        ),
        label="verify evaluator has no run residue",
        category="evaluator",
        stdout_transform=_normalized_evaluator_orphans,
    )
    _require_success(residue, "evaluator_validation")
    _copy_bounded_into_evidence(
        evidence / residue.stdout_path,
        evidence / "evaluator-residue-validation.json",
    )
    evaluator_root = _evaluator_run_root(run_id)
    evaluator_tmp = f"{evaluator_root}/tmp"
    root_created = recorder.run(
        _limactl_shell(
            EVALUATOR_INSTANCE,
            "/usr/bin/python3",
            "-B",
            "-I",
            "-c",
            f"import os,sys; os.mkdir(sys.argv[1],{EVALUATOR_RUN_DIRECTORY_MODE:#o})",
            evaluator_root,
        ),
        label="create run-scoped evaluator root",
        category="evaluator",
    )
    _require_success(root_created, "evaluator_validation")
    state["evaluator_cleanup_required"] = True
    state["evaluator_run_root_created"] = True
    tmp_created = recorder.run(
        _limactl_shell(
            EVALUATOR_INSTANCE,
            "/usr/bin/python3",
            "-B",
            "-I",
            "-c",
            f"import os,sys; os.mkdir(sys.argv[1],{EVALUATOR_RUN_DIRECTORY_MODE:#o})",
            evaluator_tmp,
        ),
        label="create run-scoped evaluator temporary directory",
        category="evaluator",
    )
    _require_success(tmp_created, "evaluator_validation")
    authority_reproduction = evidence / "authorities" / "reproduction"
    guest = recorder.run(
        _limactl_shell(
            EVALUATOR_INSTANCE,
            "sudo",
            "/usr/bin/env",
            f"TMPDIR={evaluator_tmp}",
            "/usr/bin/python3.14",
            "-B",
            "-I",
            str(authority_reproduction / "collect_evaluator_guest.py"),
        ),
        label="collect reviewed evaluator guest fingerprint",
        category="evaluator",
        stdout_transform=capture_guest_observation,
    )
    _require_success(guest, "evaluator_validation")
    if not host_observation or not guest_observation:
        raise Inconclusive(
            "evaluator_validation", "evaluator fingerprint collection was incomplete"
        )
    expected_host_keys = {"base_image", "base_image_candidates", "config", "instance"}
    expected_guest_keys = {
        "installed_package_inventory",
        "isolation",
        "packages",
        "runtime",
        "tools",
    }
    overlap = set(host_observation) & set(guest_observation)
    if (
        set(host_observation) != expected_host_keys
        or set(guest_observation) != expected_guest_keys
        or overlap
        or "schema_version" in host_observation
        or "schema_version" in guest_observation
    ):
        raise Inconclusive(
            "evaluator_validation", "evaluator fingerprint fragments overlap"
        )
    observation = {
        **host_observation,
        **guest_observation,
        "schema_version": 1,
    }
    observation_text = json.dumps(
        observation,
        allow_nan=False,
        ensure_ascii=True,
        sort_keys=True,
    ) + "\n"
    if len(observation_text.encode("utf-8")) > CONTROL_DOCUMENT_MAX_BYTES:
        raise Inconclusive(
            "evaluator_validation", "normalized evaluator observation exceeds one MiB"
        )
    boundary = recorder.run(
        [
            sys.executable,
            "-B",
            "-I",
            str(authority_reproduction / "verify_evaluator_boundary.py"),
            "--observation",
            "-",
        ],
        label="compare evaluator fingerprint with reviewed authority",
        input_text=observation_text,
    )
    boundary_report_path = evidence / "evaluator-boundary-validation.json"
    _copy_bounded_into_evidence(
        evidence / boundary.stdout_path,
        boundary_report_path,
    )
    boundary_report = _read_bounded_json(
        boundary_report_path,
        maximum_bytes=CONTROL_DOCUMENT_MAX_BYTES,
    )
    _require_success(boundary, "evaluator_validation")
    if not isinstance(boundary_report, dict) or boundary_report.get("passed") is not True:
        raise Inconclusive(
            "evaluator_validation", "evaluator authority comparison did not pass"
        )
    _write_json(evidence / "evaluator-environment.json", observation)

    dispatch_report = ROOT / "build" / "dispatch-validation.json"
    dispatch_report.unlink(missing_ok=True)
    dispatch = recorder.run(
        _limactl_shell(
            EVALUATOR_INSTANCE,
            "/usr/bin/env",
            f"TMPDIR={evaluator_tmp}",
            "make",
            "PYTHON=/usr/bin/python3",
            "verify-dispatch",
            workdir=str(ROOT),
        ),
        label="verify dispatch mechanics in evaluator VM",
    )
    _require_success(dispatch, "evaluator_validation")
    if not dispatch_report.is_file():
        raise Inconclusive("evaluator_validation", "dispatch validation report is missing")
    dispatch_value = _read_bounded_json(
        dispatch_report,
        maximum_bytes=CONTROL_DOCUMENT_MAX_BYTES,
    )
    if not isinstance(dispatch_value, dict) or dispatch_value.get("passed") is not True:
        raise Inconclusive("evaluator_validation", "dispatch validation report did not pass")
    _copy_bounded_into_evidence(
        dispatch_report,
        evidence / "dispatch-validation.json",
    )
    report_path = ROOT / "build" / "evaluator-validation.json"
    report_path.unlink(missing_ok=True)
    bank = recorder.run(
        _limactl_shell(
            EVALUATOR_INSTANCE,
            "/usr/bin/env",
            f"TMPDIR={evaluator_tmp}",
            "make",
            "PYTHON=/usr/bin/python3",
            "verify-evaluator",
            workdir=str(ROOT),
        ),
        label="validate evaluator bank",
        timeout_seconds=10 * 60,
    )
    _require_success(bank, "evaluator_validation")
    if not report_path.is_file():
        raise Inconclusive("evaluator_validation", "evaluator validation report is missing")
    report = _read_bounded_json(
        report_path,
        maximum_bytes=CONTROL_DOCUMENT_MAX_BYTES,
    )
    if not isinstance(report, dict) or report.get("passed") is not True:
        raise Inconclusive("evaluator_validation", "evaluator validation report did not pass")
    _copy_bounded_into_evidence(
        report_path,
        evidence / "evaluator-validation.json",
    )
    isolation_report = ROOT / "build" / "isolation-validation.json"
    isolation_report.unlink(missing_ok=True)
    isolation = recorder.run(
        _limactl_shell(
            EVALUATOR_INSTANCE,
            "/usr/bin/env",
            f"TMPDIR={evaluator_tmp}",
            "make",
            "PYTHON=/usr/bin/python3",
            "verify-isolation",
            workdir=str(ROOT),
        ),
        label="validate isolated runtime",
    )
    _require_success(isolation, "evaluator_validation")
    if not isolation_report.is_file():
        raise Inconclusive("evaluator_validation", "isolation validation report is missing")
    isolation_value = _read_bounded_json(
        isolation_report,
        maximum_bytes=CONTROL_DOCUMENT_MAX_BYTES,
    )
    if not isinstance(isolation_value, dict) or isolation_value.get("passed") is not True:
        raise Inconclusive("evaluator_validation", "isolation validation report did not pass")
    _copy_bounded_into_evidence(
        isolation_report,
        evidence / "isolation-validation.json",
    )


def _provision_candidate(recorder: Recorder, evidence: Path, instance: str) -> None:
    result = recorder.run(
        [str(REPRODUCTION / "prepare-candidate-lima.sh"), instance],
        label="provision and probe candidate VM",
        timeout_seconds=PROVISION_TIMEOUT_SECONDS,
    )
    source = ROOT / "build" / "candidate-boundary-validation.json"
    if source.is_file():
        _copy_bounded_into_evidence(source, evidence / "boundary-validation.json")
    _require_success(result, "candidate_provisioning")
    if not (evidence / "boundary-validation.json").is_file():
        raise Inconclusive("candidate_provisioning", "candidate boundary report is missing")
    report = _read_bounded_json(
        evidence / "boundary-validation.json",
        maximum_bytes=CONTROL_DOCUMENT_MAX_BYTES,
    )
    if not isinstance(report, dict) or report.get("passed") is not True:
        raise Inconclusive("candidate_provisioning", "candidate boundary validation did not pass")


def _capture_candidate_environment(recorder: Recorder, evidence: Path, instance: str) -> None:
    boundary = _read_bounded_json(
        evidence / "boundary-validation.json",
        maximum_bytes=CONTROL_DOCUMENT_MAX_BYTES,
    )
    try:
        configured_lima = boundary["provenance"]["lima"]
    except (KeyError, TypeError) as exc:
        raise Inconclusive(
            "candidate_provisioning",
            "candidate boundary report lacks its Lima authority",
        ) from exc
    if not isinstance(configured_lima, dict):
        raise Inconclusive(
            "candidate_provisioning",
            "candidate boundary report has an invalid Lima authority",
        )
    lima_observation: dict[str, Any] = {}

    def capture_lima(raw: str) -> str:
        normalized = _normalized_candidate_lima(raw, instance, configured_lima)
        value = json.loads(normalized)
        if not isinstance(value, dict):
            raise ValueError("normalized candidate Lima observation is invalid")
        lima_observation.update(value)
        return '{"collected":true,"scope":"candidate-lima"}\n'

    lima = recorder.run(
        ["limactl", "list", "--json", instance],
        label="inspect created candidate Lima configuration",
        category="candidate_vm",
        stdout_transform=capture_lima,
    )
    _require_success(lima, "candidate_provisioning")
    if not lima_observation:
        raise Inconclusive(
            "candidate_provisioning",
            "candidate Lima runtime provenance was not captured",
        )
    package_names = [
        line.split("=", 1)[0]
        for line in (REPRODUCTION / "candidate-apt-packages.txt")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]
    commands: list[tuple[str, list[str]]] = [
        ("candidate Codex version", _limactl_shell(instance, "codex", "--version")),
        ("candidate Codex features", _limactl_shell(instance, "codex", "features", "list")),
        (
            "candidate npm package tree",
            _limactl_shell(instance, "npm", "list", "--global", "--json", "@openai/codex"),
        ),
        ("candidate Python version", _limactl_shell(instance, "python3.14", "--version")),
        ("candidate kernel", _limactl_shell(instance, "uname", "-a")),
        (
            "candidate apt package versions",
            _limactl_shell(instance, "dpkg-query", "-W", *package_names),
        ),
    ]
    records = []
    for label, argv in commands:
        result = recorder.run(argv, label=label)
        _require_success(result, "candidate_provisioning")
        records.append({"command_sequence": result.sequence, "label": label})
    executable = recorder.run(
        _limactl_shell(
            instance,
            "sh",
            "-lc",
            'path=$(command -v codex) && test -n "$path" && printf "%s\\n" "$path" && sha256sum "$path"',
        ),
        label="locate and hash candidate Codex executable",
    )
    _require_success(executable, "candidate_provisioning")
    records.append(
        {
            "command_sequence": executable.sequence,
            "label": "candidate Codex executable and hash",
        }
    )
    _write_json(
        evidence / "candidate-environment.json",
        {
            "codex_version_required": CODEX_VERSION,
            "lima": lima_observation,
            "records": records,
            "requested_model": MODEL,
            "requested_reasoning_effort": REASONING_EFFORT,
        },
    )


def _login(recorder: Recorder, instance: str, api_key: str) -> None:
    result = recorder.run(
        _limactl_shell(instance, "codex", "login", "--with-api-key"),
        label="authenticate candidate Codex",
        input_text=api_key + "\n",
    )
    _require_success(result, "agent_authentication")


def _thread_id(events_path: Path) -> str:
    for line in events_path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            isinstance(event, dict)
            and event.get("type") == "thread.started"
            and isinstance(event.get("thread_id"), str)
        ):
            return event["thread_id"]
    raise Inconclusive("agent_invocation", "agent JSONL did not contain a thread ID")


def _validated_thread_id(events_path: Path, expected: str | None) -> str:
    observed = _thread_id(events_path)
    if expected is not None and observed != expected:
        raise Inconclusive(
            "agent_invocation",
            "remediation JSONL did not identify the original Codex thread",
        )
    return observed


def _usage(events_path: Path) -> dict[str, int | str]:
    observed: dict[str, int | str] = {field: "unknown" for field in TOKEN_FIELDS}
    for line in events_path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict) or not isinstance(event.get("usage"), dict):
            continue
        usage = event["usage"]
        for field in TOKEN_FIELDS:
            value = usage.get(field)
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                observed[field] = value
    return observed


def _validate_completion(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or not isinstance(value.get("status"), str):
        raise Inconclusive("agent_invocation", "agent completion is not a structured declaration")
    if value["status"] == "blocked":
        if set(value) != {"reason", "status"} or not isinstance(value["reason"], str):
            raise Inconclusive("agent_invocation", "agent blocked declaration is invalid")
        if len(value["reason"].encode("utf-8")) > CONTROL_DOCUMENT_MAX_BYTES:
            raise Inconclusive("agent_invocation", "agent blocked reason exceeds control limit")
        raise Inconclusive("agent_invocation", f"implementation agent blocked: {value['reason']}")
    if value["status"] != "declared_complete" or set(value) != {
        "service_command",
        "status",
    }:
        raise Inconclusive("agent_invocation", "agent did not declare completed candidate bytes")
    command = value["service_command"]
    if not isinstance(command, list):
        raise Inconclusive("agent_invocation", "agent service command is invalid")
    try:
        command = _validate_argv(command)
    except ValueError as exc:
        raise Inconclusive("agent_invocation", f"agent service command is invalid: {exc}") from exc
    if not command[0]:
        raise Inconclusive("agent_invocation", "agent service executable is empty")
    value["service_command"] = command
    return cast(dict[str, Any], value)


def _agent_shell_command(remote_completion: str, resume_thread_id: str | None) -> str:
    common = (
        f"--strict-config --ignore-user-config --ignore-rules --json "
        f"--output-schema /etc/codex/q1-l1-agent-completion.schema.json "
        f"-m {MODEL} -c 'model_reasoning_effort=\"{REASONING_EFFORT}\"' "
        f"-o \"{remote_completion}\""
    )
    if resume_thread_id is None:
        return (
            f"exec timeout --signal=KILL {REMOTE_AGENT_TIMEOUT} "
            f"codex exec {common} --color never -C \"$HOME/candidate\" -"
        )
    if re.fullmatch(r"[0-9a-fA-F-]{36}", resume_thread_id) is None:
        raise Inconclusive("agent_invocation", "recorded Codex thread ID is invalid")
    return (
        f"cd \"$HOME/candidate\" && "
        f"exec timeout --signal=KILL {REMOTE_AGENT_TIMEOUT} "
        f"codex exec resume {common} {resume_thread_id} -"
    )


def _invoke_agent(
    recorder: Recorder,
    evidence: Path,
    instance: str,
    run_id: str,
    *,
    attempt: int,
    prompt: str,
    resume_thread_id: str | None,
) -> tuple[Path, str]:
    agent_directory = evidence / "agent" / f"attempt-{attempt}"
    agent_directory.mkdir(parents=True, exist_ok=True)
    prompt_path = agent_directory / "prompt.md"
    try:
        encoded_prompt = prompt.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise Inconclusive("agent_invocation", "agent prompt is not valid UTF-8") from exc
    if len(encoded_prompt) > CONTROL_DOCUMENT_MAX_BYTES:
        raise Inconclusive("agent_invocation", "agent prompt exceeds one MiB")
    _require_evidence_capacity(
        evidence,
        len(encoded_prompt),
        replacing=prompt_path,
    )
    _atomic_write(prompt_path, encoded_prompt)
    remote_completion = f"/var/tmp/{run_id}-agent-attempt-{attempt}.json"
    invocation = _agent_shell_command(remote_completion, resume_thread_id)
    result = recorder.run(
        _limactl_shell(instance, "sh", "-lc", invocation),
        label=f"agent attempt {attempt}",
        category="agent",
        input_text=prompt,
        timeout_seconds=AGENT_OUTER_TIMEOUT_SECONDS,
        stdout_destination=agent_directory / "events.jsonl",
        stderr_destination=agent_directory / "stderr.txt",
    )
    events_path = evidence / result.stdout_path
    stderr_path = evidence / result.stderr_path
    _write_json(
        agent_directory / "usage.json",
        {
            "charge": {
                "amount": "unknown",
                "currency": "unknown",
                "reason": "codex exec JSONL reports token usage but no monetary charge",
            },
            "duration_seconds": result.duration_seconds,
            "model_requested": MODEL,
            "reasoning_effort_requested": REASONING_EFFORT,
            "tokens": _usage(events_path),
        },
    )
    breach = _command_breach(result)
    if breach is not None:
        raise Inconclusive(
            "agent_invocation",
            f"agent attempt {attempt} breached {breach}",
        )
    if result.return_code != 0:
        reason = "timed out" if result.return_code == 124 else f"exited {result.return_code}"
        raise Inconclusive("agent_invocation", f"agent attempt {attempt} {reason}")
    thread_id = _validated_thread_id(events_path, resume_thread_id)
    completion_path = agent_directory / "completion.json"
    remote_size = recorder.run(
        _limactl_shell(
            instance,
            "stat",
            "-c",
            "%s",
            remote_completion,
        ),
        label=f"measure agent attempt {attempt} completion",
        category="candidate_vm",
    )
    _require_success(remote_size, "agent_invocation")
    try:
        completion_size = int(
            (evidence / remote_size.stdout_path).read_text(encoding="utf-8").strip()
        )
    except (OSError, ValueError) as exc:
        raise Inconclusive("agent_invocation", "agent completion size is invalid") from exc
    if completion_size < 0 or completion_size > CONTROL_DOCUMENT_MAX_BYTES:
        raise Inconclusive(
            "agent_invocation",
            f"agent completion exceeds {CONTROL_DOCUMENT_MAX_BYTES} bytes",
        )
    with tempfile.TemporaryDirectory(prefix=f"{run_id}-completion-") as temporary:
        temporary_completion = Path(temporary) / "completion.json"
        completion_result = recorder.run(
            [
                "limactl",
                "copy",
                "--backend=scp",
                f"{instance}:{remote_completion}",
                str(temporary_completion),
            ],
            label=f"copy agent attempt {attempt} completion",
            category="candidate_vm",
        )
        _require_success(completion_result, "agent_invocation")
        if temporary_completion.stat().st_size != completion_size:
            raise Inconclusive("agent_invocation", "agent completion changed during copy")
        _copy_bounded_into_evidence(
            temporary_completion,
            completion_path,
        )
    try:
        completion = _validate_completion(
            _read_bounded_json(
                completion_path,
                maximum_bytes=CONTROL_DOCUMENT_MAX_BYTES,
            )
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise Inconclusive("agent_invocation", f"agent completion cannot be read: {exc}") from exc
    _write_json(completion_path, completion)
    return completion_path, thread_id


def _assert_public_safe_candidate_manifest(manifest: Path) -> None:
    try:
        value = _read_bounded_json(
            manifest,
            maximum_bytes=TRANSFER_MANIFEST_MAX_BYTES,
        )
        encoded = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            sort_keys=True,
        ).encode("utf-8")
    except (OSError, RecursionError, ValueError, json.JSONDecodeError) as exc:
        raise Inconclusive("candidate_transfer", "candidate manifest is unreadable") from exc
    if not isinstance(value, dict) or not isinstance(value.get("files"), list):
        raise Inconclusive("candidate_transfer", "candidate manifest is invalid")
    labels = _public_safety_labels(encoded, check_host_paths=True)
    for record in value["files"]:
        relative = record.get("path") if isinstance(record, dict) else None
        if not isinstance(relative, str):
            raise Inconclusive("candidate_transfer", "candidate manifest is invalid")
        labels.update(
            _public_safety_labels(
                ("/" + relative).encode("utf-8", errors="surrogatepass"),
                check_host_paths=True,
            )
        )
    if labels:
        raise Inconclusive(
            "evidence_safety",
            "candidate manifest contains a non-public-safe path",
        )


def _export_candidate(
    recorder: Recorder,
    evidence: Path,
    instance: str,
    run_id: str,
    attempt: int,
) -> tuple[Path, Path]:
    candidate_directory = evidence / "candidate" / f"attempt-{attempt}"
    source_directory = candidate_directory / "source"
    candidate_directory.mkdir(parents=True)
    transfer_status = candidate_directory / "transfer-status.json"
    transfer_started_at = _timestamp()
    _write_json(
        transfer_status,
        {"attempt": attempt, "completed": False, "started_at": transfer_started_at},
    )
    remote_prefix = f"/var/tmp/{run_id}-attempt-{attempt}"
    export_script = (
        "sudo python3 /usr/local/lib/q1-l1/candidate_snapshot.py "
        f"--root \"$HOME/candidate\" --archive {remote_prefix}.tar "
        f"--manifest {remote_prefix}.manifest.json --report {remote_prefix}.snapshot.json"
    )
    exported = recorder.run(
        _limactl_shell(instance, "sh", "-lc", export_script),
        label=f"export candidate attempt {attempt}",
    )
    _require_success(exported, "candidate_transfer")
    with tempfile.TemporaryDirectory(prefix=f"{run_id}-transfer-") as temporary:
        temporary_path = Path(temporary)
        archive = temporary_path / "candidate.tar"
        manifest = temporary_path / "manifest.json"
        snapshot_report = temporary_path / "snapshot.json"
        for remote, local, label in (
            (f"{instance}:{remote_prefix}.tar", archive, "archive"),
            (f"{instance}:{remote_prefix}.manifest.json", manifest, "manifest"),
            (f"{instance}:{remote_prefix}.snapshot.json", snapshot_report, "snapshot report"),
        ):
            copied = recorder.run(
                ["limactl", "copy", "--backend=scp", remote, str(local)],
                label=f"copy candidate attempt {attempt} {label}",
            )
            _require_success(copied, "candidate_transfer")
        if snapshot_report.stat().st_size > CONTROL_DOCUMENT_MAX_BYTES:
            raise Inconclusive("candidate_transfer", "snapshot report exceeds control limit")
        try:
            snapshot = _read_json(snapshot_report)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise Inconclusive("candidate_transfer", "snapshot report is unreadable") from exc
        if (
            not isinstance(snapshot, dict)
            or set(snapshot)
            != {
                "archive",
                "candidate_uid",
                "manifest",
                "quiesced",
                "terminated_process_count",
            }
            or snapshot.get("archive") != f"{remote_prefix}.tar"
            or snapshot.get("manifest") != f"{remote_prefix}.manifest.json"
            or snapshot.get("quiesced") is not True
            or not isinstance(snapshot.get("candidate_uid"), int)
            or isinstance(snapshot.get("candidate_uid"), bool)
            or snapshot["candidate_uid"] <= 0
            or not isinstance(snapshot.get("terminated_process_count"), int)
            or isinstance(snapshot.get("terminated_process_count"), bool)
            or snapshot["terminated_process_count"] < 0
        ):
            raise Inconclusive("candidate_transfer", "snapshot report is invalid")
        _assert_public_safe_candidate_manifest(manifest)
        started_wall = _utc_now()
        started = time.monotonic()
        temporary_source = temporary_path / "verified-source"
        try:
            validated_manifest = extract_candidate(archive, manifest, temporary_source)
            retained_source_bytes = sum(
                int(record["size"]) for record in validated_manifest["files"]
            )
            _require_evidence_capacity(evidence, retained_source_bytes)
            extracted_manifest = extract_candidate(archive, manifest, source_directory)
        except (OSError, TransferError) as exc:
            raise Inconclusive("candidate_transfer", str(exc)) from exc
        if extracted_manifest != validated_manifest:
            raise Inconclusive("candidate_transfer", "candidate extraction was not reproducible")
        recorder.internal(
            label=f"verify candidate attempt {attempt} locally",
            started_wall=started_wall,
            started_monotonic=started,
            detail={"file_count": len(extracted_manifest["files"])},
        )
        manifest_path = candidate_directory / "manifest.json"
        _require_evidence_capacity(evidence, manifest.stat().st_size)
        shutil.copy2(manifest, manifest_path)
        if snapshot_report.stat().st_size > CONTROL_DOCUMENT_MAX_BYTES:
            raise Inconclusive("candidate_transfer", "snapshot report exceeds control limit")
        _require_evidence_capacity(evidence, snapshot_report.stat().st_size)
        shutil.copy2(snapshot_report, candidate_directory / "snapshot.json")
        archive_sha256 = _sha256(archive)
        manifest_sha256 = _sha256(manifest_path)
        evaluator_attempt = _evaluator_attempt_root(run_id, attempt)
        evaluator_root = _evaluator_run_root(run_id)
        create_script = (
            "import os,sys; root,attempt,tmp,first=sys.argv[1:]; "
            "assert first in {'0','1'} and os.path.isdir(root) and os.path.isdir(tmp); "
            "os.mkdir(attempt,0o700)"
        )
        created = recorder.run(
            _limactl_shell(
                EVALUATOR_INSTANCE,
                "/usr/bin/python3",
                "-B",
                "-I",
                "-c",
                create_script,
                evaluator_root,
                evaluator_attempt,
                f"{evaluator_root}/tmp",
                "1" if attempt == 1 else "0",
            ),
            label=f"create evaluator root for candidate attempt {attempt}",
        )
        _require_success(created, "candidate_transfer")
        remote_archive = f"{evaluator_attempt}/candidate.tar"
        remote_manifest = f"{evaluator_attempt}/manifest.json"
        for local, remote, label in (
            (archive, f"{EVALUATOR_INSTANCE}:{remote_archive}", "archive"),
            (manifest, f"{EVALUATOR_INSTANCE}:{remote_manifest}", "manifest"),
        ):
            copied = recorder.run(
                ["limactl", "copy", "--backend=scp", str(local), remote],
                label=f"transfer candidate attempt {attempt} {label} to evaluator",
            )
            _require_success(copied, "candidate_transfer")
        remote_hash_result = recorder.run(
            _limactl_shell(
                EVALUATOR_INSTANCE,
                "sha256sum",
                remote_archive,
                remote_manifest,
            ),
            label=f"hash evaluator candidate attempt {attempt} transfer",
        )
        _require_success(remote_hash_result, "candidate_transfer")
        try:
            remote_hashes = _sha256sum_output(
                (evidence / remote_hash_result.stdout_path).read_text(encoding="utf-8"),
                (remote_archive, remote_manifest),
            )
        except (OSError, ValueError) as exc:
            raise Inconclusive("candidate_transfer", "evaluator transfer hashes are invalid") from exc
        if (
            remote_hashes[remote_archive] != archive_sha256
            or remote_hashes[remote_manifest] != manifest_sha256
        ):
            raise Inconclusive("candidate_transfer", "evaluator transfer changed candidate bytes")
        _write_json(
            candidate_directory / "transfer.json",
            {
                "archive_sha256": archive_sha256,
                "evaluator_archive_sha256": remote_hashes[remote_archive],
                "evaluator_manifest_sha256": remote_hashes[remote_manifest],
                "manifest_sha256": manifest_sha256,
                "source_file_count": len(extracted_manifest["files"]),
            },
        )
        _write_json(
            transfer_status,
            {
                "attempt": attempt,
                "completed": True,
                "started_at": transfer_started_at,
            },
        )
    return manifest_path, source_directory


def _bootstrap_evaluator_candidate(
    recorder: Recorder,
    evidence: Path,
    run_id: str,
    attempt: int,
) -> str:
    evaluator_attempt = _evaluator_attempt_root(run_id, attempt)
    remote_archive = f"{evaluator_attempt}/candidate.tar"
    remote_manifest = f"{evaluator_attempt}/manifest.json"
    candidate_root = f"{evaluator_attempt}/candidate"
    commands = (
        (
            "extract transferred candidate",
            (
                "/usr/bin/python3",
                "-B",
                "-I",
                str(REPRODUCTION / "candidate_transfer.py"),
                "extract",
                "--archive",
                remote_archive,
                "--manifest",
                remote_manifest,
                "--root",
                candidate_root,
            ),
        ),
        ("create public directory", ("mkdir", "-p", f"{candidate_root}/public")),
        (
            "install public contract",
            ("cp", "-R", str(ROOT / "public" / "contract"), f"{candidate_root}/public/contract"),
        ),
        (
            "verify transferred candidate",
            (
                "/usr/bin/python3",
                "-B",
                "-I",
                str(REPRODUCTION / "candidate_transfer.py"),
                "verify",
                "--root",
                candidate_root,
                "--manifest",
                remote_manifest,
            ),
        ),
        (
            "create clean virtual environment",
            ("/usr/bin/python3.14", "-B", "-I", "-m", "venv", f"{candidate_root}/.venv"),
        ),
        (
            "install locked dependencies",
            (
                f"{candidate_root}/.venv/bin/python",
                "-B",
                "-I",
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-cache-dir",
                "--no-deps",
                "--requirement",
                f"{candidate_root}/public/contract/python-arm-requirements.v1.txt",
            ),
        ),
        (
            "check locked dependencies",
            (
                f"{candidate_root}/.venv/bin/python",
                "-B",
                "-I",
                "-m",
                "pip",
                "check",
            ),
        ),
    )
    records = []
    for label, command in commands:
        result = recorder.run(
            _limactl_shell(EVALUATOR_INSTANCE, *command),
            label=f"attempt {attempt} bootstrap: {label}",
        )
        records.append(
            {
                "command_sequence": result.sequence,
                "label": label,
                "passed": result.return_code == 0,
            }
        )
        if result.return_code != 0:
            _write_json(
                evidence / "gates" / f"attempt-{attempt}" / "bootstrap.json",
                {"passed": False, "steps": records},
            )
            raise Inconclusive("clean_bootstrap", f"clean bootstrap failed at {label}")
    _write_json(
        evidence / "gates" / f"attempt-{attempt}" / "bootstrap.json",
        {"passed": True, "steps": records},
    )
    return candidate_root


def _typing_gate(
    recorder: Recorder,
    evidence: Path,
    candidate_root: str,
    run_id: str,
    attempt: int,
) -> dict[str, Any]:
    evaluator_tmp = f"{_evaluator_run_root(run_id)}/tmp"
    direct = recorder.run(
        _limactl_shell(
            EVALUATOR_INSTANCE,
            "env",
            f"TMPDIR={evaluator_tmp}",
            *_trusted_module_argv("evaluator.isolated_command"),
            "--candidate-root",
            candidate_root,
            "--",
            "python3",
            "-m",
            "mypy",
            "--config-file",
            "public/contract/mypy.v1.ini",
            ".",
            workdir=str(ROOT),
        ),
        label=f"attempt {attempt} direct pinned typecheck",
    )
    breach = _command_breach(direct)
    wrapper_completed = False
    stderr_path = getattr(direct, "stderr_path", None)
    if isinstance(stderr_path, str):
        try:
            stderr_lines = (evidence / stderr_path).read_text(encoding="utf-8").splitlines()
            wrapper_completed = bool(
                stderr_lines and stderr_lines[-1] == ISOLATED_COMMAND_COMPLETION_MARKER
            )
        except (OSError, UnicodeDecodeError):
            wrapper_completed = False
    report = {
        "direct_command_sequence": direct.sequence,
        "infrastructure_failure": (
            breach is not None
            or direct.timed_out
            or direct.return_code == 125
            or not wrapper_completed
        ),
        "limit_breach": breach,
        "passed": direct.return_code == 0,
        "return_code": direct.return_code,
        "timed_out": direct.timed_out,
        "wrapper_completed": wrapper_completed,
    }
    _write_json(evidence / "gates" / f"attempt-{attempt}" / "typing.json", report)
    if breach is not None:
        raise Inconclusive("typing_gate", f"isolated typing command breached {breach}")
    if direct.timed_out:
        raise Inconclusive("typing_gate", "isolated typing command timed out")
    if direct.return_code == 125:
        raise Inconclusive("typing_gate", "isolated typing wrapper failed")
    if not wrapper_completed:
        raise Inconclusive(
            "typing_gate",
            "isolated typing transport did not return the trusted completion marker",
        )
    return report


def _validated_behavior_report(
    value: Any,
    *,
    expected_candidate_command: list[str],
) -> dict[str, Any]:
    fields = {
        "base_url",
        "candidate_service_command",
        "contract_version",
        "duration_ms",
        "evaluator_version",
        "failure_class",
        "infrastructure_failure",
        "layers",
        "limits",
        "passed",
        "service_command",
        "service_log_tail",
        "shutdowns",
        "started_at",
        "startup_error",
        "startup_failure_origin",
        "startup_return_code",
        "tests",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError("behavioral report has the wrong top-level fields")
    if (
        value.get("base_url") != "http://127.0.0.1:18766"
        or value.get("contract_version") != "1.0.0"
        or value.get("evaluator_version") != "0.1.0"
        or value.get("candidate_service_command") != expected_candidate_command
        or not isinstance(value.get("service_command"), str)
        or not value["service_command"]
        or not isinstance(value.get("service_log_tail"), str)
        or len(value["service_log_tail"]) > 8_192
        or not isinstance(value.get("passed"), bool)
        or not isinstance(value.get("infrastructure_failure"), bool)
        or not isinstance(value.get("duration_ms"), int)
        or isinstance(value.get("duration_ms"), bool)
        or value["duration_ms"] < 0
    ):
        raise ValueError("behavioral report identity or scalar fields are invalid")
    try:
        started_at = datetime.fromisoformat(value["started_at"])
    except (TypeError, ValueError) as exc:
        raise ValueError("behavioral report timestamp is invalid") from exc
    if started_at.tzinfo is None:
        raise ValueError("behavioral report timestamp lacks a UTC offset")
    expected_limits = {
        "request_timeout_seconds": 3.0,
        "shutdown_timeout_seconds": 1.5,
        "startup_timeout_seconds": 8.0,
        "suite_timeout_seconds": 45.0,
    }
    if value.get("limits") != expected_limits:
        raise ValueError("behavioral report limits do not match the approved suite")
    startup_error = value.get("startup_error")
    startup_origin = value.get("startup_failure_origin")
    startup_return_code = value.get("startup_return_code")
    if (
        startup_error is not None
        and (not isinstance(startup_error, str) or not startup_error)
    ) or startup_origin not in {None, "candidate", "evaluator", "isolation"} or (
        startup_return_code is not None
        and (
            not isinstance(startup_return_code, int)
            or isinstance(startup_return_code, bool)
        )
    ):
        raise ValueError("behavioral startup record is invalid")
    if (startup_error is None) != (startup_origin is None) or (
        startup_error is None and startup_return_code is not None
    ):
        raise ValueError("behavioral startup error and origin disagree")
    tests = value.get("tests")
    if not isinstance(tests, list):
        raise ValueError("behavioral tests are not an array")
    expected_by_name = dict(BEHAVIOR_TEST_LAYERS)
    observed_base_names: list[str] = []
    observed_layers: dict[str, dict[str, Any]] = {}
    infrastructure_failure = startup_origin in {"evaluator", "isolation"}
    controller_finalizer_seen = False
    for index, test in enumerate(tests):
        if not isinstance(test, dict) or set(test) != {
            "detail",
            "duration_ms",
            "failure_origin",
            "layer",
            "name",
            "passed",
        }:
            raise ValueError("behavioral test record has the wrong fields")
        name = test.get("name")
        layer = test.get("layer")
        passed = test.get("passed")
        detail = test.get("detail")
        origin = test.get("failure_origin")
        duration = test.get("duration_ms")
        if name == "controller_finalizer":
            if (
                controller_finalizer_seen
                or index != len(tests) - 1
                or layer != "cleanup"
                or passed is not False
            ):
                raise ValueError("behavioral controller-finalizer record is misplaced")
            controller_finalizer_seen = True
        elif (
            not isinstance(name, str)
            or name not in expected_by_name
            or layer != expected_by_name[name]
            or controller_finalizer_seen
        ):
            raise ValueError("behavioral test name or layer is invalid")
        else:
            observed_base_names.append(name)
        if (
            not isinstance(passed, bool)
            or not isinstance(duration, int)
            or isinstance(duration, bool)
            or duration < 0
            or origin not in {None, "candidate", "evaluator", "isolation"}
            or (detail is not None and (not isinstance(detail, str) or not detail))
            or (passed and (detail is not None or origin is not None))
            or (not passed and (detail is None or origin is None))
        ):
            raise ValueError("behavioral test result is invalid")
        layer_record = observed_layers.setdefault(cast(str, layer), {"passed": True, "tests": []})
        layer_record["tests"].append(name)
        if not passed:
            layer_record["passed"] = False
        if origin in {"evaluator", "isolation"}:
            infrastructure_failure = True
    expected_names = [name for name, _layer in BEHAVIOR_TEST_LAYERS]
    if startup_error is not None and tests:
        raise ValueError("behavioral startup failure cannot contain test records")
    if observed_base_names != expected_names[: len(observed_base_names)]:
        raise ValueError("behavioral tests are not the approved ordered prefix")
    if value.get("layers") != observed_layers:
        raise ValueError("behavioral layer summary disagrees with its test records")
    shutdowns = value.get("shutdowns")
    if not isinstance(shutdowns, list):
        raise ValueError("behavioral shutdowns are not an array")
    for shutdown in shutdowns:
        if not isinstance(shutdown, dict) or set(shutdown) != {
            "elapsed_seconds",
            "forced_kill",
            "graceful_requested",
            "return_code",
        }:
            raise ValueError("behavioral shutdown record has the wrong fields")
        elapsed = shutdown.get("elapsed_seconds")
        return_code = shutdown.get("return_code")
        if (
            not isinstance(shutdown.get("forced_kill"), bool)
            or not isinstance(shutdown.get("graceful_requested"), bool)
            or not isinstance(elapsed, (int, float))
            or isinstance(elapsed, bool)
            or not math.isfinite(elapsed)
            or elapsed < 0
            or (
                return_code is not None
                and (not isinstance(return_code, int) or isinstance(return_code, bool))
            )
        ):
            raise ValueError("behavioral shutdown record is invalid")
    passed = (
        startup_error is None
        and not controller_finalizer_seen
        and observed_base_names == expected_names
        and all(test["passed"] is True for test in tests)
    )
    if value["passed"] is not passed or value["infrastructure_failure"] is not infrastructure_failure:
        raise ValueError("behavioral report disposition fields are inconsistent")
    expected_failure_class = (
        None if passed else "isolation_failure" if infrastructure_failure else "candidate_failure"
    )
    if value.get("failure_class") != expected_failure_class:
        raise ValueError("behavioral report failure class is invalid")
    return cast(dict[str, Any], value)


def _behavior_gate(
    recorder: Recorder,
    evidence: Path,
    candidate_root: str,
    completion_path: Path,
    run_id: str,
    attempt: int,
) -> dict[str, Any]:
    evaluator_attempt = _evaluator_attempt_root(run_id, attempt)
    remote_completion = f"{evaluator_attempt}/completion.json"
    copied = recorder.run(
        [
            "limactl",
            "copy",
            "--backend=scp",
            str(completion_path),
            f"{EVALUATOR_INSTANCE}:{remote_completion}",
        ],
        label=f"transfer attempt {attempt} completion to evaluator",
    )
    _require_success(copied, "candidate_transfer")
    completion_hash_result = recorder.run(
        _limactl_shell(EVALUATOR_INSTANCE, "sha256sum", remote_completion),
        label=f"hash evaluator attempt {attempt} completion",
    )
    _require_success(completion_hash_result, "candidate_transfer")
    try:
        evaluator_completion_sha256 = _sha256sum_output(
            (evidence / completion_hash_result.stdout_path).read_text(encoding="utf-8"),
            (remote_completion,),
        )[remote_completion]
    except (OSError, ValueError) as exc:
        raise Inconclusive("candidate_transfer", "evaluator completion hash is invalid") from exc
    completion_sha256 = _sha256(completion_path)
    if evaluator_completion_sha256 != completion_sha256:
        raise Inconclusive("candidate_transfer", "evaluator completion bytes changed")
    transfer_path = evidence / "candidate" / f"attempt-{attempt}" / "transfer.json"
    transfer_value = _read_json(transfer_path)
    if not isinstance(transfer_value, dict):
        raise Inconclusive("candidate_transfer", "candidate transfer record is invalid")
    transfer_value.update(
        {
            "completion_sha256": completion_sha256,
            "evaluator_completion_sha256": evaluator_completion_sha256,
        }
    )
    _write_json(transfer_path, transfer_value)
    report_path = evidence / "gates" / f"attempt-{attempt}" / "behavior.json"
    remote_report = f"{evaluator_attempt}/behavior.json"
    result = recorder.run(
        _limactl_shell(
            EVALUATOR_INSTANCE,
            "env",
            f"TMPDIR={_evaluator_run_root(run_id)}/tmp",
            *_trusted_module_argv("evaluator.rerun"),
            "--candidate-root",
            candidate_root,
            "--candidate-completion",
            remote_completion,
            "--report",
            remote_report,
            workdir=str(ROOT),
        ),
        label=f"attempt {attempt} isolated behavioral gate",
    )
    breach = _command_breach(result)
    if breach is not None:
        raise Inconclusive(
            "behavioral_gate",
            f"behavioral gate breached {breach}",
        )
    report_size_result = recorder.run(
        _limactl_shell(EVALUATOR_INSTANCE, "stat", "-c", "%s", remote_report),
        label=f"measure attempt {attempt} behavioral report",
    )
    _require_success(report_size_result, "behavioral_gate")
    try:
        report_size = int(
            (evidence / report_size_result.stdout_path).read_text(encoding="utf-8").strip()
        )
    except (OSError, ValueError) as exc:
        raise Inconclusive("behavioral_gate", "behavioral report size is invalid") from exc
    if report_size < 0 or report_size > CONTROL_DOCUMENT_MAX_BYTES:
        raise Inconclusive("behavioral_gate", "behavioral report exceeds control limit")
    with tempfile.TemporaryDirectory(prefix=f"{run_id}-behavior-report-") as temporary:
        temporary_report = Path(temporary) / "behavior.json"
        report_copy = recorder.run(
            [
                "limactl",
                "copy",
                "--backend=scp",
                f"{EVALUATOR_INSTANCE}:{remote_report}",
                str(temporary_report),
            ],
            label=f"copy attempt {attempt} behavioral report",
        )
        _require_success(report_copy, "behavioral_gate")
        if temporary_report.stat().st_size != report_size:
            raise Inconclusive("behavioral_gate", "behavioral report changed during copy")
        _copy_bounded_into_evidence(temporary_report, report_path)
    report = _read_bounded_json(
        report_path,
        maximum_bytes=CONTROL_DOCUMENT_MAX_BYTES,
    )
    try:
        expected_command = _validate_completion(
            _read_bounded_json(
                completion_path,
                maximum_bytes=CONTROL_DOCUMENT_MAX_BYTES,
            )
        )["service_command"]
        report = _validated_behavior_report(
            report,
            expected_candidate_command=expected_command,
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise Inconclusive("behavioral_gate", "behavioral report is invalid") from exc
    if result.return_code not in {0, 1}:
        raise Inconclusive("behavioral_gate", f"behavioral runner exited {result.return_code}")
    if report["infrastructure_failure"] or report["failure_class"] == "isolation_failure":
        raise Inconclusive("behavioral_gate", "isolated runtime reported an infrastructure failure")
    if (result.return_code == 0) != report["passed"]:
        raise Inconclusive("behavioral_gate", "behavioral exit code and report disagree")
    return cast(dict[str, Any], report)


def _mark_attempt(state: dict[str, Any], key: str, attempt: int) -> None:
    attempts = state.setdefault(key, [])
    if not isinstance(attempts, list) or any(
        not isinstance(item, int) or isinstance(item, bool) for item in attempts
    ):
        raise Inconclusive("orchestration", f"invalid {key} state")
    if attempt in attempts:
        raise Inconclusive("orchestration", f"attempt {attempt} reached {key} twice")
    attempts.append(attempt)


def _evaluate_attempt(
    recorder: Recorder,
    evidence: Path,
    state: dict[str, Any],
    instance: str,
    run_id: str,
    attempt: int,
    completion_path: Path,
) -> dict[str, Any]:
    _mark_attempt(state, "transfer_attempts_started", attempt)
    manifest_path, _source = _export_candidate(
        recorder, evidence, instance, run_id, attempt
    )
    _mark_attempt(state, "transferred_attempts", attempt)
    identity = _candidate_identity(manifest_path, completion_path)
    _write_json(evidence / "candidate" / f"attempt-{attempt}" / "identity.json", identity)
    _mark_attempt(state, "identified_attempts", attempt)
    _mark_attempt(state, "bootstrap_attempts", attempt)
    candidate_root = _bootstrap_evaluator_candidate(recorder, evidence, run_id, attempt)
    _mark_attempt(state, "typing_attempts", attempt)
    typing = _typing_gate(recorder, evidence, candidate_root, run_id, attempt)
    _mark_attempt(state, "behavior_attempts", attempt)
    behavior = _behavior_gate(
        recorder, evidence, candidate_root, completion_path, run_id, attempt
    )
    unchanged = recorder.run(
        _limactl_shell(
            EVALUATOR_INSTANCE,
            "/usr/bin/python3",
            "-B",
            "-I",
            str(REPRODUCTION / "candidate_transfer.py"),
            "verify",
            "--root",
            candidate_root,
            "--manifest",
            f"{_evaluator_attempt_root(run_id, attempt)}/manifest.json",
        ),
        label=f"attempt {attempt} verify isolated candidate remained read-only",
    )
    _require_success(unchanged, "isolation_integrity")
    summary = {
        "attempt": attempt,
        "behavior_passed": behavior.get("passed") is True,
        "bootstrap_passed": True,
        "candidate_identity_sha256": identity["candidate_identity_sha256"],
        "manifest_path": _relative(manifest_path, evidence),
        "manifest_sha256": _sha256(manifest_path),
        "passed": typing["passed"] and behavior.get("passed") is True,
        "service_command": identity["service_command"],
        "source_unchanged_after_gates": True,
        "typing_passed": typing["passed"],
    }
    _write_json(evidence / "gates" / f"attempt-{attempt}" / "summary.json", summary)
    _mark_attempt(state, "evaluated_attempts", attempt)
    return summary


def _failure_feedback(evidence: Path, attempt: int) -> dict[str, Any]:
    failures = []
    typing = _read_json(evidence / "gates" / f"attempt-{attempt}" / "typing.json")
    if typing.get("passed") is not True:
        for key in ("direct_command_sequence",):
            sequence = typing[key]
            prefix = f"{sequence:03d}-"
            stdout = next((evidence / "logs").glob(f"{prefix}*.stdout"))
            stderr = next((evidence / "logs").glob(f"{prefix}*.stderr"))
            failures.append(
                {
                    "gate": "typing",
                    "stderr": stderr.read_text(encoding="utf-8"),
                    "stdout": stdout.read_text(encoding="utf-8"),
                }
            )
    behavior = _read_json(evidence / "gates" / f"attempt-{attempt}" / "behavior.json")
    if behavior.get("passed") is not True:
        failures.append(
            {
                "failed_tests": [
                    test for test in behavior.get("tests", []) if test.get("passed") is not True
                ],
                "gate": "behavior",
                "service_log_tail": behavior.get("service_log_tail"),
                "startup_error": behavior.get("startup_error"),
            }
        )
    return {"attempt": attempt, "failures": failures}


def _remediation_prompt(feedback: dict[str, Any]) -> str:
    template = (REPRODUCTION / "agent-remediation-prompt.md").read_text(encoding="utf-8")
    marker = "{{FEEDBACK_JSON}}"
    if template.count(marker) != 1:
        raise Inconclusive("remediation", "remediation prompt marker is invalid")
    return template.replace(marker, json.dumps(feedback, indent=2, sort_keys=True))


def _remaining_seconds(deadline_monotonic: float) -> float:
    return max(0.001, deadline_monotonic - time.monotonic())


def _listed_instances(
    recorder: Recorder,
    *,
    label: str,
    deadline_monotonic: float | None = None,
) -> tuple[set[str] | None, str | None]:
    result = recorder.run(
        ["limactl", "list", "--json"],
        label=label,
        timeout_seconds=(
            _remaining_seconds(deadline_monotonic)
            if deadline_monotonic is not None
            else None
        ),
        deadline_reserve_seconds=0 if deadline_monotonic is not None else CLEANUP_TIMEOUT_SECONDS,
        stdout_transform=_allowlisted_lima_names,
    )
    if result.return_code != 0:
        return None, f"{label} exited {result.return_code}"
    names: set[str] = set()
    try:
        for line in (recorder.evidence / result.stdout_path).read_text(
            encoding="utf-8"
        ).splitlines():
            value = json.loads(line)
            if not isinstance(value, dict) or not isinstance(value.get("name"), str):
                raise ValueError("instance record has no name")
            names.add(value["name"])
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return None, f"{label} returned invalid JSON: {exc}"
    return names, None


def _cleanup_candidate(
    recorder: Recorder,
    instance: str,
    login_attempted: bool,
    cleanup_deadline_monotonic: float | None = None,
    verification: dict[str, bool | float] | None = None,
) -> list[str]:
    cleanup_deadline_monotonic = cleanup_deadline_monotonic or (
        time.monotonic() + CLEANUP_TIMEOUT_SECONDS
    )
    failures = []
    inspection_started_monotonic = time.monotonic()
    names, error = _listed_instances(
        recorder,
        label="inspect candidate VM before teardown",
        deadline_monotonic=cleanup_deadline_monotonic,
    )
    if error is not None or names is None:
        failures.append(error or "candidate VM inspection failed")
    elif instance in names and verification is not None:
        verification["last_verified_present_monotonic"] = (
            inspection_started_monotonic
        )
    known_present = names is None or instance in names
    if known_present and login_attempted:
        logout = recorder.run(
            _limactl_shell(instance, "codex", "logout"),
            label="remove candidate Codex authentication",
            timeout_seconds=_remaining_seconds(cleanup_deadline_monotonic),
            deadline_reserve_seconds=0,
        )
        logout_breach = _command_breach(logout)
        if logout_breach is not None:
            failures.append(f"codex logout breached {logout_breach}")
        elif logout.return_code != 0:
            failures.append(f"codex logout exited {logout.return_code}")
    if known_present:
        deleted = recorder.run(
            ["limactl", "delete", "--force", instance],
            label="delete candidate VM",
            timeout_seconds=_remaining_seconds(cleanup_deadline_monotonic),
            deadline_reserve_seconds=0,
        )
        deletion_breach = _command_breach(deleted)
        if deletion_breach is not None:
            failures.append(f"candidate VM deletion breached {deletion_breach}")
        elif deleted.return_code != 0:
            failures.append(f"candidate VM deletion exited {deleted.return_code}")
    remaining, error = _listed_instances(
        recorder,
        label="verify candidate VM teardown",
        deadline_monotonic=cleanup_deadline_monotonic,
    )
    if error is not None or remaining is None:
        failures.append(error or "candidate VM teardown verification failed")
        if verification is not None:
            verification["absent"] = False
    elif instance in remaining:
        failures.append("candidate VM still exists after teardown")
        if verification is not None:
            verification["absent"] = False
    elif verification is not None:
        verification["absent"] = True
    return failures


def _cleanup_evaluator(
    recorder: Recorder,
    run_id: str,
    cleanup_deadline_monotonic: float | None = None,
) -> list[str]:
    cleanup_deadline_monotonic = cleanup_deadline_monotonic or (
        time.monotonic() + CLEANUP_TIMEOUT_SECONDS
    )
    if RUN_ID_PATTERN.fullmatch(run_id) is None:
        return ["refused evaluator cleanup for invalid run ID"]
    run_root = _evaluator_run_root(run_id)
    removed = recorder.run(
        _limactl_shell(EVALUATOR_INSTANCE, "sudo", "rm", "-rf", run_root),
        label="remove run-scoped evaluator artifacts",
        timeout_seconds=_remaining_seconds(cleanup_deadline_monotonic),
        deadline_reserve_seconds=0,
    )
    removal_breach = _command_breach(removed)
    if removal_breach is not None:
        return [f"evaluator artifact removal breached {removal_breach}"]
    if removed.return_code != 0:
        return [f"evaluator artifact removal exited {removed.return_code}"]
    verified = recorder.run(
        _evaluator_orphan_probe_argv(
            run_root=run_root,
            probe_path=recorder.evidence
            / "authorities"
            / "reproduction"
            / "evaluator_residue_probe.py",
        ),
        label="verify run-scoped evaluator cleanup",
        timeout_seconds=_remaining_seconds(cleanup_deadline_monotonic),
        deadline_reserve_seconds=0,
    )
    verification_breach = _command_breach(verified)
    if verification_breach is not None:
        return [f"evaluator cleanup verification breached {verification_breach}"]
    return [] if verified.return_code == 0 else ["evaluator artifacts remain after cleanup"]


def _command_records(evidence: Path) -> list[dict[str, Any]]:
    records = []
    path = evidence / "commands.jsonl"
    if not path.is_file():
        return records
    for line in path.read_text(encoding="utf-8").splitlines():
        value = json.loads(line)
        if isinstance(value, dict):
            records.append(value)
    return records


def _accounting(
    evidence: Path,
    *,
    run_started_at: str,
    finished_at: str,
    review_requested_at: str | None = None,
    review_received_at: str | None = None,
    human_active_minutes: float | str = "unknown",
    candidate_vm_provisioning_started_at: str | None = None,
    candidate_vm_observed_existing_at: str | None = None,
    candidate_vm_teardown_finished_at: str | None = None,
    candidate_vm_teardown_verified: bool = False,
    candidate_vm_observed_interval_lower_bound_seconds: float | str | None = None,
    finalization_elapsed_lower_bound_seconds: float | str = 0.0,
    execute_elapsed_lower_bound_seconds: float | str = "unknown",
) -> dict[str, Any]:
    records = _command_records(evidence)
    agent_usage = []
    for path in sorted((evidence / "agent").glob("attempt-*/usage.json")):
        agent_usage.append(_read_json(path))
    trusted_machine_seconds = sum(
        float(record.get("duration_seconds", 0))
        for record in records
        if "trusted_machine" in record.get("resources", [])
    )
    evaluator_seconds = sum(
        float(record.get("duration_seconds", 0))
        for record in records
        if "evaluator" in record.get("resources", [])
    )
    agent_seconds = sum(float(item["duration_seconds"]) for item in agent_usage)
    started = datetime.fromisoformat(run_started_at)
    finished = datetime.fromisoformat(finished_at)
    review_wait: float | str = "unknown"
    if review_requested_at is not None and review_received_at is not None:
        review_wait = (
            datetime.fromisoformat(review_received_at)
            - datetime.fromisoformat(review_requested_at)
        ).total_seconds()
    candidate_lower_bound: float | str = "unknown"
    candidate_right_censored: bool | str = "unknown"
    if candidate_vm_observed_existing_at is not None:
        if (
            isinstance(candidate_vm_observed_interval_lower_bound_seconds, (int, float))
            and not isinstance(candidate_vm_observed_interval_lower_bound_seconds, bool)
            and math.isfinite(candidate_vm_observed_interval_lower_bound_seconds)
            and candidate_vm_observed_interval_lower_bound_seconds >= 0
        ):
            candidate_lower_bound = float(
                candidate_vm_observed_interval_lower_bound_seconds
            )
        candidate_right_censored = not (
            candidate_vm_teardown_verified
            and candidate_vm_teardown_finished_at is not None
        )
    return {
        "agent": {
            "invocations": agent_usage,
            "monetary_cost": "unknown",
            "total_elapsed_seconds": agent_seconds,
        },
        "candidate_vm": {
            "lifetime_seconds": "unknown",
            "monetary_cost": "unknown",
            "observed_existing_at": candidate_vm_observed_existing_at,
            "observed_interval_lower_bound_seconds": candidate_lower_bound,
            "provisioning_started_at": candidate_vm_provisioning_started_at,
            "right_censored": candidate_right_censored,
            "teardown_finished_at": candidate_vm_teardown_finished_at,
            "teardown_verified": candidate_vm_teardown_verified,
        },
        "evaluator": {
            "monetary_cost": "unknown",
            "standing_provisioning_and_idle": "excluded",
            "workload_seconds": evaluator_seconds,
        },
        "human": {
            "active_minutes": human_active_minutes,
            "monetary_cost": "unknown",
            "review_wait_upper_bound_seconds": review_wait,
        },
        "overlap": {
            "nonexclusive": True,
            "rule": (
                "Agent, candidate-VM, and evaluator intervals overlap trusted-machine "
                "and wall intervals; no category total may be summed into cost or latency."
            ),
        },
        "trusted_machine": {
            "coverage": (
                "Execute and finalization elapsed values are monotonic lower bounds ending "
                "before their containing artifacts are written. Command records are completed "
                "scoped intervals. Pending and terminal index scan-and-hash durations are in "
                "their indexes; serialization, durable write, projection, and final verification "
                "tails are unknown."
            ),
            "artifact_self_recording_tail_seconds": "unknown",
            "execute_elapsed_lower_bound_seconds": execute_elapsed_lower_bound_seconds,
            "execute_recorded_active_seconds": trusted_machine_seconds,
            "finalization_elapsed_lower_bound_seconds": (
                finalization_elapsed_lower_bound_seconds
            ),
            "monetary_cost": "unknown",
            "pending_index_scan_hash_elapsed_seconds": (
                "evidence-index.json:inventory_scan_hash_elapsed_seconds"
            ),
        },
        "wall": {
            "elapsed_lower_bound_seconds": (finished - started).total_seconds(),
            "post_cutoff_tail_seconds": "unknown",
            "recorded_cutoff_at": finished_at,
            "review_received_at": review_received_at,
            "review_requested_at": review_requested_at,
            "run_started_at": run_started_at,
        },
    }


def _unavailable(state: dict[str, Any]) -> list[dict[str, str]]:
    unavailable = []
    for item in state.get("missing_required_evidence", []):
        unavailable.append(
            {
                "observation": item,
                "reason": "required evidence was missing or failed integrity verification",
            }
        )
    if not state.get("evaluator_validated"):
        unavailable.append(
            {
                "observation": "validated evaluator and isolated runtime",
                "reason": "execution stopped before evaluator validation completed",
            }
        )
    if state.get("completed_attempts", 0) == 0:
        unavailable.extend(
            [
                {
                    "observation": "completed implementation-agent usage",
                    "reason": "no implementation attempt declared completion",
                },
                {
                    "observation": "candidate source manifest and settlement gates",
                    "reason": "no implementation attempt declared completion",
                },
            ]
        )
    if state.get("review_received_at") is not None:
        pass
    elif state["status"] != "PendingHumanReview":
        unavailable.append(
            {
                "observation": "human source-review attention and attestation",
                "reason": "the run did not reach the human source-review gate",
            }
        )
    else:
        unavailable.append(
            {
                "observation": "human source-review attention and attestation",
                "reason": "pending explicit human review",
            }
        )
    unavailable.extend(
        [
            {
                "observation": "agent monetary charge",
                "reason": "codex exec JSONL reports usage but no charge",
            },
            {
                "observation": "agent cache-write token usage",
                "reason": "pinned codex exec JSONL does not report cache-write tokens",
            },
            {
                "observation": "trusted-machine monetary cost",
                "reason": "the trusted host exposes no monetary meter",
            },
            {
                "observation": "candidate-VM monetary cost",
                "reason": "the candidate Lima instance exposes no monetary meter",
            },
            {
                "observation": "evaluator-workload monetary cost",
                "reason": "the pre-existing evaluator exposes no workload monetary meter",
            },
            {
                "observation": "human-review monetary cost",
                "reason": "human active minutes do not provide a monetary rate",
            },
            {
                "observation": "immutable model backend revision",
                "reason": "the requested gpt-5.6-luna identifier is not an immutable backend snapshot",
            },
        ]
    )
    return unavailable


def _normalize_host_text(value: str) -> str:
    normalized = value
    for path, replacement in _host_path_replacements():
        normalized = normalized.replace(path, replacement)
    return normalized


def _host_path_replacements() -> tuple[tuple[str, str], ...]:
    replacements: dict[str, str] = {}
    for replacement, paths in (
        (
            REDACTED_HOST_REPOSITORY,
            (str(REPOSITORY_ROOT), str(REPOSITORY_ROOT.resolve())),
        ),
        (REDACTED_HOST_HOME, (str(HOST_HOME), f"/home/{HOST_HOME.name}")),
        (
            REDACTED_HOST_TEMP,
            (tempfile.gettempdir(), str(Path(tempfile.gettempdir()).resolve())),
        ),
    ):
        for path in paths:
            if path:
                replacements.setdefault(path, replacement)
    return tuple(sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True))


def _host_path_redaction_is_identity_preserving(relative: str) -> bool:
    parts = PurePosixPath(relative).parts
    return bool(
        relative
        in {
            "accounting.json",
            "boundary-validation.json",
            "candidate-environment.json",
            "commands.jsonl",
            "dispatch-validation.json",
            "evaluator-validation.json",
            "isolation-validation.json",
            "redactions.json",
            "unavailable.json",
        }
        or parts[:1] == ("logs",)
    )


def _public_safety_redact(
    evidence: Path,
    result_path: Path,
    protected_values: Sequence[tuple[str, str]],
    *,
    deadline_guard: Callable[[], None] | None = None,
) -> list[dict[str, Any]]:
    targets = [path for path in evidence.rglob("*") if path.is_file() or path.is_symlink()]
    if result_path.exists() or result_path.is_symlink():
        targets.append(result_path)
    records: list[dict[str, Any]] = []
    for path in targets:
        if path.is_symlink() or not path.is_file():
            raise Inconclusive("evidence_safety", "evidence contains a symbolic link")
        relative = (
            _relative(path, evidence) if path != result_path else result_path.name
        )
        original = _read_regular_bytes_preserving_mode(path)
        sanitized = original
        for label, value in protected_values:
            needle = value.encode("utf-8")
            if not needle:
                continue
            count = sanitized.count(needle)
            if count:
                sanitized = sanitized.replace(needle, f"[REDACTED:{label}]".encode("ascii"))
                records.append(
                    {
                        "count": count,
                        "item": label,
                        "path": relative,
                        "reason": "secret control input is not evidence",
                    }
                )
        for label, pattern in PUBLIC_SECRET_PATTERNS:
            sanitized, count = pattern.subn(f"[REDACTED:{label}]".encode("ascii"), sanitized)
            if count:
                records.append(
                    {
                        "count": count,
                        "item": label,
                        "path": relative,
                        "reason": "credential-shaped bytes are not public-safe evidence",
                    }
                )
        for host_path, replacement in _host_path_replacements():
            needle = host_path.encode("utf-8")
            count = sanitized.count(needle)
            if count:
                sanitized = sanitized.replace(needle, replacement.encode("ascii"))
                records.append(
                    {
                        "count": count,
                        "item": replacement.strip("[]"),
                        "path": relative,
                        "reason": "host-local paths are normalized in public evidence",
                    }
                )
        if sanitized != original:
            target_evidence = _evidence_generation_for(path)
            if target_evidence is not None:
                _require_evidence_capacity(
                    target_evidence,
                    len(sanitized),
                    replacing=path,
                    reserve_closure=False,
                )
            if deadline_guard is not None:
                deadline_guard()
            _atomic_write(path, sanitized)
    return records


def _redactions_require_inconclusive(records: Sequence[dict[str, Any]]) -> bool:
    for record in records:
        item = record.get("item")
        relative = record.get("path")
        if not isinstance(item, str) or not isinstance(relative, str):
            return True
        if not item.startswith("HOST_"):
            return True
        if not _host_path_redaction_is_identity_preserving(relative):
            return True
    return False


def _redaction_inconclusive_reason(
    records: Sequence[dict[str, Any]],
) -> str | None:
    if not _redactions_require_inconclusive(records):
        return None
    return "public-safety redaction changed identity-bearing evidence"


def _public_safety_labels(data: bytes, *, check_host_paths: bool) -> set[str]:
    labels = {label for label, pattern in PUBLIC_SECRET_PATTERNS if pattern.search(data)}
    if check_host_paths:
        for path, replacement in _host_path_replacements():
            if path.encode("utf-8") in data:
                labels.add(replacement.strip("[]"))
    return labels


def _assert_public_safe_terminal(evidence: Path, result_path: Path) -> None:
    targets = [path for path in evidence.rglob("*") if path.is_file() or path.is_symlink()]
    targets.append(result_path)
    for path in targets:
        if path.is_symlink() or not path.is_file():
            raise ValueError("terminal evidence contains a non-regular file")
        relative = _relative(path, evidence) if path != result_path else result_path.name
        path_labels = _public_safety_labels(
            relative.encode("utf-8", errors="surrogatepass"),
            check_host_paths=True,
        )
        if path_labels:
            raise ValueError(
                f"terminal evidence has an unsafe path: {','.join(sorted(path_labels))}"
            )
        labels = _public_safety_labels(
            _read_regular_bytes_preserving_mode(path),
            check_host_paths=True,
        )
        if labels:
            raise ValueError(
                f"terminal evidence is not public-safe at {relative}: {','.join(sorted(labels))}"
            )


def _render_result(state: dict[str, Any]) -> str:
    status = state["status"]
    disposition = {
        "Accepted": "Accepted (Pass)",
        "Rejected": "Rejected (Fail)",
        "Inconclusive": "Inconclusive",
        "PendingHumanReview": "Pending human source review",
    }[status]
    effect = {
        "Accepted": (
            "Q1 gains one configuration-specific cost-to-accepted-completion "
            "observation. It does not establish a distribution or authorize a next loop."
        ),
        "Rejected": (
            "Q1 gains a configuration-specific cost-to-rejection observation, not a "
            "cost-to-accepted-completion observation. It does not authorize a next loop."
        ),
        "Inconclusive": (
            "Q1 gains the recorded cost and failure evidence, but no valid "
            "cost-to-accepted-completion observation. It does not authorize a next loop."
        ),
        "PendingHumanReview": (
            "Q1 gains the non-human cost observation, but accepted-completion cost remains "
            "pending explicit human source review."
        ),
    }[status]
    raw_summary = state.get("final_gate_summary")
    if isinstance(raw_summary, dict):
        gate_summary = {
            key: raw_summary.get(key)
            for key in (
                "attempt",
                "behavior_passed",
                "bootstrap_passed",
                "candidate_identity_sha256",
                "source_unchanged_after_gates",
                "typing_passed",
            )
        }
    else:
        gate_summary = "unavailable"
    summary_literal = "    " + json.dumps(gate_summary, ensure_ascii=True, sort_keys=True)
    reason_literal = "    " + json.dumps(
        str(state.get("disposition_reason", "")), ensure_ascii=True
    )
    return f"""# {ACTIVE_LOOP.loop_id} result — contract reproduction

## Observed evidence

- Run: `{state['run_id']}`
- Executable contract commit: `{state['contract_commit']}`
- Candidate attempts completed: {state.get('completed_attempts', 0)}
- Evidence: [`evidence/{state['run_id']}`](evidence/{state['run_id']})
- Separate cost and latency ledger: [`evidence/{state['run_id']}/accounting.json`](evidence/{state['run_id']}/accounting.json)

Final non-human gates:

{summary_literal}

## Disposition

**{disposition}.**

Reason:

{reason_literal}

## Deviations and unknowns

See `evidence/{state['run_id']}/unavailable.json`. Missing required evidence is not recorded as zero and forces `Inconclusive`; explicitly unavailable cost observations remain unknown.

## Effect on Q1

{effect}

## Possible next loops

None authorized. The terminal evidence returns to human review for a broad next-step decision.

## Promotion candidate

None. Loop success and promotion are separate human decisions.
"""


def _evidence_index(
    evidence: Path,
    *,
    index_name: str = "evidence-index.json",
    version: int = 3,
) -> dict[str, Any]:
    generation_started = time.monotonic()
    if PurePosixPath(index_name).parts != (index_name,):
        raise ValueError("evidence index name must be a root filename")
    entries = []
    for path in sorted(evidence.rglob("*")):
        if path == evidence / index_name:
            continue
        if path.is_symlink():
            raise ValueError(f"evidence contains a symbolic link: {_relative(path, evidence)}")
        if path.is_file():
            relative = _relative(path, evidence)
            labels = _public_safety_labels(
                relative.encode("utf-8", errors="surrogatepass"),
                check_host_paths=True,
            )
            if labels:
                raise ValueError(
                    f"evidence path is not public-safe: {','.join(sorted(labels))}"
                )
            entries.append(
                {
                    "path": relative,
                    "sha256": _sha256(path),
                    "size": path.stat().st_size,
                }
            )
    return {
        "artifact_self_recording_tail_seconds": "unknown",
        "files": entries,
        "generated_at": _timestamp(),
        "inventory_scan_hash_elapsed_seconds": time.monotonic() - generation_started,
        "version": version,
    }


def _required_evidence(evidence: Path, state: dict[str, Any]) -> list[Path]:
    required = [
        evidence / "accounting.json",
        evidence / "commands.jsonl",
        evidence / "pending-RESULT.md",
        evidence / "redactions.json",
        evidence / "run.json",
        evidence / "unavailable.json",
    ]
    authority_names = (
        "QUESTION.md",
        "LOOP.md",
        "candidate-lima.yaml",
        "candidate-apt-packages.txt",
        "candidate-codex-config.toml",
        "candidate-codex-requirements.toml",
        "agent-completion.schema.json",
        "agent-initial-prompt.md",
        "agent-remediation-prompt.md",
        "HUMAN_REVIEW.md",
        "prepare-candidate-lima.sh",
        "bootstrap-candidate-lima.sh",
        "candidate_boundary_probe.py",
        "candidate_snapshot.py",
        "candidate_transfer.py",
        "verify_candidate_boundary.py",
        "Makefile",
    )
    required.extend(evidence / "authorities" / name for name in authority_names)
    if LOOP_ROOT != ROOT:
        required.extend(
            (
                evidence / "context.json",
                evidence / "authorities" / "workload" / "LOOP.md",
            )
        )
        required.extend(
            evidence / "authorities" / "loop" / path.name
            for path in LOOP_AUTHORITY_PATHS
        )
    if LOOP_CANDIDATE_QUALIFICATION_ROOT is not None:
        setup_root = evidence / "setup" / "candidate-boundary-qualification"
        required.extend(
            setup_root / name
            for name in (
                "boundary-validation.json",
                "commands.jsonl",
                "redactions.json",
                "setup-accounting.json",
                QUALIFICATION_REPORT_NAME,
                QUALIFICATION_INDEX_NAME,
                QUALIFICATION_COMPLETION_NAME,
            )
        )
        required.extend(
            path
            for path in setup_root.rglob("*")
            if path.is_file() and not path.is_symlink()
        )
    required.extend(
        evidence / "authorities" / "public-contract" / path.relative_to(ROOT / "public" / "contract")
        for path in (ROOT / "public" / "contract").rglob("*")
        if path.is_file()
    )
    for source_root, name in (
        (REPRODUCTION, "reproduction"),
        (ROOT / "evaluator", "evaluator"),
    ):
        required.extend(
            evidence / "authorities" / name / path.relative_to(source_root)
            for path in source_root.rglob("*")
            if path.is_file() and "__pycache__" not in path.relative_to(source_root).parts
        )
    if state.get("evaluator_validated"):
        required.extend(
            (
                evidence / "dispatch-validation.json",
                evidence / "evaluator-boundary-validation.json",
                evidence / "evaluator-environment.json",
                evidence / "evaluator-validation.json",
                evidence / "evaluator-residue-validation.json",
                evidence / "isolation-validation.json",
            )
        )
    if state.get("candidate_boundary_validated"):
        required.extend(
            (evidence / "boundary-validation.json", evidence / "candidate-environment.json")
        )
    for attempt in range(1, int(state.get("agent_attempts_invoked", 0)) + 1):
        agent = evidence / "agent" / f"attempt-{attempt}"
        required.extend(
            (
                agent / "events.jsonl",
                agent / "prompt.md",
                agent / "stderr.txt",
                agent / "usage.json",
            )
        )
        if attempt == 2:
            required.append(agent / "feedback.json")
    for attempt in range(1, int(state.get("completed_attempts", 0)) + 1):
        required.append(evidence / "agent" / f"attempt-{attempt}" / "completion.json")
    for attempt in state.get("transfer_attempts_started", []):
        required.append(
            evidence / "candidate" / f"attempt-{attempt}" / "transfer-status.json"
        )
    for attempt in state.get("transferred_attempts", []):
        required.extend(
            (
                evidence / "candidate" / f"attempt-{attempt}" / "manifest.json",
                evidence / "candidate" / f"attempt-{attempt}" / "snapshot.json",
                evidence / "candidate" / f"attempt-{attempt}" / "transfer.json",
            )
        )
    for attempt in state.get("identified_attempts", []):
        required.append(evidence / "candidate" / f"attempt-{attempt}" / "identity.json")
    for attempt in state.get("bootstrap_attempts", []):
        required.append(evidence / "gates" / f"attempt-{attempt}" / "bootstrap.json")
    for attempt in state.get("typing_attempts", []):
        required.append(evidence / "gates" / f"attempt-{attempt}" / "typing.json")
    for attempt in state.get("behavior_attempts", []):
        required.append(evidence / "gates" / f"attempt-{attempt}" / "behavior.json")
    for attempt in state.get("evaluated_attempts", []):
        required.append(evidence / "gates" / f"attempt-{attempt}" / "summary.json")
    return required


def _mark_inconclusive(state: dict[str, Any], stage: str, detail: str) -> None:
    normalized = _normalize_host_text(detail)
    history = state.setdefault("failure_history", [])
    record = {"detail": normalized, "stage": stage}
    if isinstance(history, list) and record not in history:
        history.append(record)
    previous = state.get("disposition_reason")
    state["status"] = "Inconclusive"
    state["failure_stage"] = stage
    if isinstance(previous, str) and previous and previous != normalized:
        state["disposition_reason"] = f"{previous}; {normalized}"
    else:
        state["disposition_reason"] = normalized


def _api_key_omissions(state: dict[str, Any]) -> list[dict[str, str]]:
    if state.get("login_attempted") is not True:
        return []
    return [
        {
            "item": "OpenAI API key",
            "reason": (
                "candidate login was attempted with secret stdin and the control "
                "input was never captured"
            ),
        }
    ]


def _require_execution_deadline_open(
    *,
    final_phase_deadline: float,
    automated_phase_deadline: float,
) -> None:
    now = time.monotonic()
    if now >= final_phase_deadline or now >= automated_phase_deadline:
        raise ExecuteHardDeadline()


def _write_run_outputs(
    evidence: Path,
    state: dict[str, Any],
    *,
    recorder: Recorder,
    protected_values: Sequence[tuple[str, str]] = (),
    run_started_monotonic: float | None = None,
    final_phase_deadline: float = math.inf,
    automated_phase_deadline: float = math.inf,
) -> None:
    closure_started_wall = _utc_now()
    closure_started_monotonic = time.monotonic()

    def require_open() -> None:
        _require_execution_deadline_open(
            final_phase_deadline=final_phase_deadline,
            automated_phase_deadline=automated_phase_deadline,
        )

    def write_control_outputs() -> None:
        reserve_terminal = state.get("status") == "PendingHumanReview"
        finished_at = (
            state.get("review_received_at")
            or state.get("automated_recorded_cutoff_at")
            or _timestamp()
        )
        accounting = _accounting(
            evidence,
            run_started_at=state["run_started_at"],
            finished_at=finished_at,
            review_requested_at=state.get("review_requested_at"),
            review_received_at=state.get("review_received_at"),
            human_active_minutes=state.get("human_active_minutes", "unknown"),
            candidate_vm_provisioning_started_at=state.get(
                "candidate_vm_provisioning_started_at"
            ),
            candidate_vm_observed_existing_at=state.get(
                "candidate_vm_observed_existing_at"
            ),
            candidate_vm_teardown_finished_at=state.get(
                "candidate_vm_teardown_finished_at"
            ),
            candidate_vm_teardown_verified=state.get(
                "candidate_vm_teardown_verified", False
            )
            is True,
            candidate_vm_observed_interval_lower_bound_seconds=state.get(
                "candidate_vm_observed_interval_lower_bound_seconds"
            ),
            finalization_elapsed_lower_bound_seconds=state.get(
                "finalization_elapsed_lower_bound_seconds", 0.0
            ),
            execute_elapsed_lower_bound_seconds=state.get(
                "execute_elapsed_lower_bound_seconds", "unknown"
            ),
        )
        require_open()
        _write_json(
            evidence / "accounting.json",
            accounting,
            reserve_closure=reserve_terminal,
            deadline_guard=require_open,
        )
        require_open()
        _write_json(
            evidence / "unavailable.json",
            _unavailable(state),
            reserve_closure=reserve_terminal,
            deadline_guard=require_open,
        )
        require_open()
        _write_json(
            evidence / "redactions.json",
            {
                "omissions": _api_key_omissions(state),
                "redactions": state.get("redactions", []),
            },
            reserve_closure=reserve_terminal,
            deadline_guard=require_open,
        )
        require_open()
        _write_json(
            evidence / "run.json",
            state,
            reserve_closure=reserve_terminal,
            deadline_guard=require_open,
        )
        rendered = _render_result(state).encode("utf-8")
        require_open()
        _atomic_write(evidence / "pending-RESULT.md", rendered)
        require_open()
        _atomic_write(RESULT_PATH, rendered)

    def enforce_public_safety() -> None:
        require_open()
        records = _public_safety_redact(
            evidence,
            RESULT_PATH,
            protected_values,
            deadline_guard=require_open,
        )
        if not records:
            return
        safe_state = _read_json(evidence / "run.json")
        if not isinstance(safe_state, dict):
            raise Inconclusive("evidence_safety", "sanitized run state is invalid")
        state.clear()
        state.update(safe_state)
        state.setdefault("redactions", []).extend(records)
        redaction_reason = _redaction_inconclusive_reason(records)
        if redaction_reason is not None:
            _mark_inconclusive(state, "evidence_safety", redaction_reason)
        write_control_outputs()
        require_open()
        if _public_safety_redact(
            evidence,
            RESULT_PATH,
            protected_values,
            deadline_guard=require_open,
        ):
            raise Inconclusive("evidence_safety", "public-safety redaction did not converge")

    require_open()
    write_control_outputs()
    enforce_public_safety()
    source_errors = []
    for attempt in state.get("transferred_attempts", []):
        try:
            verify_candidate(
                evidence / "candidate" / f"attempt-{attempt}" / "source",
                evidence / "candidate" / f"attempt-{attempt}" / "manifest.json",
            )
        except (OSError, TransferError) as exc:
            source_errors.append(f"attempt {attempt}: {type(exc).__name__}")
    missing = [
        _relative(path, evidence) for path in _required_evidence(evidence, state) if not path.is_file()
    ]
    if missing or source_errors:
        details = []
        if missing:
            details.append(f"required evidence is missing: {', '.join(missing)}")
        if source_errors:
            details.append(f"candidate source verification failed: {'; '.join(source_errors)}")
        state["missing_required_evidence"] = [*missing, *source_errors]
        if state["status"] != "Inconclusive":
            _mark_inconclusive(
                state,
                "evidence_completion",
                "; ".join(details),
            )
        write_control_outputs()
        enforce_public_safety()
    require_open()
    recorder.internal(
        label="close pending evidence controls",
        started_wall=closure_started_wall,
        started_monotonic=closure_started_monotonic,
        detail={"phase": "redaction, verification, rendering, and accounting"},
        deadline_guard=require_open,
    )
    if run_started_monotonic is not None:
        state["execute_elapsed_lower_bound_seconds"] = max(
            0.0,
            time.monotonic() - run_started_monotonic,
        )
    state["automated_recorded_cutoff_at"] = _timestamp()
    if state.get("status") == "PendingHumanReview":
        state["review_requested_at"] = state["automated_recorded_cutoff_at"]
    write_control_outputs()
    enforce_public_safety()

    def write_index() -> None:
        index = _evidence_index(evidence)
        encoded_index = (
            json.dumps(index, allow_nan=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        _require_evidence_capacity(
            evidence,
            len(encoded_index),
            replacing=evidence / "evidence-index.json",
            reserve_closure=state.get("status") == "PendingHumanReview",
        )
        require_open()
        _atomic_write(evidence / "evidence-index.json", encoded_index)

    write_index()
    require_open()
    if _evidence_size(evidence) > RETAINED_EVIDENCE_MAX_BYTES:
        raise Inconclusive("evidence_limit", "retained pending evidence exceeds its limit")


def _perform_execution_work(
    *,
    contract_commit: str,
    api_key: str,
    recorder: Recorder,
    evidence: Path,
    state: dict[str, Any],
    instance: str,
    run_id: str,
    context: dict[str, Any],
) -> None:
    authority_copy_started_wall = _utc_now()
    authority_copy_started_monotonic = time.monotonic()
    if LOOP_ROOT != ROOT:
        _write_json(evidence / "context.json", _run_context_record())
    _copy_run_authorities(evidence)
    recorder.internal(
        label="capture reviewed run authorities",
        started_wall=authority_copy_started_wall,
        started_monotonic=authority_copy_started_monotonic,
        detail={"phase": "copy and hash executable authorities"},
    )
    _validate_evaluator(recorder, evidence, run_id, state)
    state["evaluator_validated"] = True
    context["provision_attempted"] = True
    state["candidate_vm_provisioning_started_at"] = _timestamp()
    _provision_candidate(recorder, evidence, instance)
    state["candidate_vm_observed_existing_at"] = _timestamp()
    context["candidate_vm_observed_monotonic"] = time.monotonic()
    state["candidate_boundary_validated"] = True
    _capture_candidate_environment(recorder, evidence, instance)
    context["login_attempted"] = True
    state["login_attempted"] = True
    _login(recorder, instance, api_key)
    api_key = ""
    try:
        _checkout_guard(
            contract_commit,
            allowed_untracked=(evidence, RESULT_PATH),
            recorder=recorder,
        )
    except RuntimeError as exc:
        raise Inconclusive("contract_drift", str(exc)) from exc
    initial_prompt = (REPRODUCTION / "agent-initial-prompt.md").read_text(encoding="utf-8")
    state["agent_attempts_invoked"] = 1
    completion, thread_id = _invoke_agent(
        recorder,
        evidence,
        instance,
        run_id,
        attempt=1,
        prompt=initial_prompt,
        resume_thread_id=None,
    )
    state["agent_thread_id"] = thread_id
    state["completed_attempts"] = 1
    summary = _evaluate_attempt(recorder, evidence, state, instance, run_id, 1, completion)
    if not summary["passed"]:
        feedback = _failure_feedback(evidence, 1)
        _write_json(evidence / "agent" / "attempt-2" / "feedback.json", feedback)
        state["agent_attempts_invoked"] = 2
        completion, _thread = _invoke_agent(
            recorder,
            evidence,
            instance,
            run_id,
            attempt=2,
            prompt=_remediation_prompt(feedback),
            resume_thread_id=thread_id,
        )
        state["completed_attempts"] = 2
        summary = _evaluate_attempt(recorder, evidence, state, instance, run_id, 2, completion)
    state["final_gate_summary"] = summary
    state["final_candidate_identity_sha256"] = summary["candidate_identity_sha256"]
    state["final_manifest_sha256"] = summary["manifest_sha256"]
    if summary["passed"]:
        state["status"] = "PendingHumanReview"
        state["disposition_reason"] = (
            "All non-human gates passed; acceptance requires explicit human source review."
        )
    else:
        state["status"] = "Rejected"
        state["disposition_reason"] = (
            "The final declared candidate retained an admissible failed gate after remediation."
        )


def _finish_execution(
    *,
    contract_commit: str,
    evidence: Path,
    recorder: Recorder,
    state: dict[str, Any],
    instance: str,
    run_id: str,
    context: dict[str, Any],
    run_started_monotonic: float,
    final_phase_deadline: float,
) -> None:
    cleanup_failures: list[str] = []
    cleanup_deadline = final_phase_deadline
    state["cleanup_started_at"] = _timestamp()
    try:
        if context["provision_attempted"]:
            candidate_cleanup_verification: dict[str, bool | float] = {}
            try:
                cleanup_failures.extend(
                    _cleanup_candidate(
                        recorder,
                        instance,
                        context["login_attempted"],
                        cleanup_deadline,
                        candidate_cleanup_verification,
                    )
                )
            except Exception as exc:
                cleanup_failures.append(
                    f"candidate cleanup raised {type(exc).__name__}"
                )
            state["candidate_vm_teardown_finished_at"] = _timestamp()
            state["candidate_vm_teardown_verified"] = (
                candidate_cleanup_verification.get("absent", False)
            )
            first_observed = context["candidate_vm_observed_monotonic"]
            last_observed = candidate_cleanup_verification.get(
                "last_verified_present_monotonic",
                first_observed,
            )
            if first_observed is not None and isinstance(
                last_observed,
                (int, float),
            ):
                state["candidate_vm_observed_interval_lower_bound_seconds"] = max(
                    0.0,
                    float(last_observed) - first_observed,
                )
        if state.get("evaluator_cleanup_required"):
            try:
                cleanup_failures.extend(
                    _cleanup_evaluator(recorder, run_id, cleanup_deadline)
                )
            except Exception as exc:
                cleanup_failures.append(
                    f"evaluator cleanup raised {type(exc).__name__}"
                )
        state["cleanup_finished_at"] = _timestamp()
        _require_execution_deadline_open(
            final_phase_deadline=final_phase_deadline,
            automated_phase_deadline=recorder.deadline_monotonic or math.inf,
        )
        state["redactions"] = list(recorder.redactions)
        if cleanup_failures:
            _mark_inconclusive(state, "cleanup", "; ".join(cleanup_failures))
        try:
            _checkout_guard(
                contract_commit,
                allowed_untracked=(evidence, RESULT_PATH),
                recorder=recorder,
            )
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            _mark_inconclusive(
                state,
                "contract_drift",
                f"approved checkout changed during execution: {type(exc).__name__}",
            )
        try:
            _write_run_outputs(
                evidence,
                state,
                recorder=recorder,
                protected_values=recorder.protected_values(),
                run_started_monotonic=run_started_monotonic,
                final_phase_deadline=final_phase_deadline,
                automated_phase_deadline=recorder.deadline_monotonic or math.inf,
            )
        except Exception as exc:
            _mark_inconclusive(
                state,
                "evidence_closure",
                f"pending evidence closure raised {type(exc).__name__}",
            )
            state.pop("review_requested_at", None)
            state["redactions"] = list(recorder.redactions)
            try:
                _write_run_outputs(
                    evidence,
                    state,
                    recorder=recorder,
                    protected_values=recorder.protected_values(),
                    run_started_monotonic=run_started_monotonic,
                    final_phase_deadline=final_phase_deadline,
                    automated_phase_deadline=recorder.deadline_monotonic or math.inf,
                )
            except Exception as recovery_exc:
                _mark_inconclusive(
                    state,
                    "evidence_closure",
                    f"minimal closure recovery raised {type(recovery_exc).__name__}",
                )
                state["automated_recorded_cutoff_at"] = _timestamp()
                state["execute_elapsed_lower_bound_seconds"] = max(
                    0.0,
                    time.monotonic() - run_started_monotonic,
                )
                rendered = _render_result(state).encode("utf-8")
                try:
                    _require_execution_deadline_open(
                        final_phase_deadline=final_phase_deadline,
                        automated_phase_deadline=(
                            recorder.deadline_monotonic or math.inf
                        ),
                    )
                    _atomic_write(evidence / "pending-RESULT.md", rendered)
                    _require_execution_deadline_open(
                        final_phase_deadline=final_phase_deadline,
                        automated_phase_deadline=(
                            recorder.deadline_monotonic or math.inf
                        ),
                    )
                    _atomic_write(RESULT_PATH, rendered)
                    _require_execution_deadline_open(
                        final_phase_deadline=final_phase_deadline,
                        automated_phase_deadline=(
                            recorder.deadline_monotonic or math.inf
                        ),
                    )
                    _write_json(
                        evidence / "run.json",
                        state,
                        reserve_closure=False,
                        deadline_guard=lambda: _require_execution_deadline_open(
                            final_phase_deadline=final_phase_deadline,
                            automated_phase_deadline=(
                                recorder.deadline_monotonic or math.inf
                            ),
                        ),
                    )
                except Exception:
                    pass
        try:
            _verify_pending_index(evidence, require_completion=False)
        except (OSError, ValueError, RecursionError, json.JSONDecodeError) as exc:
            raise ExecuteEvidenceIncomplete() from exc
    finally:
        recorder.clear_protected_values()


def _execute_locked(contract_commit: str, deadline: ExecutionDeadline) -> int:
    api_key = _preflight(contract_commit)
    _load_candidate_transfer()
    run_id = _run_id()
    instance = _instance_name(run_id)
    evidence = EVIDENCE_ROOT / run_id
    run_started_at = _timestamp()
    run_started_monotonic = time.monotonic()
    automated_phase_deadline = (
        run_started_monotonic + AUTOMATED_PHASE_TIMEOUT_SECONDS
    )
    automated_work_deadline = automated_phase_deadline - CLEANUP_TIMEOUT_SECONDS
    evidence.mkdir(parents=True, exist_ok=False)
    recorder = Recorder(
        evidence,
        deadline_monotonic=automated_phase_deadline,
    )
    recorder.protect("OPENAI_API_KEY", api_key)
    state: dict[str, Any] = {
        "agent_attempts_invoked": 0,
        "behavior_attempts": [],
        "bootstrap_attempts": [],
        "candidate_instance": instance,
        "completed_attempts": 0,
        "contract_commit": contract_commit,
        "evaluated_attempts": [],
        "identified_attempts": [],
        "loop_id": ACTIVE_LOOP.loop_id,
        "login_attempted": False,
        "run_id": run_id,
        "run_started_at": run_started_at,
        "automated_phase_deadline_seconds": AUTOMATED_PHASE_TIMEOUT_SECONDS,
        "automated_work_deadline_seconds": (
            AUTOMATED_PHASE_TIMEOUT_SECONDS - CLEANUP_TIMEOUT_SECONDS
        ),
        "cleanup_and_pending_closure_deadline_seconds": CLEANUP_TIMEOUT_SECONDS,
        "status": "Inconclusive",
        "transfer_attempts_started": [],
        "transferred_attempts": [],
        "typing_attempts": [],
        "workload_id": WORKLOAD.workload_id,
    }
    context: dict[str, Any] = {
        "candidate_vm_observed_monotonic": None,
        "login_attempted": False,
        "provision_attempted": False,
    }

    def mark_work_deadline() -> None:
        _mark_inconclusive(
            state,
            "execution_envelope",
            "automated work window exhausted the five-minute cleanup reserve",
        )

    try:
        try:
            deadline.start(automated_work_deadline, automated_phase_deadline)
            _perform_execution_work(
                contract_commit=contract_commit,
                api_key=api_key,
                recorder=recorder,
                evidence=evidence,
                state=state,
                instance=instance,
                run_id=run_id,
                context=context,
            )
        except ExecuteWorkDeadline:
            mark_work_deadline()
        except Inconclusive as exc:
            _mark_inconclusive(state, exc.stage, exc.detail)
        except Exception as exc:
            _mark_inconclusive(
                state,
                "orchestration",
                f"unexpected orchestration error: {type(exc).__name__}",
            )
        work_deadline_observed = deadline.begin_cleanup()
    except ExecuteWorkDeadline:
        mark_work_deadline()
        work_deadline_observed = deadline.begin_cleanup()

    if work_deadline_observed:
        mark_work_deadline()
    if deadline.hard_deadline is None:
        raise RuntimeError("cleanup deadline was not established")
    _finish_execution(
        contract_commit=contract_commit,
        evidence=evidence,
        recorder=recorder,
        state=state,
        instance=instance,
        run_id=run_id,
        context=context,
        run_started_monotonic=run_started_monotonic,
        final_phase_deadline=deadline.hard_deadline,
    )
    deadline.complete()
    try:
        _write_completion_receipt(
            evidence,
            kind="execution",
            run_id=run_id,
            contract_commit=contract_commit,
        )
        _verify_pending_index(evidence)
    except Exception as exc:
        raise ExecuteEvidenceIncomplete() from exc
    print(json.dumps({"run_id": run_id, "status": state["status"]}, sort_keys=True))
    return 0 if state["status"] in {"PendingHumanReview", "Rejected", "Inconclusive"} else 1


def execute(contract_commit: str) -> int:
    lock_descriptor = _acquire_execution_lock()
    deadline = ExecutionDeadline()
    terminal_incomplete = False
    result: int | None = None
    failure: BaseException | None = None
    restore_mask: set[signal.Signals] | None = None

    def observe_failure(exc: BaseException) -> None:
        nonlocal failure, terminal_incomplete
        if isinstance(
            exc,
            (ExecuteWorkDeadline, ExecuteHardDeadline, ExecuteEvidenceIncomplete),
        ):
            terminal_incomplete = True
        elif failure is None:
            failure = exc

    try:
        try:
            deadline.install()
            result = _execute_locked(contract_commit, deadline)
        except (
            ExecuteWorkDeadline,
            ExecuteHardDeadline,
            ExecuteEvidenceIncomplete,
        ):
            terminal_incomplete = True
            try:
                deadline.abort()
            except BaseException as abort_exc:
                observe_failure(abort_exc)
        except BaseException as exc:
            observe_failure(exc)
    finally:
        try:
            restore_mask = signal.pthread_sigmask(
                signal.SIG_BLOCK,
                {signal.SIGALRM},
            )
            try:
                terminal_incomplete = (
                    deadline.restore_blocked() or terminal_incomplete
                )
            except BaseException as exc:
                observe_failure(exc)
        except BaseException as exc:
            observe_failure(exc)
        finally:
            try:
                os.close(lock_descriptor)
            except BaseException as exc:
                observe_failure(exc)
            finally:
                if restore_mask is not None:
                    try:
                        signal.pthread_sigmask(signal.SIG_SETMASK, restore_mask)
                    except BaseException as exc:
                        observe_failure(exc)
    if terminal_incomplete:
        print(
            json.dumps(
                {
                    "failure_stage": "execution_envelope",
                    "recovery": "human_required",
                    "status": "Inconclusive",
                    "terminal_evidence": "incomplete",
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    if failure is not None:
        raise failure.with_traceback(failure.__traceback__)
    if result is None:
        raise RuntimeError("execution completed without a result")
    return result


def _review_location(
    value: Any,
    *,
    source_files: set[str],
    service_command: list[str],
    allow_missing: bool,
    source_line_counts: dict[str, int] | None = None,
    allow_source_file: bool = True,
) -> dict[str, Any]:
    if not isinstance(value, dict) or not isinstance(value.get("kind"), str):
        raise ValueError("human review location is invalid")
    kind = value["kind"]
    if kind == "source_line":
        if set(value) != {"file", "kind", "line"} or value.get("file") not in source_files:
            raise ValueError("source-line finding does not identify final candidate source")
        line = value.get("line")
        if not isinstance(line, int) or isinstance(line, bool) or line < 1:
            raise ValueError("source-line finding requires a positive line")
        if source_line_counts is not None and line > source_line_counts.get(value["file"], 0):
            raise ValueError("source-line finding identifies a line that does not exist")
    elif kind == "source_file" and allow_source_file:
        if set(value) != {"file", "kind"} or value.get("file") not in source_files:
            raise ValueError("source-file finding does not identify final candidate source")
    elif kind == "service_command_argument":
        if set(value) != {"argument_index", "kind"}:
            raise ValueError("service-command finding has the wrong fields")
        index = value.get("argument_index")
        if (
            not isinstance(index, int)
            or isinstance(index, bool)
            or index < 0
            or index >= len(service_command)
        ):
            raise ValueError("service-command finding has an invalid argument index")
    elif kind == "missing_workspace_path" and allow_missing:
        if set(value) != {"kind", "path"} or not isinstance(value.get("path"), str):
            raise ValueError("missing-path finding has the wrong fields")
        relative = PurePosixPath(value["path"])
        if (
            relative.is_absolute()
            or not relative.parts
            or any(part in {"", ".", ".."} for part in relative.parts)
            or relative.as_posix() != value["path"]
            or value["path"] in source_files
            or any(
                PurePosixPath(source).is_relative_to(relative)
                for source in source_files
            )
            or any(
                relative.is_relative_to(PurePosixPath(source))
                for source in source_files
            )
        ):
            raise ValueError(
                "missing-path finding does not identify an absent regular-file path"
            )
    else:
        raise ValueError("human review location kind is not allowed")
    return cast(dict[str, Any], value)


def _validate_attestation(
    value: Any,
    expected_manifest: str,
    expected_identity: str,
    source_files: set[str],
    service_command: list[str],
    source_line_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    required = {
        "active_minutes",
        "approved_boundary_exceptions",
        "decision",
        "findings",
        "reviewed_candidate_identity_sha256",
        "reviewed_manifest_sha256",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("human attestation has the wrong fields")
    if value["decision"] not in {"Affirmative", "Negative"}:
        raise ValueError("human decision must be Affirmative or Negative")
    if value["reviewed_manifest_sha256"] != expected_manifest:
        raise ValueError("human review did not identify the final candidate manifest")
    if value["reviewed_candidate_identity_sha256"] != expected_identity:
        raise ValueError("human review did not identify the final candidate command and source")
    if not isinstance(value["findings"], list) or not isinstance(
        value["approved_boundary_exceptions"], list
    ):
        raise ValueError("human findings and boundary exceptions must be arrays")
    active = value["active_minutes"]
    if active != "unknown" and (
        not isinstance(active, (int, float))
        or isinstance(active, bool)
        or not math.isfinite(active)
        or active < 0
    ):
        raise ValueError("human active_minutes must be nonnegative or unknown")
    if value["decision"] == "Negative" and not value["findings"]:
        raise ValueError("a Negative human review requires a concrete finding")
    if value["decision"] == "Affirmative" and value["findings"]:
        raise ValueError("an Affirmative human review cannot contain violation findings")
    for finding in value["findings"]:
        if not isinstance(finding, dict) or set(finding) != {"clause", "detail", "location"}:
            raise ValueError("human finding has the wrong fields")
        if finding["clause"] not in HUMAN_REVIEW_CLAUSES:
            raise ValueError("human finding clause is not one of the declared checklist clauses")
        if not isinstance(finding["detail"], str) or not finding["detail"].strip():
            raise ValueError("human finding detail must be a nonempty string")
        _review_location(
            finding["location"],
            source_files=source_files,
            service_command=service_command,
            allow_missing=True,
            source_line_counts=source_line_counts,
            allow_source_file=True,
        )
    for exception in value["approved_boundary_exceptions"]:
        if not isinstance(exception, dict) or set(exception) != {
            "boundary",
            "kind",
            "location",
            "necessity",
        }:
            raise ValueError("human boundary exception has the wrong fields")
        if exception["kind"] != "boundary_cast_or_suppression_outside_prohibited_surfaces":
            raise ValueError("human review tried to waive a non-waivable surface")
        for field in ("boundary", "necessity"):
            if not isinstance(exception[field], str) or not exception[field].strip():
                raise ValueError(f"human boundary exception {field} must be nonempty")
        _review_location(
            exception["location"],
            source_files=source_files,
            service_command=service_command,
            allow_missing=False,
            source_line_counts=source_line_counts,
            allow_source_file=False,
        )
    return cast(dict[str, Any], value)


def _verify_inventory(
    evidence: Path,
    *,
    index_name: str,
    version: int,
    allowed_extra_paths: set[str] | None = None,
) -> dict[str, Any]:
    index_path = evidence / index_name
    index = _read_json(index_path)
    if (
        not isinstance(index, dict)
        or set(index)
        != {
            "artifact_self_recording_tail_seconds",
            "files",
            "generated_at",
            "inventory_scan_hash_elapsed_seconds",
            "version",
        }
        or index.get("version") != version
        or not isinstance(index.get("files"), list)
        or index.get("artifact_self_recording_tail_seconds") != "unknown"
        or not isinstance(index.get("inventory_scan_hash_elapsed_seconds"), (int, float))
        or isinstance(index.get("inventory_scan_hash_elapsed_seconds"), bool)
        or not math.isfinite(index["inventory_scan_hash_elapsed_seconds"])
        or index["inventory_scan_hash_elapsed_seconds"] < 0
    ):
        raise ValueError(f"{index_name} is invalid")
    indexed_paths: set[str] = set()
    for record in index["files"]:
        if not isinstance(record, dict) or set(record) != {"path", "sha256", "size"}:
            raise ValueError(f"{index_name} contains an invalid file record")
        relative = PurePosixPath(record["path"]) if isinstance(record["path"], str) else None
        if (
            relative is None
            or relative.is_absolute()
            or not relative.parts
            or any(part in {"", ".", ".."} for part in relative.parts)
            or relative.as_posix() != record["path"]
            or record["path"] in indexed_paths
        ):
            raise ValueError(f"{index_name} contains an invalid path")
        if _public_safety_labels(
            record["path"].encode("utf-8", errors="surrogatepass"),
            check_host_paths=True,
        ):
            raise ValueError(f"{index_name} contains a non-public-safe path")
        indexed_paths.add(record["path"])
        path = evidence.joinpath(*relative.parts)
        if (
            not isinstance(record["sha256"], str)
            or not isinstance(record["size"], int)
            or isinstance(record["size"], bool)
            or record["size"] < 0
            or not path.is_file()
            or path.is_symlink()
            or _sha256(path) != record["sha256"]
            or path.stat().st_size != record["size"]
        ):
            raise ValueError(f"indexed evidence changed or is missing: {record['path']}")
    observed_paths = set()
    for path in evidence.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"evidence contains a symbolic link: {_relative(path, evidence)}")
        if path.is_file() and path != index_path:
            observed_paths.add(_relative(path, evidence))
    extras = allowed_extra_paths or set()
    if (
        not indexed_paths.issubset(observed_paths)
        or observed_paths - indexed_paths - extras
        or indexed_paths & extras
    ):
        raise ValueError(f"evidence files do not exactly match {index_name}")
    if _evidence_size(evidence) > RETAINED_EVIDENCE_MAX_BYTES:
        raise ValueError("retained evidence exceeds its approved byte limit")
    return cast(dict[str, Any], index)


def _verify_pending_index(
    evidence: Path,
    *,
    allow_terminal: bool = False,
    require_completion: bool = True,
) -> dict[str, Any]:
    extras = {EXECUTION_COMPLETION_NAME}
    if allow_terminal:
        extras.update(
            {
                FINALIZATION_ATTEMPT_NAME,
                FINALIZATION_COMPLETION_NAME,
                "settlement.json",
                "terminal-evidence-index.json",
            }
        )
    index = _verify_inventory(
        evidence,
        index_name="evidence-index.json",
        version=3,
        allowed_extra_paths=extras,
    )
    pending_result = evidence / "pending-RESULT.md"
    if "pending-RESULT.md" not in {record["path"] for record in index["files"]}:
        raise ValueError("pending evidence index does not include pending-RESULT.md")
    if not allow_terminal and (
        not RESULT_PATH.is_file()
        or RESULT_PATH.is_symlink()
        or RESULT_PATH.read_bytes() != pending_result.read_bytes()
    ):
        raise ValueError("pending RESULT.md projection changed or is missing")
    if require_completion:
        state = _read_json(evidence / "run.json")
        if (
            not isinstance(state, dict)
            or not isinstance(state.get("run_id"), str)
            or not isinstance(state.get("contract_commit"), str)
        ):
            raise ValueError("pending run identity is invalid")
        _validate_completion_receipt(
            evidence,
            kind="execution",
            run_id=state["run_id"],
            contract_commit=state["contract_commit"],
        )
    return index


def _source_line_counts(root: Path, source_files: set[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for relative in sorted(source_files):
        path = root.joinpath(*PurePosixPath(relative).parts)
        observed = path.stat(follow_symlinks=False)
        original_mode = stat.S_IMODE(observed.st_mode)
        changed_mode = False
        hard_deadline = False
        try:
            try:
                data = path.read_bytes()
            except PermissionError:
                path.chmod(original_mode | stat.S_IRUSR, follow_symlinks=False)
                changed_mode = True
                data = path.read_bytes()
        except (ExecuteHardDeadline, FinalizationHardDeadline):
            hard_deadline = True
            raise
        finally:
            if changed_mode and not hard_deadline:
                path.chmod(original_mode, follow_symlinks=False)
        finished = path.stat(follow_symlinks=False)
        if (
            observed.st_dev != finished.st_dev
            or observed.st_ino != finished.st_ino
            or observed.st_size != finished.st_size
            or stat.S_IMODE(finished.st_mode) != original_mode
        ):
            raise ValueError("candidate source changed while line locations were derived")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            counts[relative] = 0
        else:
            counts[relative] = len(text.splitlines())
    return counts


def _pending_review_inputs(
    evidence: Path,
    run_id: str,
    contract_commit: str,
    *,
    allow_terminal: bool = False,
) -> tuple[dict[str, Any], set[str], dict[str, int], list[str]]:
    state = _read_json(evidence / "run.json")
    if not isinstance(state, dict) or state.get("status") != "PendingHumanReview":
        raise ValueError("run is not pending human source review")
    if state.get("run_id") != run_id or state.get("contract_commit") != contract_commit:
        raise ValueError("pending run identity does not match the requested contract")
    _verify_pending_index(evidence, allow_terminal=allow_terminal)
    summary = state.get("final_gate_summary")
    if not isinstance(summary, dict) or summary.get("attempt") not in {1, 2}:
        raise ValueError("final gate summary is invalid")
    manifest_relative = summary.get("manifest_path")
    relative = PurePosixPath(manifest_relative) if isinstance(manifest_relative, str) else None
    if (
        relative is None
        or relative.is_absolute()
        or any(part in {"", ".", ".."} for part in relative.parts)
        or relative.as_posix() != manifest_relative
    ):
        raise ValueError("final candidate manifest path is invalid")
    manifest_path = evidence.joinpath(*relative.parts)
    manifest = _read_json(manifest_path)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), list):
        raise ValueError("final candidate manifest is invalid")
    source_files = {
        record["path"]
        for record in manifest["files"]
        if isinstance(record, dict) and isinstance(record.get("path"), str)
    }
    if len(source_files) != len(manifest["files"]):
        raise ValueError("final candidate manifest contains an invalid source record")
    service_command = summary.get("service_command")
    if not isinstance(service_command, list):
        raise ValueError("final service command is invalid")
    service_command = _validate_argv(service_command)
    if not service_command[0]:
        raise ValueError("final service command is invalid")
    source_root = evidence / "candidate" / f"attempt-{summary['attempt']}" / "source"
    verify_candidate(
        source_root,
        manifest_path,
    )
    line_counts = _source_line_counts(source_root, source_files)
    identity_value = {
        "manifest_sha256": _sha256(manifest_path),
        "service_command": service_command,
    }
    identity_hash = hashlib.sha256(
        json.dumps(identity_value, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()
    if (
        state.get("final_manifest_sha256") != identity_value["manifest_sha256"]
        or state.get("final_candidate_identity_sha256") != identity_hash
        or summary.get("candidate_identity_sha256") != identity_hash
    ):
        raise ValueError("final candidate identity does not match its source and command")
    return state, source_files, line_counts, service_command


def _verified_automatic_terminal_generation(
    evidence: Path,
    run_id: str,
    contract_commit: str,
    state: Any,
    *,
    allow_terminal: bool = False,
) -> bool:
    if (
        not isinstance(state, dict)
        or state.get("status") not in {"Rejected", "Inconclusive"}
        or state.get("run_id") != run_id
        or state.get("contract_commit") != contract_commit
    ):
        return False
    try:
        _verify_pending_index(evidence, allow_terminal=allow_terminal)
        return (evidence / "pending-RESULT.md").read_text(
            encoding="utf-8"
        ) == _render_result(state)
    except (KeyError, OSError, RecursionError, TypeError, ValueError, json.JSONDecodeError):
        return False


def _minimal_invalid_pending_state(
    run_id: str,
    contract_commit: str,
    received_at: str,
) -> dict[str, Any]:
    return {
        "completed_attempts": 0,
        "contract_commit": contract_commit,
        "run_id": run_id,
        "run_started_at": received_at,
        "status": "Inconclusive",
    }


def _fallback_terminal_accounting(
    state: dict[str, Any],
    received_at: str,
) -> dict[str, Any]:
    try:
        return _accounting(
            Path(state["evidence_path"]),
            run_started_at=state["run_started_at"],
            finished_at=received_at,
            review_requested_at=state.get("review_requested_at"),
            review_received_at=state.get("review_received_at"),
            human_active_minutes=state.get("human_active_minutes", "unknown"),
            candidate_vm_provisioning_started_at=state.get(
                "candidate_vm_provisioning_started_at"
            ),
            candidate_vm_observed_existing_at=state.get(
                "candidate_vm_observed_existing_at"
            ),
            candidate_vm_teardown_finished_at=state.get(
                "candidate_vm_teardown_finished_at"
            ),
            candidate_vm_teardown_verified=state.get(
                "candidate_vm_teardown_verified", False
            )
            is True,
            candidate_vm_observed_interval_lower_bound_seconds=state.get(
                "candidate_vm_observed_interval_lower_bound_seconds"
            ),
            finalization_elapsed_lower_bound_seconds=state.get(
                "finalization_elapsed_lower_bound_seconds", "unknown"
            ),
            execute_elapsed_lower_bound_seconds=state.get(
                "execute_elapsed_lower_bound_seconds", "unknown"
            ),
        )
    except (KeyError, OSError, RecursionError, TypeError, ValueError, json.JSONDecodeError):
        return _unknown_accounting(state, received_at)


def _unknown_accounting(state: dict[str, Any], finished_at: str) -> dict[str, Any]:
    return {
        "agent": {
            "invocations": "unknown",
            "monetary_cost": "unknown",
            "total_elapsed_seconds": "unknown",
        },
        "candidate_vm": {
            "lifetime_seconds": "unknown",
            "monetary_cost": "unknown",
            "observed_existing_at": state.get("candidate_vm_observed_existing_at"),
            "observed_interval_lower_bound_seconds": "unknown",
            "provisioning_started_at": state.get("candidate_vm_provisioning_started_at"),
            "right_censored": "unknown",
            "teardown_finished_at": state.get("candidate_vm_teardown_finished_at"),
            "teardown_verified": "unknown",
        },
        "evaluator": {
            "monetary_cost": "unknown",
            "standing_provisioning_and_idle": "excluded",
            "workload_seconds": "unknown",
        },
        "human": {
            "active_minutes": state.get("human_active_minutes", "unknown"),
            "monetary_cost": "unknown",
            "review_wait_upper_bound_seconds": "unknown",
        },
        "overlap": {
            "nonexclusive": True,
            "rule": (
                "Agent, candidate-VM, and evaluator intervals overlap trusted-machine "
                "and wall intervals; no category total may be summed into cost or latency."
            ),
        },
        "trusted_machine": {
            "coverage": "unknown because the pending accounting generation was invalid",
            "artifact_self_recording_tail_seconds": "unknown",
            "execute_elapsed_lower_bound_seconds": state.get(
                "execute_elapsed_lower_bound_seconds", "unknown"
            ),
            "execute_recorded_active_seconds": "unknown",
            "finalization_elapsed_lower_bound_seconds": state.get(
                "finalization_elapsed_lower_bound_seconds", "unknown"
            ),
            "monetary_cost": "unknown",
            "pending_index_scan_hash_elapsed_seconds": "unknown",
        },
        "wall": {
            "elapsed_lower_bound_seconds": "unknown",
            "post_cutoff_tail_seconds": "unknown",
            "recorded_cutoff_at": finished_at,
            "review_received_at": state.get("review_received_at"),
            "review_requested_at": state.get("review_requested_at"),
            "run_started_at": state.get("run_started_at", "unknown"),
        },
    }


def _settlement_value(
    *,
    evidence: Path,
    run_id: str,
    contract_commit: str,
    pending_state: dict[str, Any],
    pending_valid: bool,
    pending_detail: str | None,
    attestation: dict[str, Any] | None,
    received_at: str,
    finalization_started_at: str | None = None,
    finalization_elapsed_lower_bound_seconds: float | str = "unknown",
) -> dict[str, Any]:
    terminal_state = dict(pending_state)
    terminal_state["run_id"] = run_id
    terminal_state["contract_commit"] = contract_commit
    terminal_state["finalization_started_at"] = finalization_started_at
    terminal_state["finalization_elapsed_lower_bound_seconds"] = (
        finalization_elapsed_lower_bound_seconds
    )
    if pending_valid and attestation is not None:
        terminal_state["human_active_minutes"] = attestation["active_minutes"]
        terminal_state["review_received_at"] = received_at
        terminal_state["status"] = (
            "Accepted" if attestation["decision"] == "Affirmative" else "Rejected"
        )
        terminal_state["failure_stage"] = None
        terminal_state["disposition_reason"] = (
            "All non-human gates passed and human source review was affirmative."
            if terminal_state["status"] == "Accepted"
            else "Human source review found a declared implementation violation."
        )
    else:
        terminal_state["status"] = "Inconclusive"
        terminal_state["failure_stage"] = "human_review_evidence"
        terminal_state["disposition_reason"] = (
            "Pending evidence or final candidate source failed integrity verification before human settlement."
        )
        terminal_state["human_active_minutes"] = "unknown"
    terminal_state["evidence_path"] = str(evidence)
    accounting = (
        _fallback_terminal_accounting(terminal_state, received_at)
        if pending_valid
        else _unknown_accounting(terminal_state, received_at)
    )
    terminal_state.pop("evidence_path", None)
    unavailable = _unavailable(terminal_state)
    result_text = _render_result(terminal_state)
    result_bytes = result_text.encode("utf-8")
    pending_index = evidence / "evidence-index.json"
    pending_hash = (
        _sha256(pending_index)
        if pending_index.is_file() and not pending_index.is_symlink()
        else "unknown"
    )
    return {
        "accounting": accounting,
        "attestation": attestation,
        "contract_commit": contract_commit,
        "disposition_reason": terminal_state["disposition_reason"],
        "failure_stage": terminal_state.get("failure_stage"),
        "pending_evidence": {
            "detail": pending_detail,
            "index_path": "evidence-index.json",
            "index_sha256": pending_hash,
            "verification": "valid" if pending_valid else "invalid",
        },
        "received_at": received_at,
        "result": {
            "sha256": hashlib.sha256(result_bytes).hexdigest(),
            "size": len(result_bytes),
            "utf8": result_text,
        },
        "run_id": run_id,
        "status": terminal_state["status"],
        "terminal_state": terminal_state,
        "unavailable": unavailable,
        "version": 1,
    }


def _validate_settlement(
    value: Any,
    *,
    evidence: Path,
    run_id: str,
    contract_commit: str,
) -> dict[str, Any]:
    fields = {
        "accounting",
        "attestation",
        "contract_commit",
        "disposition_reason",
        "failure_stage",
        "pending_evidence",
        "received_at",
        "result",
        "run_id",
        "status",
        "terminal_state",
        "unavailable",
        "version",
    }
    if (
        not isinstance(value, dict)
        or set(value) != fields
        or value.get("version") != 1
        or value.get("run_id") != run_id
        or value.get("contract_commit") != contract_commit
        or value.get("status") not in {"Accepted", "Rejected", "Inconclusive"}
        or not isinstance(value.get("received_at"), str)
    ):
        raise ValueError("terminal settlement is invalid")
    try:
        received = datetime.fromisoformat(value["received_at"])
    except ValueError as exc:
        raise ValueError("terminal settlement timestamp is invalid") from exc
    if received.tzinfo is None:
        raise ValueError("terminal settlement timestamp must include a UTC offset")
    pending = value.get("pending_evidence")
    if (
        not isinstance(pending, dict)
        or set(pending) != {"detail", "index_path", "index_sha256", "verification"}
        or pending.get("index_path") != "evidence-index.json"
        or pending.get("verification") not in {"valid", "invalid"}
        or not isinstance(pending.get("index_sha256"), str)
    ):
        raise ValueError("terminal settlement pending-evidence record is invalid")
    result = value.get("result")
    if (
        not isinstance(result, dict)
        or set(result) != {"sha256", "size", "utf8"}
        or not isinstance(result.get("utf8"), str)
        or not isinstance(result.get("size"), int)
        or isinstance(result.get("size"), bool)
        or result["size"] != len(result["utf8"].encode("utf-8"))
        or result.get("sha256") != hashlib.sha256(result["utf8"].encode("utf-8")).hexdigest()
    ):
        raise ValueError("terminal settlement result is invalid")
    terminal_state = value.get("terminal_state")
    finalization_lower_bound = (
        terminal_state.get("finalization_elapsed_lower_bound_seconds")
        if isinstance(terminal_state, dict)
        else None
    )
    if (
        not isinstance(terminal_state, dict)
        or terminal_state.get("status") != value["status"]
        or terminal_state.get("run_id") != run_id
        or terminal_state.get("contract_commit") != contract_commit
        or terminal_state.get("failure_stage") != value.get("failure_stage")
        or terminal_state.get("disposition_reason") != value.get("disposition_reason")
        or result["utf8"] != _render_result(terminal_state)
        or value.get("unavailable") != _unavailable(terminal_state)
        or (
            finalization_lower_bound != "unknown"
            and (
                not isinstance(finalization_lower_bound, (int, float))
                or isinstance(finalization_lower_bound, bool)
                or not math.isfinite(finalization_lower_bound)
                or finalization_lower_bound < 0
            )
        )
        or (
            terminal_state.get("finalization_started_at") is not None
            and not isinstance(terminal_state.get("finalization_started_at"), str)
        )
    ):
        raise ValueError("terminal settlement state is invalid")

    if pending["verification"] == "valid":
        if pending.get("detail") is not None or not isinstance(
            value.get("attestation"), dict
        ):
            raise ValueError("valid pending evidence requires an attestation")
        pending_state, source_files, source_line_counts, service_command = _pending_review_inputs(
            evidence,
            run_id,
            contract_commit,
            allow_terminal=True,
        )
        attestation = _validate_attestation(
            value["attestation"],
            pending_state["final_manifest_sha256"],
            pending_state["final_candidate_identity_sha256"],
            source_files,
            service_command,
            source_line_counts,
        )
        expected = _settlement_value(
            evidence=evidence,
            run_id=run_id,
            contract_commit=contract_commit,
            pending_state=pending_state,
            pending_valid=True,
            pending_detail=None,
            attestation=attestation,
            received_at=value["received_at"],
            finalization_started_at=terminal_state.get("finalization_started_at"),
            finalization_elapsed_lower_bound_seconds=terminal_state.get(
                "finalization_elapsed_lower_bound_seconds", "unknown"
            ),
        )
    else:
        if (
            value.get("status") != "Inconclusive"
            or value.get("attestation") is not None
            or pending.get("detail") != PENDING_INTEGRITY_FAILURE_DETAIL
        ):
            raise ValueError("invalid pending evidence can only settle Inconclusive")
        minimal_state = _minimal_invalid_pending_state(
            run_id,
            contract_commit,
            value["received_at"],
        )
        expected = _settlement_value(
            evidence=evidence,
            run_id=run_id,
            contract_commit=contract_commit,
            pending_state=minimal_state,
            pending_valid=False,
            pending_detail=pending.get("detail"),
            attestation=None,
            received_at=value["received_at"],
            finalization_started_at=terminal_state.get("finalization_started_at"),
            finalization_elapsed_lower_bound_seconds=terminal_state.get(
                "finalization_elapsed_lower_bound_seconds", "unknown"
            ),
        )
    if value != expected:
        raise ValueError("terminal settlement is not the canonical disposition")
    return cast(dict[str, Any], value)


def _close_terminal_evidence(
    evidence: Path,
    settlement: dict[str, Any],
) -> None:
    terminal_index = evidence / "terminal-evidence-index.json"
    if terminal_index.exists() or terminal_index.is_symlink():
        raise ValueError("pre-existing terminal evidence requires human recovery")
    _atomic_write(RESULT_PATH, settlement["result"]["utf8"].encode("utf-8"))
    _assert_public_safe_terminal(evidence, RESULT_PATH)
    value = _evidence_index(
        evidence,
        index_name="terminal-evidence-index.json",
        version=4,
    )
    encoded = (
        json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    _require_evidence_capacity(
        evidence,
        len(encoded),
        reserve_closure=False,
    )
    _atomic_write_new(terminal_index, encoded)
    if _evidence_size(evidence) > RETAINED_EVIDENCE_MAX_BYTES:
        raise ValueError("terminal evidence exceeds its approved byte limit")


def _verify_terminal_index(
    evidence: Path,
    *,
    run_id: str,
    contract_commit: str,
    require_completion: bool = True,
) -> dict[str, Any]:
    _validate_finalization_attempt(
        evidence,
        run_id=run_id,
        contract_commit=contract_commit,
    )
    _verify_inventory(
        evidence,
        index_name="terminal-evidence-index.json",
        version=4,
        allowed_extra_paths={FINALIZATION_COMPLETION_NAME},
    )
    settlement = _validate_settlement(
        _read_json(evidence / "settlement.json"),
        evidence=evidence,
        run_id=run_id,
        contract_commit=contract_commit,
    )
    if (
        not RESULT_PATH.is_file()
        or RESULT_PATH.is_symlink()
        or RESULT_PATH.read_bytes() != settlement["result"]["utf8"].encode("utf-8")
    ):
        raise ValueError("terminal RESULT.md does not match settlement")
    if settlement["pending_evidence"]["verification"] == "valid":
        index = _verify_pending_index(evidence, allow_terminal=True)
        if _sha256(evidence / "evidence-index.json") != settlement["pending_evidence"][
            "index_sha256"
        ]:
            raise ValueError("terminal settlement does not bind the pending index")
        if index.get("version") != 3:
            raise ValueError("terminal settlement references an invalid pending generation")
    _assert_public_safe_terminal(evidence, RESULT_PATH)
    if require_completion:
        _validate_completion_receipt(
            evidence,
            kind="finalization",
            run_id=run_id,
            contract_commit=contract_commit,
        )
    return settlement


def _validate_finalization_attempt(
    evidence: Path,
    *,
    run_id: str,
    contract_commit: str,
) -> dict[str, Any]:
    value = _read_bounded_json(
        evidence / FINALIZATION_ATTEMPT_NAME,
        maximum_bytes=CONTROL_DOCUMENT_MAX_BYTES,
    )
    if (
        not isinstance(value, dict)
        or set(value) != {"contract_commit", "run_id", "started_at", "version"}
        or value.get("version") != 1
        or value.get("run_id") != run_id
        or value.get("contract_commit") != contract_commit
        or not isinstance(value.get("started_at"), str)
    ):
        raise ValueError("finalization attempt marker is invalid")
    try:
        started_at = datetime.fromisoformat(value["started_at"])
    except ValueError as exc:
        raise ValueError("finalization attempt timestamp is invalid") from exc
    if started_at.tzinfo is None:
        raise ValueError("finalization attempt timestamp must include a UTC offset")
    return cast(dict[str, Any], value)


def _begin_finalization_attempt(run_id: str, contract_commit: str) -> None:
    if RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise ValueError("invalid run ID")
    contract_commit = _validate_contract_commit(contract_commit)
    evidence = EVIDENCE_ROOT / run_id
    if not evidence.is_dir() or evidence.is_symlink():
        raise ValueError("run evidence directory does not exist")
    terminal_names = (
        FINALIZATION_ATTEMPT_NAME,
        FINALIZATION_COMPLETION_NAME,
        "settlement.json",
        "terminal-evidence-index.json",
    )
    preexisting = [
        name
        for name in terminal_names
        if (evidence / name).exists() or (evidence / name).is_symlink()
    ]
    temporary_prefixes = tuple(
        f".{name}." for name in (*terminal_names, EXECUTION_COMPLETION_NAME)
    )
    preexisting.extend(
        path.name
        for path in evidence.iterdir()
        if path.name.endswith(".tmp")
        and path.name.startswith(temporary_prefixes)
    )
    result_prefix = f".{RESULT_PATH.name}."
    preexisting.extend(
        path.name
        for path in RESULT_PATH.parent.iterdir()
        if path.name.endswith(".tmp") and path.name.startswith(result_prefix)
    )
    if preexisting:
        raise ValueError(
            "pre-existing finalization evidence requires human recovery: "
            + ", ".join(sorted(set(preexisting)))
        )
    marker = {
        "contract_commit": contract_commit,
        "run_id": run_id,
        "started_at": _timestamp(),
        "version": 1,
    }
    encoded = (
        json.dumps(marker, allow_nan=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    if _public_safety_labels(encoded, check_host_paths=True):
        raise ValueError("finalization attempt marker is not public-safe")
    _require_evidence_capacity(evidence, len(encoded), reserve_closure=False)
    _atomic_write_new(evidence / FINALIZATION_ATTEMPT_NAME, encoded)
    _validate_finalization_attempt(
        evidence,
        run_id=run_id,
        contract_commit=contract_commit,
    )


def _finalize_locked(run_id: str, attestation_path: Path, contract_commit: str) -> str:
    finalization_started_at = _timestamp()
    finalization_started_monotonic = time.monotonic()
    if RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise ValueError("invalid run ID")
    contract_commit = _validate_contract_commit(contract_commit)
    evidence = EVIDENCE_ROOT / run_id
    if not evidence.is_dir() or evidence.is_symlink():
        raise ValueError("run evidence directory does not exist")
    _validate_finalization_attempt(
        evidence,
        run_id=run_id,
        contract_commit=contract_commit,
    )
    terminal_paths = (
        evidence / FINALIZATION_COMPLETION_NAME,
        evidence / "settlement.json",
        evidence / "terminal-evidence-index.json",
    )
    preexisting = [
        path.name for path in terminal_paths if path.exists() or path.is_symlink()
    ]
    if preexisting:
        raise ValueError(
            "pre-existing terminal evidence requires human recovery: "
            + ", ".join(preexisting)
        )
    if attestation_path.resolve().is_relative_to(REPOSITORY_ROOT.resolve()):
        raise ValueError("human attestation must be supplied from outside the repository")
    _checkout_guard(contract_commit, allowed_untracked=(evidence, RESULT_PATH))
    _load_candidate_transfer()
    settlement_path = evidence / "settlement.json"

    received_at = finalization_started_at
    pending_valid = False
    pending_detail: str | None = None
    attestation: dict[str, Any] | None = None
    try:
        pending_state, source_files, source_line_counts, service_command = _pending_review_inputs(
            evidence,
            run_id,
            contract_commit,
            allow_terminal=True,
        )
        pending_valid = True
    except (OSError, ValueError, RecursionError, TransferError, json.JSONDecodeError) as exc:
        pending_detail = PENDING_INTEGRITY_FAILURE_DETAIL
        try:
            loaded = _read_json(evidence / "run.json")
        except (OSError, ValueError, RecursionError, json.JSONDecodeError):
            loaded = None
        if _verified_automatic_terminal_generation(
            evidence,
            run_id,
            contract_commit,
            loaded,
            allow_terminal=True,
        ):
            raise ValueError("run is not pending human source review") from exc
        pending_state = _minimal_invalid_pending_state(
            run_id,
            contract_commit,
            received_at,
        )

    if pending_valid:
        raw_attestation = _read_bounded_json(
            attestation_path,
            maximum_bytes=CONTROL_DOCUMENT_MAX_BYTES,
        )
        encoded_attestation = json.dumps(
            raw_attestation, allow_nan=False, ensure_ascii=True, sort_keys=True
        ).encode("utf-8")
        if len(encoded_attestation) > CONTROL_DOCUMENT_MAX_BYTES:
            raise ValueError("canonical human attestation exceeds one MiB")
        if _public_safety_labels(encoded_attestation, check_host_paths=True):
            raise ValueError("human attestation is not public-safe")
        attestation = _validate_attestation(
            raw_attestation,
            pending_state["final_manifest_sha256"],
            pending_state["final_candidate_identity_sha256"],
            source_files,
            service_command,
            source_line_counts,
        )

    _checkout_guard(contract_commit, allowed_untracked=(evidence, RESULT_PATH))
    finalization_elapsed_lower_bound_seconds = (
        time.monotonic() - finalization_started_monotonic
    )
    settlement = _settlement_value(
        evidence=evidence,
        run_id=run_id,
        contract_commit=contract_commit,
        pending_state=pending_state,
        pending_valid=pending_valid,
        pending_detail=pending_detail,
        attestation=attestation,
        received_at=received_at,
        finalization_started_at=finalization_started_at,
        finalization_elapsed_lower_bound_seconds=(
            finalization_elapsed_lower_bound_seconds
        ),
    )
    settlement_bytes = (
        json.dumps(settlement, allow_nan=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    labels = _public_safety_labels(settlement_bytes, check_host_paths=True)
    if labels:
        raise ValueError(
            "terminal settlement is not public-safe: " + ",".join(sorted(labels))
        )
    _validate_settlement(
        settlement,
        evidence=evidence,
        run_id=run_id,
        contract_commit=contract_commit,
    )
    _checkout_guard(contract_commit, allowed_untracked=(evidence, RESULT_PATH))
    _require_evidence_capacity(
        evidence,
        len(settlement_bytes),
        reserve_closure=False,
    )
    _atomic_write_new(settlement_path, settlement_bytes)
    _close_terminal_evidence(evidence, settlement)
    _verify_terminal_index(
        evidence,
        run_id=run_id,
        contract_commit=contract_commit,
        require_completion=False,
    )
    return cast(str, settlement["status"])


def finalize(run_id: str, attestation_path: Path, contract_commit: str) -> int:
    lock_descriptor = _acquire_execution_lock()
    deadline = FinalizationDeadline()
    hard_cutoff = False
    status: str | None = None
    failure: BaseException | None = None
    restore_mask: set[signal.Signals] | None = None

    def observe_failure(exc: BaseException) -> None:
        nonlocal failure, hard_cutoff
        if isinstance(exc, FinalizationHardDeadline):
            hard_cutoff = True
        elif failure is None:
            failure = exc

    try:
        try:
            if RUN_ID_PATTERN.fullmatch(run_id) is None:
                raise ValueError("invalid run ID")
            contract_commit = _validate_contract_commit(contract_commit)
            evidence = EVIDENCE_ROOT / run_id
            _checkout_guard(
                contract_commit,
                allowed_untracked=(evidence, RESULT_PATH),
            )
            try:
                _validate_completion_receipt(
                    evidence,
                    kind="execution",
                    run_id=run_id,
                    contract_commit=contract_commit,
                    verify_index=False,
                )
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError(
                    "execution completion is not machine-closed; human recovery is required"
                ) from exc
            try:
                execution_state = _read_json(evidence / "run.json")
            except (OSError, ValueError, json.JSONDecodeError):
                execution_state = None
            if _verified_automatic_terminal_generation(
                evidence,
                run_id,
                contract_commit,
                execution_state,
            ):
                raise ValueError(
                    "automatic terminal generation does not enter human finalization"
                )
            _begin_finalization_attempt(run_id, contract_commit)
            deadline.install()
            status = _finalize_locked(run_id, attestation_path, contract_commit)
            deadline.complete()
            try:
                _write_completion_receipt(
                    evidence,
                    kind="finalization",
                    run_id=run_id,
                    contract_commit=contract_commit,
                )
                _verify_terminal_index(
                    evidence,
                    run_id=run_id,
                    contract_commit=contract_commit,
                )
            except Exception as exc:
                raise ValueError(
                    "finalization completion is not machine-closed; human recovery is required"
                ) from exc
        except BaseException as exc:
            observe_failure(exc)
    finally:
        try:
            restore_mask = signal.pthread_sigmask(
                signal.SIG_BLOCK,
                {signal.SIGALRM},
            )
            try:
                hard_cutoff = deadline.restore_blocked() or hard_cutoff
            except BaseException as exc:
                observe_failure(exc)
        except BaseException as exc:
            observe_failure(exc)
        finally:
            try:
                os.close(lock_descriptor)
            except BaseException as exc:
                observe_failure(exc)
            finally:
                if restore_mask is not None:
                    try:
                        signal.pthread_sigmask(signal.SIG_SETMASK, restore_mask)
                    except BaseException as exc:
                        observe_failure(exc)
    if hard_cutoff:
        print(
            '{"failure_stage":"finalization_deadline","recovery":"human_required",'
            '"status":"Inconclusive","terminal_evidence":"incomplete"}',
            file=sys.stderr,
        )
        return 2
    if failure is not None:
        raise failure.with_traceback(failure.__traceback__)
    if status is None:
        raise RuntimeError("finalization completed without a terminal status")
    print(json.dumps({"run_id": run_id, "status": status}, sort_keys=True))
    return 0


def plan() -> int:
    sequence = ["clean reviewed contract commit"]
    if LOOP_CANDIDATE_QUALIFICATION_ROOT is not None:
        sequence.append(
            "one exact candidate-boundary qualification outside task-cost measurement; "
            "a started failure closes Inconclusive"
        )
    sequence.extend(
        (
            f"agent-owned {ACTIVE_LOOP.loop_id} setup and zero scoped residue before run clocks or evidence",
            "start run clocks and evidence, then recheck zero scoped residue",
            "exact q1-l1-evaluator fingerprint, dispatch, evaluator, and isolation validation",
            "fresh candidate VM provisioning and boundary probe",
            "stdin API-key login",
            "initial agent invocation",
            "manifested candidate transfer",
            "clean bootstrap, typing, and isolated behavior",
            "one same-thread remediation and complete gate rerun when needed",
            "verify v3 index and append its execution-completion receipt",
            "automatic Rejected or Inconclusive: commit locally",
            "otherwise PendingHumanReview: stop for human attestation",
            "verify v4 index, append its finalization-completion receipt, and commit locally",
        )
    )
    print(
        json.dumps(
            {
                "agent_stack": {
                    "codex_cli": CODEX_VERSION,
                    "model": MODEL,
                    "reasoning_effort": REASONING_EFFORT,
                },
                "experiment": _run_context_record(),
                "agent_budget": {
                    "initial": 1,
                    "remediation": 1,
                    "retries": 0,
                    "same_thread": True,
                },
                "control_limits_bytes": {
                    "argv_aggregate": ARGV_MAX_AGGREGATE_BYTES,
                    "argv_entry": ARGV_MAX_ENTRY_BYTES,
                    "argv_entries": ARGV_MAX_ENTRIES,
                    "completion_prompt_attestation_each": CONTROL_DOCUMENT_MAX_BYTES,
                    "command_stream_each": COMMAND_STREAM_MAX_BYTES,
                    "retained_evidence": RETAINED_EVIDENCE_MAX_BYTES,
                },
                "evaluator": {
                    "instance": EVALUATOR_INSTANCE,
                    "preexisting_only": True,
                    "resource_envelope": {
                        "cpu_equivalents": 4,
                        "memory_bytes": 4 * 1024**3,
                        "pids": 256,
                        "swap_bytes": 0,
                        "writable_state_bytes": 1024**3,
                    },
                },
                "human_gate": "after all non-human gates pass",
                "sequence": sequence,
                "timeouts_seconds": {
                    "agent_guest": AGENT_TIMEOUT_SECONDS,
                    "agent_outer": AGENT_OUTER_TIMEOUT_SECONDS,
                    "automated_execute": AUTOMATED_PHASE_TIMEOUT_SECONDS,
                    "automated_work_before_cleanup_reserve": (
                        AUTOMATED_PHASE_TIMEOUT_SECONDS - CLEANUP_TIMEOUT_SECONDS
                    ),
                    "cleanup_and_pending_closure": CLEANUP_TIMEOUT_SECONDS,
                    "command_default": DEFAULT_COMMAND_TIMEOUT_SECONDS,
                    "human_finalization": FINALIZATION_TIMEOUT_SECONDS,
                    "provisioning": PROVISION_TIMEOUT_SECONDS,
                },
                "transfer_limits": {
                    "depth": 32,
                    "entries": 10_000,
                    "file_bytes": 16 * 1024 * 1024,
                    "manifest_bytes": 8 * 1024 * 1024,
                    "path_bytes": 1024,
                    "total_regular_file_bytes": 128 * 1024 * 1024,
                },
            },
            indent=2,
        )
    )
    return 0


def _qualification_path(root: Path) -> Path:
    absolute = root.absolute()
    expected = (LOOP_ROOT / "build" / "candidate-boundary-qualification").absolute()
    if absolute != expected:
        raise ValueError("qualification root is not owned by the active loop")
    build_root = absolute.parent
    if build_root.exists() and (build_root.is_symlink() or not build_root.is_dir()):
        raise RuntimeError("active-loop build root is not a real directory")
    return absolute


def _qualification_json_lines(path: Path) -> list[dict[str, Any]]:
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_size > CONTROL_DOCUMENT_MAX_BYTES
    ):
        raise ValueError("candidate-boundary command record is invalid")
    try:
        values = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("candidate-boundary command record is invalid") from exc
    if not all(isinstance(value, dict) for value in values):
        raise ValueError("candidate-boundary command record is invalid")
    return cast(list[dict[str, Any]], values)


def _validate_candidate_boundary_commands(root: Path, instance: str) -> None:
    prepare = (
        f"{REDACTED_HOST_REPOSITORY}/"
        + (REPRODUCTION / "prepare-candidate-lima.sh")
        .relative_to(REPOSITORY_ROOT)
        .as_posix()
    )
    expected = (
        ("provision and probe candidate VM", [prepare, instance]),
        ("inspect candidate VM before teardown", ["limactl", "list", "--json"]),
        ("delete candidate VM", ["limactl", "delete", "--force", instance]),
        ("verify candidate VM teardown", ["limactl", "list", "--json"]),
    )
    records = _qualification_json_lines(root / "commands.jsonl")
    record_keys = {
        "argv",
        "category",
        "duration_seconds",
        "finished_at",
        "kind",
        "label",
        "limit_breach",
        "resources",
        "return_code",
        "sequence",
        "started_at",
        "stderr_path",
        "stdout_path",
        "timed_out",
    }
    if len(records) != len(expected):
        raise ValueError("candidate-boundary command sequence is invalid")
    for sequence, (record, (label, argv)) in enumerate(zip(records, expected), start=1):
        duration = record.get("duration_seconds")
        if (
            set(record) != record_keys
            or record.get("kind") != "command"
            or record.get("sequence") != sequence
            or record.get("label") != label
            or record.get("argv") != argv
            or record.get("category") != "machine"
            or record.get("return_code") != 0
            or record.get("timed_out") is not False
            or record.get("limit_breach") is not None
            or not isinstance(duration, (int, float))
            or isinstance(duration, bool)
            or not math.isfinite(duration)
            or duration < 0
        ):
            raise ValueError("candidate-boundary command sequence is invalid")
        for stream in ("stdout_path", "stderr_path"):
            relative_value = record.get(stream)
            relative = (
                PurePosixPath(relative_value)
                if isinstance(relative_value, str)
                else None
            )
            if (
                relative is None
                or relative.is_absolute()
                or not relative.parts
                or any(part in {"", ".", ".."} for part in relative.parts)
                or relative.as_posix() != relative_value
            ):
                raise ValueError("candidate-boundary command stream is invalid")
            path = root.joinpath(*relative.parts)
            if path.is_symlink() or not path.is_file():
                raise ValueError("candidate-boundary command stream is invalid")
    before = {
        value.get("name")
        for value in _qualification_json_lines(
            root / cast(str, records[1]["stdout_path"])
        )
    }
    after = {
        value.get("name")
        for value in _qualification_json_lines(
            root / cast(str, records[3]["stdout_path"])
        )
    }
    if (
        instance not in before
        or EVALUATOR_INSTANCE not in before
        or instance in after
        or EVALUATOR_INSTANCE not in after
    ):
        raise ValueError("candidate-boundary teardown is unproven")


def _validate_candidate_boundary_report(boundary: Any) -> None:
    import verify_candidate_boundary as boundary_authority

    if (
        not isinstance(boundary, dict)
        or set(boundary)
        != {
            "failure",
            "failure_phase",
            "passed",
            "probe",
            "probe_process",
            "provenance",
            "schema_version",
        }
        or boundary.get("schema_version") != 2
        or boundary.get("passed") is not True
        or boundary.get("failure") is not None
        or boundary.get("failure_phase") is not None
        or boundary.get("probe") != EXPECTED_CANDIDATE_BOUNDARY
        or not isinstance(boundary.get("probe_process"), dict)
        or not isinstance(boundary.get("provenance"), dict)
    ):
        raise ValueError("candidate-boundary qualification report did not pass")
    process = boundary["probe_process"]
    if (
        set(process)
        != {
            "encoding",
            "retention_limit_bytes",
            "return_code",
            "stderr",
            "stdout",
        }
        or process.get("encoding") != "utf-8-backslashreplace"
        or process.get("retention_limit_bytes") != 4 * 1024
        or process.get("return_code") != 0
    ):
        raise ValueError("candidate-boundary probe process is invalid")
    for stream_name in ("stdout", "stderr"):
        stream = process.get(stream_name)
        if (
            not isinstance(stream, dict)
            or set(stream) != {"redactions", "text", "truncated"}
            or not isinstance(stream.get("text"), str)
            or len(stream["text"].encode("utf-8")) > 4 * 1024
            or not isinstance(stream.get("truncated"), bool)
            or not isinstance(stream.get("redactions"), list)
        ):
            raise ValueError("candidate-boundary probe stream is invalid")
        for redaction in stream["redactions"]:
            if (
                not isinstance(redaction, dict)
                or set(redaction) != {"count", "item"}
                or not isinstance(redaction.get("count"), int)
                or isinstance(redaction.get("count"), bool)
                or redaction["count"] <= 0
                or redaction.get("item")
                not in {"CANDIDATE_HOME", "HOST_HOME", "HOST_REPOSITORY", "OPENAI_API_KEY"}
            ):
                raise ValueError("candidate-boundary probe redaction is invalid")
    provenance = boundary["provenance"]
    expected_authority = boundary_authority._authority_hashes(ROOT)
    expected_installed = set(boundary_authority.INSTALLED_AUTHORITIES.values())
    expected_runtime = boundary_authority._required_packages(ROOT)
    runtime = provenance.get("candidate_runtime")
    if (
        set(provenance)
        != {
            "authority_sha256",
            "candidate_runtime",
            "codex_cli_required",
            "installed_sha256",
            "lima",
            "permissions_profile",
        }
        or provenance.get("codex_cli_required") != CODEX_VERSION
        or provenance.get("permissions_profile") != "q1_l1"
        or provenance.get("authority_sha256") != expected_authority
        or not isinstance(provenance.get("installed_sha256"), dict)
        or set(provenance["installed_sha256"]) != expected_installed
        or any(
            digest != expected_authority.get(name)
            for name, digest in provenance["installed_sha256"].items()
        )
        or not isinstance(runtime, dict)
        or set(runtime) != {"packages", "python_sha256", "python_version"}
        or runtime.get("python_version") != "3.14.4"
        or re.fullmatch(r"[0-9a-f]{64}", str(runtime.get("python_sha256"))) is None
        or not isinstance(runtime.get("packages"), dict)
        or set(runtime["packages"]) != set(expected_runtime) | {"pip"}
        or any(runtime["packages"].get(name) != version for name, version in expected_runtime.items())
        or not isinstance(runtime["packages"].get("pip"), str)
        or not runtime["packages"]["pip"]
        or provenance.get("lima") != boundary_authority._lima_authority(ROOT)
    ):
        raise ValueError("candidate-boundary provenance is invalid")


def _qualification_accounting(
    root: Path,
    duration_seconds: float,
) -> dict[str, Any]:
    recorded_seconds: float | str = "unknown"
    try:
        records = _qualification_json_lines(root / "commands.jsonl")
        durations = [record.get("duration_seconds") for record in records]
        if all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and value >= 0
            for value in durations
        ):
            recorded_seconds = sum(cast(float, value) for value in durations)
    except (OSError, ValueError, RuntimeError):
        pass
    return {
        "agent": {
            "invocations": 0,
            "model_cost": 0,
            "reason": "qualification uses no API credential or model",
        },
        "candidate_vm": {
            "monetary_cost": "unknown",
            "setup_only": True,
        },
        "evaluator": {
            "acceptance_workload_seconds": 0,
            "residue_probe_seconds": "unknown",
        },
        "human": {
            "active_minutes": "unknown",
            "monetary_cost": "unknown",
        },
        "schema_version": 1,
        "task_measurement_started": False,
        "trusted_machine": {
            "artifact_self_recording_tail_seconds": "unknown",
            "monetary_cost": "unknown",
            "recorded_command_seconds": recorded_seconds,
            "setup_elapsed_lower_bound_seconds": duration_seconds,
        },
        "wall": {
            "post_cutoff_tail_seconds": "unknown",
            "setup_elapsed_lower_bound_seconds": duration_seconds,
            "task_elapsed_seconds": 0,
        },
    }


def _render_failed_qualification_result(report: dict[str, Any]) -> str:
    failures = json.dumps(
        report["failure_categories"],
        ensure_ascii=True,
        sort_keys=True,
    )
    return f"""# {ACTIVE_LOOP.loop_id} result — candidate-boundary qualification

## Observed evidence

- Run: `{report['run_id']}`
- Executable contract commit: `{report['contract_commit']}`
- Model or agent invoked: no
- Task measurement started: no
- Setup evidence: [`evidence/{report['run_id']}`](evidence/{report['run_id']})
- Separate setup ledger: [`evidence/{report['run_id']}/setup-accounting.json`](evidence/{report['run_id']}/setup-accounting.json)

Qualification failure categories: `{failures}`

## Disposition

**Inconclusive.** The exact candidate-boundary qualification failed after its durable attempt marker. {ACTIVE_LOOP.loop_id} cannot execute or retry from this contract.

## Effect on Q1

Q1 gains a reproducible harness finding but no task-cost observation. The failed qualification is not evidence that the frozen workload itself passes or fails.

## Possible next loops

This result authorizes no next loop. Continue only under an existing human-approved troubleshooting sequence; otherwise return the evidence for broad human review.

## Promotion candidate

None. Qualification, loop success, and promotion remain separate human decisions.
"""


def _close_failed_boundary_qualification(
    root: Path,
    report: dict[str, Any],
) -> None:
    run_id = cast(str, report["run_id"])
    terminal_evidence = EVIDENCE_ROOT / run_id
    if terminal_evidence.exists() or terminal_evidence.is_symlink():
        raise RuntimeError("qualification terminal evidence already exists")
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
    os.replace(root, terminal_evidence)
    result = terminal_evidence / "terminal-RESULT.md"
    if result.is_symlink() or not result.is_file():
        raise RuntimeError("qualification terminal result is missing")
    _atomic_write_new(RESULT_PATH, result.read_bytes())
    _assert_public_safe_terminal(terminal_evidence, RESULT_PATH)


def qualify_candidate_boundary(expected_commit: str, root: Path) -> int:
    """Run the exact candidate provisioner and close its setup evidence."""

    expected_commit = _validate_contract_commit(expected_commit)
    root = _qualification_path(root)
    report_path = root / QUALIFICATION_REPORT_NAME
    if root.exists() or root.is_symlink():
        raise RuntimeError("candidate-boundary qualification was already attempted")
    _checkout_guard(expected_commit)
    lock_descriptor = _acquire_execution_lock()
    try:
        _assert_no_orphaned_run()
        if RESULT_PATH.exists():
            raise RuntimeError(f"{ACTIVE_LOOP.loop_id} already has RESULT.md")
        run_id = _run_id()
        instance = _instance_name(run_id)
        started_wall = _utc_now()
        started_monotonic = time.monotonic()
        recorder = Recorder(root)
        _write_json(
            report_path,
            {
                "contract_commit": expected_commit,
                "instance": instance,
                "loop_id": ACTIVE_LOOP.loop_id,
                "run_id": run_id,
                "schema_version": 1,
                "started_at": _timestamp(started_wall),
                "status": "Running",
            },
        )
        failures: list[str] = []
        interrupted: BaseException | None = None
        boundary_validated = False
        try:
            _provision_candidate(recorder, root, instance)
            _validate_candidate_boundary_report(
                _read_bounded_json(
                    root / "boundary-validation.json",
                    maximum_bytes=CONTROL_DOCUMENT_MAX_BYTES,
                )
            )
            boundary_validated = True
        except BaseException as exc:
            interrupted = exc
            failures.append("candidate_boundary_validation")
        cleanup_completed = False
        try:
            cleanup_failures = _cleanup_candidate(recorder, instance, False)
            cleanup_completed = not cleanup_failures
        except BaseException as exc:
            cleanup_failures = [f"candidate cleanup raised {type(exc).__name__}"]
            if interrupted is None:
                interrupted = exc
        if cleanup_failures:
            failures.append("candidate_cleanup")
        command_sequence_validated = False
        try:
            _validate_candidate_boundary_commands(root, instance)
            command_sequence_validated = True
        except (OSError, ValueError, RuntimeError):
            failures.append("candidate_boundary_commands")
        residue_clean = False
        try:
            _assert_no_orphaned_run()
            residue_clean = True
        except (OSError, ValueError, RuntimeError):
            failures.append("post_qualification_residue")
        source_unchanged = False
        try:
            _checkout_guard(expected_commit)
            source_unchanged = True
        except (OSError, ValueError, RuntimeError):
            failures.append("reviewed_source_changed")
        redactions_recorded = False
        try:
            _write_json(root / "redactions.json", recorder.redactions)
            redactions_recorded = True
        except (OSError, ValueError, RuntimeError):
            failures.append("qualification_redactions")
        if any(
            path.is_symlink() or not path.is_file()
            for path in (
                root / "commands.jsonl",
                root / "boundary-validation.json",
                root / "redactions.json",
            )
        ):
            failures.append("qualification_evidence")
        finished_wall = _utc_now()
        duration_seconds = time.monotonic() - started_monotonic
        try:
            _write_json(
                root / "setup-accounting.json",
                _qualification_accounting(root, duration_seconds),
            )
        except (OSError, ValueError, RuntimeError):
            failures.append("qualification_accounting")
        postconditions = {
            "boundary_validated": boundary_validated,
            "candidate_absent_and_evaluator_residue_zero": residue_clean,
            "candidate_cleanup_completed": cleanup_completed,
            "command_sequence_validated": command_sequence_validated,
            "redactions_recorded": redactions_recorded,
            "reviewed_source_unchanged": source_unchanged,
        }
        passed = (
            not failures
            and interrupted is None
            and all(postconditions.values())
        )
        report = {
            "contract_commit": expected_commit,
            "disposition": None if passed else "Inconclusive",
            "duration_seconds": duration_seconds,
            "failure_categories": failures,
            "finished_at": _timestamp(finished_wall),
            "instance": instance,
            "loop_id": ACTIVE_LOOP.loop_id,
            "postconditions": postconditions,
            "redaction_count": len(recorder.redactions),
            "run_id": run_id,
            "schema_version": 1,
            "started_at": _timestamp(started_wall),
            "status": "Passed" if passed else "Failed",
        }
        _write_json(report_path, report)
        if not passed:
            _atomic_write_new(
                root / "terminal-RESULT.md",
                _render_failed_qualification_result(report).encode("utf-8"),
            )
        _assert_public_safe_terminal(root, report_path)
        _write_json(
            root / QUALIFICATION_INDEX_NAME,
            _evidence_index(
                root,
                index_name=QUALIFICATION_INDEX_NAME,
                version=1,
            ),
            reserve_closure=False,
        )
        _write_completion_receipt(
            root,
            kind="qualification",
            run_id=run_id,
            contract_commit=expected_commit,
        )
        _verify_inventory(
            root,
            index_name=QUALIFICATION_INDEX_NAME,
            version=1,
            allowed_extra_paths={QUALIFICATION_COMPLETION_NAME},
        )
        _validate_completion_receipt(
            root,
            kind="qualification",
            run_id=run_id,
            contract_commit=expected_commit,
        )
        _assert_public_safe_terminal(root, report_path)
        if not passed:
            _close_failed_boundary_qualification(root, report)
            print(json.dumps({"run_id": run_id, "status": "Inconclusive"}, sort_keys=True))
            return 2
        print(json.dumps(report, sort_keys=True))
        return 0
    finally:
        os.close(lock_descriptor)


def require_candidate_boundary_qualification(
    root: Path,
    expected_commit: str,
) -> None:
    """Require a closed, passing qualification of the measured provisioner."""

    expected_commit = _validate_contract_commit(expected_commit)
    root = _qualification_path(root)
    report_path = root / QUALIFICATION_REPORT_NAME
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError("candidate-boundary qualification is missing")
    required_paths = (
        report_path,
        root / "commands.jsonl",
        root / "boundary-validation.json",
        root / "redactions.json",
        root / "setup-accounting.json",
        root / QUALIFICATION_INDEX_NAME,
        root / QUALIFICATION_COMPLETION_NAME,
    )
    if any(path.is_symlink() or not path.is_file() for path in required_paths):
        raise RuntimeError("candidate-boundary qualification report is missing")
    report = _read_bounded_json(
        report_path,
        maximum_bytes=CONTROL_DOCUMENT_MAX_BYTES,
    )
    required = {
        "contract_commit",
        "disposition",
        "duration_seconds",
        "failure_categories",
        "finished_at",
        "instance",
        "loop_id",
        "postconditions",
        "redaction_count",
        "run_id",
        "schema_version",
        "started_at",
        "status",
    }
    if (
        not isinstance(report, dict)
        or set(report) != required
        or report.get("schema_version") != 1
        or report.get("loop_id") != ACTIVE_LOOP.loop_id
        or report.get("contract_commit") != expected_commit
        or report.get("disposition") is not None
        or report.get("status") != "Passed"
        or report.get("failure_categories") != []
        or report.get("postconditions")
        != {
            "boundary_validated": True,
            "candidate_absent_and_evaluator_residue_zero": True,
            "candidate_cleanup_completed": True,
            "command_sequence_validated": True,
            "redactions_recorded": True,
            "reviewed_source_unchanged": True,
        }
        or not isinstance(report.get("redaction_count"), int)
        or isinstance(report.get("redaction_count"), bool)
        or report["redaction_count"] < 0
        or not isinstance(report.get("duration_seconds"), (int, float))
        or isinstance(report.get("duration_seconds"), bool)
        or not math.isfinite(report["duration_seconds"])
        or report["duration_seconds"] < 0
        or not isinstance(report.get("started_at"), str)
        or not isinstance(report.get("finished_at"), str)
        or not isinstance(report.get("run_id"), str)
        or RUN_ID_PATTERN.fullmatch(report["run_id"]) is None
        or not isinstance(report.get("instance"), str)
        or report["instance"] != _instance_name(report["run_id"])
    ):
        raise RuntimeError("candidate-boundary qualification did not pass this contract")
    _validate_completion_receipt(
        root,
        kind="qualification",
        run_id=report["run_id"],
        contract_commit=expected_commit,
    )
    _verify_inventory(
        root,
        index_name=QUALIFICATION_INDEX_NAME,
        version=1,
        allowed_extra_paths={QUALIFICATION_COMPLETION_NAME},
    )
    redactions = _read_bounded_json(
        root / "redactions.json",
        maximum_bytes=CONTROL_DOCUMENT_MAX_BYTES,
    )
    if not isinstance(redactions, list) or len(redactions) != report["redaction_count"]:
        raise RuntimeError("candidate-boundary redaction record is invalid")
    accounting = _read_bounded_json(
        root / "setup-accounting.json",
        maximum_bytes=CONTROL_DOCUMENT_MAX_BYTES,
    )
    if (
        not isinstance(accounting, dict)
        or accounting.get("schema_version") != 1
        or accounting.get("task_measurement_started") is not False
        or not isinstance(accounting.get("agent"), dict)
        or accounting["agent"].get("invocations") != 0
        or accounting["agent"].get("model_cost") != 0
        or not isinstance(accounting.get("evaluator"), dict)
        or accounting["evaluator"].get("acceptance_workload_seconds") != 0
        or not isinstance(accounting.get("wall"), dict)
        or accounting["wall"].get("task_elapsed_seconds") != 0
    ):
        raise RuntimeError("candidate-boundary setup accounting is invalid")
    _validate_candidate_boundary_commands(root, report["instance"])
    boundary = _read_bounded_json(
        root / "boundary-validation.json",
        maximum_bytes=CONTROL_DOCUMENT_MAX_BYTES,
    )
    _validate_candidate_boundary_report(boundary)
    _assert_public_safe_terminal(root, report_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            f"Execute the approved {ACTIVE_LOOP.loop_id} workflow or finalize its "
            "human review gate."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan", help="print the approved sequence without changing state")
    if LOOP_CANDIDATE_QUALIFICATION_ROOT is not None:
        qualify_parser = subparsers.add_parser(
            "qualify",
            help="qualify the exact candidate boundary outside task-cost measurement",
        )
        qualify_parser.add_argument("--contract-commit", required=True)
    execute_parser = subparsers.add_parser(
        "execute", help="execute through the human source-review boundary"
    )
    execute_parser.add_argument("--contract-commit", required=True)
    finalize_parser = subparsers.add_parser("finalize", help="record the explicit human gate")
    finalize_parser.add_argument("--run-id", required=True)
    finalize_parser.add_argument("--attestation", type=Path, required=True)
    finalize_parser.add_argument("--contract-commit", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "plan":
            return plan()
        if args.command == "qualify":
            if LOOP_CANDIDATE_QUALIFICATION_ROOT is None:
                raise RuntimeError("active loop has no candidate-boundary qualification")
            return qualify_candidate_boundary(
                args.contract_commit,
                LOOP_CANDIDATE_QUALIFICATION_ROOT,
            )
        if args.command == "execute":
            return execute(args.contract_commit)
        return finalize(args.run_id, args.attestation, args.contract_commit)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
