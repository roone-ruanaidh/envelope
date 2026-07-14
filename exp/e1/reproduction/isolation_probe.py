"""Probe the proposed candidate runtime's filesystem and network boundary."""

from __future__ import annotations

import socket
from pathlib import Path


assert not Path("/Users/engineer/ws/ev/exp/e1/evaluator").exists()

listener = socket.socket()
listener.bind(("127.0.0.1", 0))
listener.close()

external = socket.socket()
external.settimeout(0.1)
assert external.connect_ex(("1.1.1.1", 80)) != 0
external.close()

print("root-netns-mountns-ok")
