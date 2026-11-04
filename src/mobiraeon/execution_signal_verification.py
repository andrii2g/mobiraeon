"""Bounded signal reentrancy probes; tracing selects a window, never an occurrence rate."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time

CHILD = r"""
import dis,json,os,signal,sys,threading,time
def emit(record):
    # Test instrumentation only: no TextIO lock held across production calls.
    os.write(1,(json.dumps(record)+"\n").encode())
if sys.argv[4]:
    sys.path.insert(0, os.path.join(sys.argv[4], "src"))
emit({"timing":"before_execution_import","monotonic_ns":time.monotonic_ns()})
import mobiraeon.execution as execution
emit({"timing":"after_execution_import","monotonic_ns":time.monotonic_ns()})

mode, first, second = sys.argv[1:4]
first, second = getattr(signal, first), getattr(signal, second)
previous = {s: signal.getsignal(s) for s in (signal.SIGINT,signal.SIGTERM)}
events=[]
depth=0
fired=False
emit({"implementation":execution.__file__})
with execution.execution_signals() as interruption:
    actual=signal.getsignal(first)
    assert callable(actual) and signal.getsignal(second) is actual
    calls=[i.opname for i in dis.get_instructions(actual) if i.opname.startswith("CALL")]
    def observe(signum,frame):
        global depth
        depth+=1
        level=depth
        event={"event":"enter","depth":level,"signal":signal.Signals(signum).name}
        events.append(event);emit(event)
        try:
            actual(signum,frame)
        finally:
            event={"event":"return","depth":level,"signal":signal.Signals(signum).name}
            events.append(event);emit(event)
            depth-=1
    for s in (signal.SIGINT,signal.SIGTERM):
        signal.signal(s,observe)
    legacy=isinstance(interruption,threading.Event)
    def trace(frame,event,arg):
        global fired
        held=(legacy and frame.f_code is threading.Event.set.__code__
              and frame.f_locals.get("self") is interruption
              and interruption._cond._is_owned())
        minimal=(not legacy and frame.f_code is actual.__code__)
        if (mode=="nested" and not fired and event=="line" and depth==1
            and (held or minimal)):
            fired=True
            window="event_condition_owned" if held else "production_handler_line"
            emit({"event":"schedule_nested","window":window})
            signal.raise_signal(second)
        return trace
    if mode=="nested":
        sys.settrace(trace)
    if mode=="spaced":
        def send():
            for i in range(5):
                time.sleep(0.05)
                signal.raise_signal(first if i%2==0 else second)
        sender=threading.Thread(target=send)
        sender.start()
        end=time.monotonic()+2
        while len([e for e in events if e["event"]=="return"])<5 and time.monotonic()<end:
            time.sleep(0.005)
        sender.join(timeout=1)
        assert not sender.is_alive()
    else:
        signal.raise_signal(first)
    sys.settrace(None)
    pending=interruption.is_set()
restored=all(signal.getsignal(s)==h for s,h in previous.items())
emit({"completed":True,"pending":pending,"restored":restored,"nested_scheduled":fired,
      "handler_call_opcodes":calls,"events":events,
      "timing":"semantic_completion","monotonic_ns":time.monotonic_ns()})
"""

CASES = [
    ("single", "SIGINT", "SIGTERM"),
    ("single", "SIGTERM", "SIGINT"),
    ("nested", "SIGINT", "SIGINT"),
    ("nested", "SIGINT", "SIGTERM"),
    ("nested", "SIGTERM", "SIGINT"),
    ("nested", "SIGTERM", "SIGTERM"),
    *(("spaced", "SIGTERM", "SIGINT") for _ in range(3)),
]


def run_case(mode, first, second, *, python=sys.executable, source_root=None, deadline=4):
    environment = {k: v for k, v in os.environ.items() if not k.startswith("MOBIRAEON_")}
    environment.pop("PYTHONPATH", None)
    command = [str(python), "-c", CHILD, mode, first, second, str(source_root or "")]
    with tempfile.TemporaryDirectory(prefix="mobiraeon-signal-probe-") as outside:
        parent_timing = {"popen_started_ns": time.monotonic_ns()}
        process = subprocess.Popen(
            command,
            cwd=outside,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        parent_timing["popen_returned_ns"] = time.monotonic_ns()
        timed_out = False
        parent_timing["communicate_started_ns"] = time.monotonic_ns()
        try:
            stdout, stderr = process.communicate(timeout=deadline)
            parent_timing["communicate_returned_ns"] = time.monotonic_ns()
        except subprocess.TimeoutExpired:
            parent_timing["communicate_timed_out_ns"] = time.monotonic_ns()
            timed_out = True
            parent_timing["kill_started_ns"] = time.monotonic_ns()
            process.kill()
            parent_timing["kill_returned_ns"] = time.monotonic_ns()
            parent_timing["reap_communicate_started_ns"] = time.monotonic_ns()
            stdout, stderr = process.communicate(timeout=3)
            parent_timing["reap_communicate_returned_ns"] = time.monotonic_ns()
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
        == (5 if mode == "spaced" else 2 if mode == "nested" else 1)
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
        "timing": {
            "clock": "monotonic_ns",
            "deadline_seconds": deadline,
            "post_kill_seconds": 3,
            # communicate establishes its own cutoff just after this anchor.
            "communicate_reference_deadline_ns": parent_timing["communicate_started_ns"]
            + int(deadline * 1_000_000_000),
            "parent": parent_timing,
            "child": {
                record["timing"]: record["monotonic_ns"]
                for record in records
                if record.get("timing")
                in ("before_execution_import", "after_execution_import", "semantic_completion")
            },
        },
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
            "Nested cases select a deterministic timing window; spaced controls are untraced. "
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
