"""No host authority: PID-namespace lifetime guard for the fixed fixture."""

import os
import signal
import subprocess
import sys

child = subprocess.Popen(
    [sys.executable, "-I", "/fixture/program.py", sys.argv[1]],
    stdin=sys.stdin,
    start_new_session=True,
)
try:
    result = child.wait(timeout=float(sys.argv[2]))
except subprocess.TimeoutExpired:
    os.killpg(child.pid, signal.SIGKILL)
    child.wait()
    result = 124
raise SystemExit(result)
