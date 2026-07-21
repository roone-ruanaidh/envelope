"""Exit zero on SIGTERM for the isolated lifecycle probe."""

from __future__ import annotations

import signal
import time


def stop(_signum: int, _frame: object) -> None:
    raise SystemExit(0)


signal.signal(signal.SIGTERM, stop)
print("ready", flush=True)
while True:
    time.sleep(1)
