"""Fixed fixture. Extra probe modes are only selected by trusted test composition."""

import hashlib
import json
import os
import signal
import subprocess
import sys
import time

mode = sys.argv[1]
content = sys.stdin.buffer.read()
text = content.decode("utf-8")
if mode == "success":
    print(
        json.dumps(
            {
                "schema": "fixture-summary-v1",
                "input_sha256": hashlib.sha256(content).hexdigest(),
                "utf8_bytes": len(content),
                "characters": len(text),
                "lines": len(text.splitlines()),
                "words": len(text.split()),
            },
            separators=(",", ":"),
        ),
        flush=True,
    )
elif mode == "failure":
    print("fixture failure", file=sys.stderr, flush=True)
    sys.exit(1)
elif mode == "stubborn_child":
    subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(600)",
        ]
    )
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    while True:
        time.sleep(0.1)
elif mode == "excess_output":
    while True:
        os.write(1, b"x" * 4096)
elif mode == "invalid":
    print('{"schema":"wrong"}', flush=True)
elif mode == "partial":
    print('{"schema":', flush=True)
elif mode == "cpu":
    while True:
        pass
elif mode == "memory":
    blocks = []
    while True:
        blocks.append(bytearray(1024 * 1024))
elif mode == "pids":
    while True:
        if os.fork() == 0:
            time.sleep(600)
            os._exit(0)
elif mode in {"scratch", "scratch_shm"}:
    with open(
        "/tmp/overflow" if mode == "scratch" else "/dev/shm/overflow", "wb", buffering=0
    ) as output:
        while True:
            output.write(b"x" * (1024 * 1024))
elif mode == "controls":
    import socket

    failures = {}
    for path in ("/forbidden", "/etc/hosts"):
        try:
            with open(path, "wb") as output:
                output.write(b"forbidden")
        except OSError:
            failures[path] = True
    try:
        socket.create_connection(("1.1.1.1", 80), timeout=0.5)
        network_blocked = False
    except OSError:
        network_blocked = True
    print(
        json.dumps(
            {
                "uid": os.getuid(),
                "write_refused": failures,
                "network_blocked": network_blocked,
                "socket_absent": not os.path.exists("/var/run/docker.sock"),
                "environment": sorted(os.environ),
                "cgroup": {
                    name: open("/sys/fs/cgroup/" + name).read().strip()
                    for name in ("cpu.max", "memory.max", "memory.swap.max", "pids.max")
                },
            }
        ),
        flush=True,
    )
else:
    while True:
        time.sleep(0.1)
