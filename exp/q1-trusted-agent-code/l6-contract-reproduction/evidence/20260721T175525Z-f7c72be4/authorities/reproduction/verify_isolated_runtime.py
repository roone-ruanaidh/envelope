"""Validate the production isolation wrapper with the evaluator reference."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
for import_root in (ROOT, ROOT / "reproduction"):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from candidate_transfer import build_manifest
from evaluator import candidate_exec


FIXTURE = ROOT / "evaluator" / "fixtures" / "service.py"
SERVICE_PROBE = ROOT / "reproduction" / "isolation_probe_service.py"
REQUIREMENTS = ROOT / "public" / "contract" / "python-arm-requirements.v1.txt"
APPROVED_CPU_MAX = "400000 100000"
APPROVED_MEMORY_MAX_BYTES = 4 * 1024**3
APPROVED_MEMORY_SWAP_MAX_BYTES = 0
APPROVED_MEMORY_OOM_GROUP = 1
APPROVED_PIDS_MAX = 256
APPROVED_WRITABLE_STATE_BYTES = 1024**3
APPROVED_MOUNT_OPTIONS = ("nodev", "noexec", "nosuid", "rw")
SERVICE_MOUNT_MARKER = "q1-l1-service-mount-options="
TRUSTED_MODULE_RUNNER = (
    'import runpy,sys;sys.path.insert(0,".");'
    'module=sys.argv.pop(1);runpy.run_module(module,run_name="__main__")'
)
CPU_LIMIT_PROBE = """import os,time
children=[]
for _ in range(6):
    child=os.fork()
    if child == 0:
        deadline=time.monotonic()+0.5
        while time.monotonic() < deadline:
            pass
        os._exit(0)
    children.append(child)
for child in children:
    os.waitpid(child,0)
"""
PIDS_LIMIT_PROBE = f"""import subprocess
children=[]
try:
    for _ in range({APPROVED_PIDS_MAX + 32}):
        children.append(subprocess.Popen(['/usr/bin/sleep','30']))
except OSError:
    pass
finally:
    for child in children:
        child.terminate()
    for child in children:
        child.wait()
"""


def _mount_assertion(paths: tuple[str, str]) -> str:
    """Return trusted guest code that reports only approved mount facts."""

    return (
        "import json,os\n"
        f"paths={paths!r}\n"
        f"required={APPROVED_MOUNT_OPTIONS!r}\n"
        "matches={path:[] for path in paths}\n"
        "with open('/proc/self/mountinfo',encoding='ascii') as stream:\n"
        " for line in stream:\n"
        "  fields=line.split()\n"
        "  if len(fields)<10 or '-' not in fields:\n"
        "   raise RuntimeError('malformed mountinfo')\n"
        "  separator=fields.index('-')\n"
        "  if separator<6 or separator+3>=len(fields):\n"
        "   raise RuntimeError('malformed mountinfo separator')\n"
        "  if fields[4] in matches:\n"
        "   options=set(fields[5].split(','))\n"
        "   matches[fields[4]].append(tuple(sorted(options.intersection(required))))\n"
        "if any(len(matches[path])!=1 or matches[path][0]!=required for path in paths):\n"
        " raise RuntimeError('required writable mount options are absent or ambiguous')\n"
        "mount_options={path:list(matches[path][0]) for path in paths}\n"
    )


ISOLATED_COMMAND_STATE_ASSERTION = _mount_assertion(("/tmp", "/q1-l1-state")) + (
    "stats=[os.statvfs(path) for path in paths]\n"
    "print(json.dumps({'capacities':[item.f_blocks*item.f_frsize for item in stats],"
    "'mount_options':mount_options,"
    "'same_filesystem':os.stat(paths[0]).st_dev==os.stat(paths[1]).st_dev},sort_keys=True))\n"
)
SERVICE_STATE_ASSERTION = _mount_assertion(("/tmp", "/state")) + (
    "stats=[os.statvfs(path) for path in paths]\n"
    f"if any(item.f_blocks*item.f_frsize>{APPROVED_WRITABLE_STATE_BYTES} for item in stats):\n"
    " raise RuntimeError('writable-state capacity exceeds one GiB')\n"
    "if os.stat(paths[0]).st_dev!=os.stat(paths[1]).st_dev:\n"
    " raise RuntimeError('service writable paths are not one filesystem')\n"
    f"print({SERVICE_MOUNT_MARKER!r}+json.dumps(mount_options,sort_keys=True,separators=(',',':')),flush=True)\n"
    "import runpy\n"
    "runpy.run_path('/work/isolation_probe_service.py',run_name='__main__')\n"
)
IGNORING_SERVICE_STATE_ASSERTION = SERVICE_STATE_ASSERTION.replace(
    "import runpy\n",
    "os.environ['Q1_L1_FIXTURE_MODE']='ignore_sigterm'\nimport runpy\n",
)
RUNTIME_RESIDUE_PROBE = """import glob,json,pathlib
counts={'cgroups':len(glob.glob('/sys/fs/cgroup/**/q1-l1-candidate-*',recursive=True)),
        'loops':0,'mounts':0}
for backing in glob.glob('/sys/block/loop*/loop/backing_file'):
 try: value=pathlib.Path(backing).read_bytes()
 except OSError: continue
 if b'/tmp/q1-l1-run-' in value: counts['loops']+=1
for process in pathlib.Path('/proc').iterdir():
 if not process.name.isdigit(): continue
 try: value=(process/'mountinfo').read_bytes()
 except OSError: continue
 if b'/tmp/q1-l1-run-' in value: counts['mounts']+=1
print(json.dumps(counts,sort_keys=True))
"""


def _production_limit_exports_match() -> bool:
    missing = object()
    actual = (
        getattr(candidate_exec, "CPU_MAX", missing),
        getattr(candidate_exec, "MEMORY_MAX_BYTES", missing),
        getattr(candidate_exec, "MEMORY_SWAP_MAX_BYTES", missing),
        getattr(candidate_exec, "MEMORY_OOM_GROUP", missing),
        getattr(candidate_exec, "PIDS_MAX", missing),
        getattr(candidate_exec, "WRITABLE_STATE_BYTES", missing),
    )
    approved = (
        APPROVED_CPU_MAX,
        APPROVED_MEMORY_MAX_BYTES,
        APPROVED_MEMORY_SWAP_MAX_BYTES,
        APPROVED_MEMORY_OOM_GROUP,
        APPROVED_PIDS_MAX,
        APPROVED_WRITABLE_STATE_BYTES,
    )
    return all(
        type(observed) is type(expected) and observed == expected
        for observed, expected in zip(actual, approved, strict=True)
    )


def _service_mount_options_valid(log_tail: object) -> bool:
    if not isinstance(log_tail, str):
        return False
    encoded = [
        line.removeprefix(SERVICE_MOUNT_MARKER)
        for line in log_tail.splitlines()
        if line.startswith(SERVICE_MOUNT_MARKER)
    ]
    if not encoded:
        return False
    try:
        observed = [json.loads(value) for value in encoded]
    except json.JSONDecodeError:
        return False
    expected = {
        "/state": list(APPROVED_MOUNT_OPTIONS),
        "/tmp": list(APPROVED_MOUNT_OPTIONS),
    }
    return all(value == expected for value in observed)


def _public_command_state_observation(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict) or set(value) != {
        "capacities",
        "mount_options",
        "same_filesystem",
    }:
        return None
    capacities = value["capacities"]
    expected_mounts = {
        "/q1-l1-state": list(APPROVED_MOUNT_OPTIONS),
        "/tmp": list(APPROVED_MOUNT_OPTIONS),
    }
    if (
        not isinstance(capacities, list)
        or len(capacities) != 2
        or not all(type(capacity) is int and capacity >= 0 for capacity in capacities)
        or value["mount_options"] != expected_mounts
        or type(value["same_filesystem"]) is not bool
    ):
        return None
    return {
        "capacities": capacities,
        "mount_options": expected_mounts,
        "same_filesystem": value["same_filesystem"],
    }


def _write_report(report_path: Path, report: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _isolated_command(candidate: Path, *command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-B",
            "-I",
            "-c",
            TRUSTED_MODULE_RUNNER,
            "evaluator.isolated_command",
            "--candidate-root",
            str(candidate),
            "--",
            *command,
        ],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _raw_wrapper_setup_failure(candidate: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "/usr/bin/sudo",
            "/usr/bin/unshare",
            "--net",
            "--fork",
            "/usr/bin/env",
            "Q1_L1_OUTER_NETNS=1",
            sys.executable,
            "-B",
            "-I",
            "-c",
            TRUSTED_MODULE_RUNNER,
            "evaluator.isolated_command",
            "--inside-netns",
            "--candidate-root",
            str(candidate / "missing-wrapper-fixture"),
            "--",
            "true",
        ],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _runtime_residue_counts() -> dict[str, int] | None:
    completed = subprocess.run(
        [
            "/usr/bin/sudo",
            "/usr/bin/python3.14",
            "-B",
            "-I",
            "-c",
            RUNTIME_RESIDUE_PROBE,
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None
    expected = {"cgroups", "loops", "mounts"}
    if (
        completed.returncode != 0
        or not isinstance(value, dict)
        or set(value) != expected
        or not all(type(value[key]) is int and value[key] >= 0 for key in expected)
    ):
        return None
    return value


def verify(report_path: Path) -> dict[str, Any]:
    if not _production_limit_exports_match():
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "passed": False,
            "production_limit_exports_match": False,
        }
        _write_report(report_path, report)
        return report

    with tempfile.TemporaryDirectory(prefix="q1-l1-isolation-validation-") as temporary:
        temporary_root = Path(temporary)
        temporary_root.chmod(0o755)
        candidate = temporary_root / "candidate"
        candidate.mkdir()
        shutil.copy2(FIXTURE, candidate / "service.py")
        shutil.copy2(SERVICE_PROBE, candidate / "isolation_probe_service.py")
        (candidate / "mypy.py").write_text("print('fake-mypy-loaded')\n", encoding="utf-8")
        (candidate / "sitecustomize.py").write_text(
            "print('fake-sitecustomize-loaded')\n", encoding="utf-8"
        )
        subprocess.run(
            ["/usr/bin/python3.14", "-B", "-I", "-m", "venv", str(candidate / ".venv")],
            check=True,
        )
        subprocess.run(
            [
                str(candidate / ".venv" / "bin" / "python"),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-cache-dir",
                "--no-deps",
                "--requirement",
                str(REQUIREMENTS),
            ],
            check=True,
        )
        subprocess.run(
            [str(candidate / ".venv" / "bin" / "python"), "-m", "pip", "check"],
            check=True,
        )
        before = build_manifest(candidate)
        service_command = ["python3", "-c", SERVICE_STATE_ASSERTION, str(ROOT)]
        completion = Path(temporary) / "completion.json"
        completion.write_text(
            json.dumps(
                {"service_command": service_command, "status": "declared_complete"},
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        candidate_report = Path(temporary) / "candidate-report.json"
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                "-I",
                "-c",
                TRUSTED_MODULE_RUNNER,
                "evaluator.rerun",
                "--candidate-root",
                str(candidate),
                "--candidate-completion",
                str(completion),
                "--report",
                str(candidate_report),
            ],
            cwd=ROOT,
            check=False,
        )
        observed = json.loads(candidate_report.read_text(encoding="utf-8"))
        ignoring_command = [
            "python3",
            "-c",
            IGNORING_SERVICE_STATE_ASSERTION,
            str(ROOT),
        ]
        ignoring_completion = Path(temporary) / "ignoring-completion.json"
        ignoring_completion.write_text(
            json.dumps(
                {"service_command": ignoring_command, "status": "declared_complete"},
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        ignoring_report_path = Path(temporary) / "ignoring-report.json"
        ignoring_completed = subprocess.run(
            [
                sys.executable,
                "-B",
                "-I",
                "-c",
                TRUSTED_MODULE_RUNNER,
                "evaluator.rerun",
                "--candidate-root",
                str(candidate),
                "--candidate-completion",
                str(ignoring_completion),
                "--report",
                str(ignoring_report_path),
            ],
            cwd=ROOT,
            check=False,
        )
        ignoring_observed = json.loads(ignoring_report_path.read_text(encoding="utf-8"))
        command_probe = _isolated_command(
            candidate,
            "python3",
            "-c",
            "import pathlib,sys; assert sys.executable.startswith('/work/.venv/'); "
            f"assert not pathlib.Path({str(ROOT)!r}).exists(); print('isolated-command-ok')",
        )
        shadow_probe = _isolated_command(candidate, "python3", "-m", "mypy", "--version")
        capacity_probe = _isolated_command(
            candidate,
            "python3",
            "-c",
            ISOLATED_COMMAND_STATE_ASSERTION,
        )
        try:
            capacity_observed = _public_command_state_observation(
                json.loads(capacity_probe.stdout)
            )
        except json.JSONDecodeError:
            capacity_observed = None
        cpu_limit_probe = _isolated_command(candidate, "python3", "-c", CPU_LIMIT_PROBE)
        memory_limit_probe = _isolated_command(
            candidate,
            "python3",
            "-c",
            f"bytearray({APPROVED_MEMORY_MAX_BYTES + 64 * 1024**2})",
        )
        pids_limit_probe = _isolated_command(candidate, "python3", "-c", PIDS_LIMIT_PROBE)
        candidate_125 = _isolated_command(
            candidate,
            "sh",
            "-c",
            "rm -f /q1-l1-state/entry.sock; exit 125",
        )
        isolation_125 = _raw_wrapper_setup_failure(candidate)

        descendant_marker = f"q1-l1-descendant-{uuid.uuid4().hex}"
        descendant_probe = _isolated_command(
            candidate,
            "python3",
            "-c",
            "import subprocess,sys; subprocess.Popen([sys.executable,'-c',"
            "'import time; time.sleep(300)',sys.argv[1]],start_new_session=True)",
            descendant_marker,
        )
        descendant_survived = True
        for _attempt in range(20):
            processes = subprocess.run(
                ["/usr/bin/ps", "-eo", "args="],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout
            descendant_survived = descendant_marker in processes
            if not descendant_survived:
                break
            time.sleep(0.05)
        runtime_residue = _runtime_residue_counts()
        after = build_manifest(candidate)
        service_mount_options_valid = _service_mount_options_valid(
            observed.get("service_log_tail")
        )
        passed = (
            completed.returncode == 0
            and observed.get("passed") is True
            and observed.get("infrastructure_failure") is False
            and observed.get("candidate_service_command") == service_command
            and '"candidate_external_route": "blocked"' in observed.get("service_log_tail", "")
            and command_probe.returncode == 0
            and command_probe.stdout.strip() == "isolated-command-ok"
            and shadow_probe.returncode == 0
            and shadow_probe.stdout.strip().startswith("mypy 2.2.0 ")
            and "fake-mypy-loaded" not in shadow_probe.stdout + shadow_probe.stderr
            and "fake-sitecustomize-loaded" not in shadow_probe.stdout + shadow_probe.stderr
            and capacity_probe.returncode == 0
            and isinstance(capacity_observed, dict)
            and capacity_observed.get("same_filesystem") is True
            and capacity_observed.get("capacities")
            == [APPROVED_WRITABLE_STATE_BYTES, APPROVED_WRITABLE_STATE_BYTES]
            and capacity_observed.get("mount_options")
            == {
                "/q1-l1-state": list(APPROVED_MOUNT_OPTIONS),
                "/tmp": list(APPROVED_MOUNT_OPTIONS),
            }
            and service_mount_options_valid
            and cpu_limit_probe.returncode == 125
            and "4-CPU quota was reached" in cpu_limit_probe.stderr
            and memory_limit_probe.returncode == 125
            and "4-GiB memory limit was reached" in memory_limit_probe.stderr
            and pids_limit_probe.returncode == 125
            and "256-task limit was reached" in pids_limit_probe.stderr
            and candidate_125.returncode == 1
            and isolation_125.returncode == 125
            and descendant_probe.returncode == candidate_exec.FOREGROUND_VIOLATION_EXIT
            and "declared foreground command left a surviving process"
            in descendant_probe.stderr
            and not descendant_survived
            and ignoring_completed.returncode == 1
            and ignoring_observed.get("passed") is False
            and ignoring_observed.get("infrastructure_failure") is False
            and ignoring_observed.get("failure_class") == "candidate_failure"
            and ignoring_observed.get("candidate_service_command") == ignoring_command
            and runtime_residue == {"cgroups": 0, "loops": 0, "mounts": 0}
            and before == after
        )
        report = {
            "candidate_acceptance": observed,
            "command_probe": {
                "return_code": command_probe.returncode,
                "stderr": command_probe.stderr,
                "stdout": command_probe.stdout,
            },
            "candidate_exit_125_probe": {
                "return_code": candidate_125.returncode,
                "stderr": candidate_125.stderr,
            },
            "cpu_limit_probe": {
                "return_code": cpu_limit_probe.returncode,
                "stderr": cpu_limit_probe.stderr,
            },
            "memory_limit_probe": {
                "return_code": memory_limit_probe.returncode,
                "stderr": memory_limit_probe.stderr,
            },
            "pids_limit_probe": {
                "return_code": pids_limit_probe.returncode,
                "stderr": pids_limit_probe.stderr,
            },
            "writable_state_probe": {
                "observed": capacity_observed,
                "return_code": capacity_probe.returncode,
                "stderr": capacity_probe.stderr,
            },
            "descendant_cleanup_probe": {
                "return_code": descendant_probe.returncode,
                "stderr": descendant_probe.stderr,
                "survived": descendant_survived,
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "ignored_sigterm_probe": {
                "candidate_acceptance": ignoring_observed,
                "rerun_return_code": ignoring_completed.returncode,
            },
            "passed": passed,
            "production_limit_exports_match": True,
            "rerun_return_code": completed.returncode,
            "runtime_residue_after_forced_candidate_stop": runtime_residue,
            "service_writable_mount_probe": {
                "observed_required_options": (
                    {
                        "/state": list(APPROVED_MOUNT_OPTIONS),
                        "/tmp": list(APPROVED_MOUNT_OPTIONS),
                    }
                    if service_mount_options_valid
                    else None
                ),
                "passed": service_mount_options_valid,
            },
            "source_unchanged": before == after,
            "typing_shadow_probe": {
                "return_code": shadow_probe.returncode,
                "stderr": shadow_probe.stderr,
                "stdout": shadow_probe.stdout,
            },
            "wrapper_exit_125_probe": {
                "return_code": isolation_125.returncode,
                "stderr": isolation_125.stderr,
                "stdout": isolation_125.stdout,
            },
        }
    _write_report(report_path, report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    report_path = Path(argv[0]) if argv else ROOT / "build" / "isolation-validation.json"
    try:
        report = verify(report_path)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(json.dumps({"passed": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
