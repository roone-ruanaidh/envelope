"""Verify that process-group SIGTERM remains a clean exit through bubblewrap."""

from __future__ import annotations

import os
import json
import signal
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
probe = ROOT / "reproduction" / "signal_probe.py"
info_read, info_write = os.pipe()
command = [
    "bwrap",
    "--ro-bind",
    "/usr",
    "/usr",
    "--ro-bind",
    "/lib",
    "/lib",
    "--ro-bind",
    str(probe),
    "/probe.py",
    "--proc",
    "/proc",
    "--dev",
    "/dev",
    "--tmpfs",
    "/tmp",
    "--unshare-user",
    "--unshare-pid",
    "--unshare-ipc",
    "--unshare-uts",
    "--unshare-cgroup-try",
    "--die-with-parent",
    "--as-pid-1",
    "--info-fd",
    str(info_write),
    "--uid",
    "65534",
    "--gid",
    "65534",
    "/usr/bin/python3",
    "/probe.py",
]
process = subprocess.Popen(
    command,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    start_new_session=True,
    pass_fds=(info_write,),
)
os.close(info_write)
with os.fdopen(info_read, encoding="utf-8") as info_stream:
    sandbox_info = json.load(info_stream)
child_pid = sandbox_info.get("child-pid")
if not isinstance(child_pid, int):
    raise RuntimeError(f"bubblewrap did not report child-pid: {sandbox_info!r}")
if process.stdout is None:
    raise RuntimeError("probe stdout was not captured")
if process.stdout.readline().strip() != "ready":
    raise RuntimeError("isolated signal probe did not become ready")
os.kill(child_pid, signal.SIGTERM)
return_code = process.wait(timeout=2)
if return_code != 0:
    stderr = "" if process.stderr is None else process.stderr.read()
    raise RuntimeError(f"isolated SIGTERM returned {return_code}: {stderr}")
print("isolated-sigterm-zero-ok")
