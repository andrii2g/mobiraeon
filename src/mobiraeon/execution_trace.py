"""Bounded private supervision telemetry, independent of business outcome/authority."""

import hashlib
import json
import math
import os
import platform
import sys
import time
from collections import deque
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from mobiraeon.private_state import durable_new, harden, protected

_trace = ContextVar("execution_boundary_trace", default=None)
_span = ContextVar("execution_boundary_span", default=None)
_phase = ContextVar("execution_boundary_phase", default=("admission", None))


def safe(value, depth=0):
    if value is None or type(value) in (bool, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, str):
        return value[:512]
    if depth < 3 and isinstance(value, dict):
        return {str(k)[:64]: safe(v, depth + 1) for k, v in list(value.items())[:32]}
    return {"unavailable_type": type(value).__name__}


def event(kind, *, critical=False, **fields):
    trace = _trace.get()
    if trace is None:
        return None
    try:
        return trace.add(kind, critical=critical, **fields)
    except Exception:
        trace.telemetry_failed = True
        return None


@contextmanager
def use_trace(trace):
    token = _trace.set(trace)
    try:
        yield
    finally:
        _trace.reset(token)


@contextmanager
def phase(name, deadline):
    token = _phase.set((name, deadline))
    try:
        yield
    finally:
        _phase.reset(token)


@contextmanager
def span(kind, **fields):
    identity = event(kind + "_entry", **fields)
    token = _span.set(identity)
    try:
        yield identity
    except BaseException as error:
        reason = getattr(error, "reason", None)
        event(
            kind + "_error",
            critical=True,
            call_id=identity,
            exception_type=type(error).__name__,
            reason=getattr(reason, "value", None),
        )
        raise
    else:
        event(kind + "_exit", call_id=identity)
    finally:
        _span.reset(token)


class BoundaryTrace:
    def __init__(self, handoff):
        self.nonce = handoff["nonce"]
        self.directory = Path(handoff["settings"]["data_dir"])
        self.sequence = 0
        self.head = []
        self.recent = deque(maxlen=96)
        self.critical_head = []
        self.critical = deque(maxlen=48)
        self.telemetry_failed = False
        self.identity = {k: handoff.get(k) for k in ("nonce", "engine_id", "attempt")}
        self.identity.update(
            image_id=handoff["settings"].get("image_id"),
            engine_id=handoff["settings"].get("engine_id"),
        )
        self.client = dict(
            python=sys.executable,
            python_version=platform.python_version(),
            host=platform.node(),
            docker_executable=handoff["settings"].get("docker_executable"),
            endpoint=handoff["settings"].get("endpoint"),
        )
        if os.name != "nt":
            self.client.update(uid=os.getuid(), gid=os.getgid())
            try:
                self.client["netns"] = os.readlink("/proc/self/ns/net")
            except OSError:
                self.client["netns"] = None
        package = Path(__file__).parent
        self.hashes = {
            n: hashlib.sha256((package / n).read_bytes()).hexdigest()
            for n in ("execution.py", "docker_worker.py", "execution_trace.py")
        }

    def add(self, kind, *, critical=False, **fields):
        self.sequence += 1
        now = time.monotonic()
        current_phase, deadline = _phase.get()
        record = dict(
            sequence=self.sequence,
            kind=kind[:96],
            monotonic=now,
            utc=time.time(),
            parent_call_id=_span.get(),
            phase=current_phase,
            parent_deadline=deadline,
            remaining=None if deadline is None else deadline - now,
            fields=safe(fields),
        )
        if len(json.dumps(record, allow_nan=False).encode()) > 1280:
            # Bound each retained event independently, including adversarial fields.
            raw_fields = json.dumps(record["fields"], allow_nan=False).encode()
            record["fields"] = dict(
                fields_truncated=True,
                bytes=len(raw_fields),
                sha256=hashlib.sha256(raw_fields).hexdigest(),
            )
        if critical:
            if len(self.critical_head) < 16:
                self.critical_head.append(record)
            else:
                self.critical.append(record)
        elif len(self.head) < 16:
            self.head.append(record)
        else:
            self.recent.append(record)
        return self.sequence

    def export(self):
        try:
            self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            harden(self.directory)
            protected(self.directory, directory=True)
            events = sorted(
                [*self.head, *self.recent, *self.critical_head, *self.critical],
                key=lambda e: e["sequence"],
            )
            payload = dict(
                schema="execution-boundary-v1",
                identity=self.identity,
                client=self.client,
                source_hashes=self.hashes,
                events=events,
                events_seen=self.sequence,
                events_truncated=len(events) < self.sequence,
                telemetry_failed=self.telemetry_failed,
                timing_note=(
                    "Process monotonic anchors; UTC correlation only. "
                    "Instrumentation overhead counts inside existing phase budgets."
                ),
            )
            raw = json.dumps(payload, allow_nan=False).encode()
            assert len(raw) <= 262144
            path = self.directory / (self.nonce + ".boundary.json")
            durable_new(path, raw)
            return dict(available=True, path=str(path), bytes=len(raw))
        except Exception as error:
            return dict(available=False, failure_type=type(error).__name__)
