"""Bounded foundation host signal probes; fresh scopes differ from within-scope repetition."""

import argparse
import json
import os
import subprocess
import sys
import tempfile

CHILD = r"""
import json, os, signal, sys, threading, time

if sys.argv[4]:
    sys.path.insert(0, os.path.join(sys.argv[4], "src"))
import mobiraeon.cli as cli

mode, first, second = sys.argv[1:4]
first, second = getattr(signal, first), getattr(signal, second)
stop = threading.Event()
real_signal = signal.signal
previous = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)}
depth = 0
nested = False
actual = None


def emit(record):
    os.write(1, (json.dumps(record) + "\n").encode())


emit({"implementation": cli.__file__, "mode": mode})


def install(signum, handler):
    global actual
    if (
        callable(handler)
        and getattr(handler, "__name__", None) == "request_stop"
        and getattr(handler, "__module__", None) == cli.__name__
    ):
        actual = handler

        def observed(number, frame):
            global depth
            depth += 1
            level = depth
            emit({"event": "enter", "depth": level, "signal": signal.Signals(number).name})
            try:
                return handler(number, frame)
            finally:
                emit({"event": "return", "depth": level, "signal": signal.Signals(number).name})
                depth -= 1

        return real_signal(signum, observed)
    return real_signal(signum, handler)


signal.signal = install


def trace(frame, event, arg):
    global nested
    if (
        mode == "nested"
        and not nested
        and event == "line"
        and depth == 1
        and (
            (
                frame.f_code is threading.Event.set.__code__
                and frame.f_locals.get("self") is stop
                and stop._cond._is_owned()
            )
            or (frame.f_code is actual.__code__ and "set" not in actual.__code__.co_names)
        )
    ):
        nested = True
        emit(
            {
                "event": "schedule_nested",
                "window": "actual production handler or Event Condition-owned window",
            }
        )
        signal.raise_signal(second)
    return trace


if mode == "nested":
    sys.settrace(trace)


def run_once(number):
    timer = threading.Timer(
        0.05, lambda: stop.set() if mode == "external" else signal.raise_signal(number)
    )
    timer.start()
    cli.serve(stop)
    timer.join(timeout=1)
    assert not timer.is_alive()
    assert stop.is_set()
    assert all(signal.getsignal(s) == handler for s, handler in previous.items())


if mode == "spaced_scopes":
    for i in range(3):
        stop.clear()
        run_once(first if i % 2 == 0 else second)
        time.sleep(0.05)
else:
    run_once(first)
sys.settrace(None)
emit(
    {
        "completed": True,
        "nested_scheduled": nested,
        "pending": stop.is_set(),
        "restored": all(signal.getsignal(s) == h for s, h in previous.items()),
    }
)
"""

CASES = [
    ("single", "SIGINT", "SIGTERM"),
    ("single", "SIGTERM", "SIGINT"),
    ("nested", "SIGINT", "SIGINT"),
    ("nested", "SIGINT", "SIGTERM"),
    ("nested", "SIGTERM", "SIGINT"),
    ("nested", "SIGTERM", "SIGTERM"),
    ("spaced_scopes", "SIGTERM", "SIGINT"),
    ("external", "SIGINT", "SIGTERM"),
]


def run_case(mode, first, second, *, python=sys.executable, source_root=None, deadline=4):
    environment = {k: v for k, v in os.environ.items() if not k.startswith("MOBIRAEON_")}
    environment.pop("PYTHONPATH", None)
    command = [str(python), "-c", CHILD, mode, first, second, str(source_root or "")]
    with tempfile.TemporaryDirectory(prefix="mobiraeon-signal-probe-") as outside:
        process = subprocess.Popen(
            command,
            cwd=outside,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        timed_out = False
        try:
            stdout, stderr = process.communicate(timeout=deadline)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            stdout, stderr = process.communicate(timeout=3)
    records = [json.loads(line) for line in stdout.splitlines()]
    completed = next((r for r in records if r.get("completed")), None)
    entries = [r for r in records if r.get("event") == "enter"]
    returns = [r for r in records if r.get("event") == "return"]
    nested = any(r["depth"] == 2 for r in entries)
    passed = (
        not timed_out
        and process.returncode == 0
        and completed is not None
        and completed["pending"]
        and completed["restored"]
        and len(entries)
        == len(returns)
        == (
            0
            if mode == "external"
            else 3
            if mode == "spaced_scopes"
            else 2
            if mode == "nested"
            else 1
        )
        and (
            mode != "nested"
            or (
                completed["nested_scheduled"]
                and nested
                and [r["depth"] for r in returns] == [2, 1]
            )
        )
    )
    return {
        "mode": mode,
        "first": first,
        "second": second,
        "command": command,
        "timed_out": timed_out,
        "exit_code": process.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "records": records,
        "nested_delivery_observed": nested,
        "handler_entries": len(entries),
        "handler_returns": len(returns),
        "reaped": process.poll() is not None,
        "result": "passed" if passed else "failed",
    }


def exercise(*, python=sys.executable, source_root=None):
    checks = [run_case(*case, python=python, source_root=source_root) for case in CASES]
    return {
        "result": "passed" if all(c["result"] == "passed" for c in checks) else "failed",
        "scheduling": (
            "Nested cases select a deterministic window; fresh-scope controls are untraced. "
            "No occurrence rate is claimed."
        ),
        "checks": checks,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-python", default=sys.executable)
    parser.add_argument("--source-root")
    args = parser.parse_args()
    result = exercise(python=args.target_python, source_root=args.source_root)
    print(json.dumps(result, indent=2))
    return int(result["result"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
