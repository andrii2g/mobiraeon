"""Foreground fixture supervision, with Docker effects outside SQLite transactions."""

import hashlib
import json
import signal
import subprocess
import threading
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import replace
from functools import partial
from pathlib import Path
from uuid import uuid4

from mobiraeon.access import Access, CurrentAccessPolicy, execute, one
from mobiraeon.contracts import (
    EXECUTION_ACTIONS,
    BusinessData,
    BusinessTarget,
    EntityId,
    Operation,
    OperationResult,
    Outcome,
    Owner,
)
from mobiraeon.coordination import Coordinator, operation_fingerprint, require
from mobiraeon.docker_worker import DockerWorker, actuation_lock, completion_deadline
from mobiraeon.errors import Reason, SafeError
from mobiraeon.execution_schema import reference, validate
from mobiraeon.execution_trace import BoundaryTrace, use_trace
from mobiraeon.execution_trace import event as boundary_event
from mobiraeon.execution_trace import phase as boundary_phase
from mobiraeon.operations import Binding, OperationBoundary
from mobiraeon.private_state import durable_new, harden, protected
from mobiraeon.registry_schema import canonical

_interruption = ContextVar("execution_interruption", default=None)


class _PendingInterruption:
    """Main-thread signal flag; synchronization belongs in normal control flow."""

    __slots__ = ("pending",)

    def __init__(self):
        self.pending = False

    def is_set(self):
        return self.pending


@contextmanager
def execution_signals():
    """Coalesce ordinary foreground interruption; never raise during safety cleanup."""
    current = _interruption.get()
    if current is not None:
        yield current
        return
    interruption = _PendingInterruption()
    token = _interruption.set(interruption)
    previous = {}

    def request_stop(signum, frame):
        # No lock-taking calls: another signal may reenter this exact assignment.
        interruption.pending = True

    try:
        if threading.current_thread() is threading.main_thread():
            for signum in (signal.SIGINT, signal.SIGTERM):
                previous[signum] = signal.signal(signum, request_stop)
        yield interruption
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        _interruption.reset(token)


class CaptureFailure(Exception):
    """A fixed diagnostic, never raw stream exception content."""


class SupervisedConfiguration:
    def resolve(self, references):
        require(
            references
            == {kind: reference(kind) for kind in ("agent", "profile", "role", "context")},
            Reason.NOT_FOUND,
        )
        return {
            "mode": "supervised-fixture-v1",
            "references": references,
            "provider": "unavailable",
            "qualification": "fixture-only",
        }


class ExecutionService:
    def __init__(self, store, private, settings, *, worker_type=DockerWorker, hook=None):
        self.store, self.private, self.settings = store, private, settings or {}
        self.access = Access(store, private)
        self.worker_type = worker_type
        # Trusted test composition only; never a CLI field or configuration switch.
        self.hook = hook or (lambda phase: None)

    def load(self, task, tx=None):
        if tx is None:
            with self.store.engine.connect() as connection:
                return self.load(task, connection)
        row = one(tx, "SELECT * FROM execution_runs WHERE task=:task", {"task": task})
        require(row is not None, Reason.NOT_FOUND)
        return json.loads(row["handoff"]), json.loads(row["record"])

    def event(self, tx, task, record):
        execute(
            tx,
            "INSERT INTO execution_events(task,record) VALUES(:task,:record)",
            {"task": task, "record": canonical(record | {"at": time.time()})},
        )

    def update(self, task, generation, changes, event):
        with self.store.transaction() as tx:
            handoff, current = self.load(task, tx)
            require(current["generation"] == generation, Reason.REFUSED)
            require(not current.get("terminal"), Reason.CONFLICT)
            current |= changes
            execute(
                tx,
                "UPDATE execution_runs SET generation=:generation,held=:held,record=:record "
                "WHERE task=:task",
                {
                    "task": task,
                    "generation": current["generation"],
                    "held": current["held"],
                    "record": canonical(current),
                },
            )
            self.event(
                tx,
                task,
                {
                    "event": event,
                    "generation": generation,
                    "attempt": handoff["attempt"],
                    "changes": changes,
                },
            )
            return current

    def invoke(self, code, target=None, inputs=None, *, proof=None, progress=None):
        if code == Operation.EXECUTION_RUN:
            # Include reservation/progress so interruption cannot be lost between
            # admission and supervision. Nested supervision shares this event.
            with execution_signals():
                return self._invoke(code, target, inputs, proof=proof, progress=progress)
        return self._invoke(code, target, inputs, proof=proof, progress=progress)

    def _invoke(self, code, target=None, inputs=None, *, proof=None, progress=None):
        invocation = uuid4()
        operation, caller = None, None
        try:
            operation = Operation(code)
            if isinstance(target, dict):
                target = BusinessTarget(**target)
            validate(operation, target, inputs)
            self.store.check()
            caller = self.access.caller(proof)
            policy = CurrentAccessPolicy(self.access, proof)
            prepared = None
            if caller is not None and policy.permits(caller, operation, target) is True:
                if operation == Operation.EXECUTION_RUN:
                    with self.store.engine.connect() as tx:
                        exists = one(
                            tx,
                            "SELECT task FROM execution_runs WHERE task=:task",
                            {"task": target.identity},
                        )
                    if exists is None:
                        directory = Path(self.settings.get("data_dir", ""))
                        require(
                            directory.parent == self.private.directory
                            and directory.name != "credentials"
                            and not directory.is_symlink()
                            and (not directory.exists() or directory.is_dir()),
                            Reason.INVALID_INPUT,
                        )
                        if directory.exists():
                            protected(directory, directory=True)
                        try:
                            prepared = self.worker_type(self.settings).preflight()
                        except Exception:
                            raise SafeError(Reason.UNAVAILABLE) from None
            bindings = {
                action: Binding(
                    Owner.COORDINATION,
                    partial(self._handle, action, caller, proof, prepared),
                    True,
                    True,
                    partial(validate, action),
                    True,
                )
                for action in EXECUTION_ACTIONS
            }
            result = OperationBoundary(bindings, policy, caller, self.store).invoke(
                operation, target=target, inputs=inputs
            )
            if result.outcome != Outcome.SUCCESS:
                if result.outcome == Outcome.UNCERTAIN and operation == Operation.EXECUTION_RUN:
                    try:
                        with self.store.transaction() as tx:
                            Coordinator(self.store, self.private)._history(
                                tx,
                                target.identity,
                                result.invocation_id,
                                caller.actor.value,
                                operation,
                                result.outcome,
                                {
                                    "requires_inspection": True,
                                    "operation_id": inputs["operation_id"],
                                    "fingerprint": operation_fingerprint(
                                        operation, target, caller.actor, inputs
                                    ),
                                },
                            )
                    except Exception:
                        result = replace(result, data=BusinessData(audit_status="unavailable"))
                return result
            record = result.data.records[0]
            boundary_event("before_progress", critical=True)
            if progress:
                progress(result)
            if operation == Operation.EXECUTION_RUN and record.get("new_reservation"):
                self.supervise(target, proof, progress)
                handoff, record = self.load(target.identity)
                result = replace(result, data=BusinessData((record,), state=record["phase"]))
                if (
                    not record.get("terminal")
                    or record.get("outcome") == "unknown"
                    or record["held"]
                ):
                    return replace(result, outcome=Outcome.UNCERTAIN, reason=Reason.UNCERTAIN)
                if record["outcome"] != "succeeded" or not record.get("artifact_valid"):
                    return replace(
                        result, outcome=Outcome.FAILURE, reason=Reason.EXECUTION_FAILED
                    )
            elif operation == Operation.EXECUTION_RUN and record.get("terminal"):
                if record["outcome"] == "unknown" or record["held"]:
                    return replace(result, outcome=Outcome.UNCERTAIN, reason=Reason.UNCERTAIN)
                if record["outcome"] != "succeeded" or not record.get("artifact_valid"):
                    return replace(
                        result, outcome=Outcome.FAILURE, reason=Reason.EXECUTION_FAILED
                    )
            elif operation == Operation.EXECUTION_STOP and not record.get("terminal"):
                self.cleanup_only(target.identity)
                _, record = self.load(target.identity)
                result = replace(
                    result,
                    data=BusinessData(
                        (record | {"stop_acknowledged": True},), state=record["phase"]
                    ),
                )
            return result
        except ValueError, TypeError, KeyError, UnicodeError:
            outcome, reason = Outcome.INVALID, Reason.INVALID_INPUT
        except SafeError as error:
            reason = error.reason
            outcome = {
                Reason.INVALID_INPUT: Outcome.INVALID,
                Reason.REFUSED: Outcome.REFUSED,
                Reason.PROTECTION: Outcome.REFUSED,
                Reason.AUTHENTICATION: Outcome.REFUSED,
                Reason.UNAVAILABLE: Outcome.UNAVAILABLE,
            }.get(reason, Outcome.UNCERTAIN)
        except Exception:
            outcome, reason = Outcome.UNCERTAIN, Reason.UNCERTAIN
        return OperationResult(
            invocation, operation, outcome, reason, caller.actor if caller else None
        )

    def _handle(self, operation, caller, proof, prepared, tx, target, inputs, invocation):
        task = target.identity
        coordinator = Coordinator(
            self.store, self.private, configuration_source=SupervisedConfiguration()
        )
        if operation == Operation.EXECUTION_STATUS:
            handoff, record = self.load(task, tx)
            require(inputs["attempt_id"] == handoff["attempt"])
            events = [
                json.loads(r["record"])
                for r in execute(
                    tx,
                    "SELECT record FROM execution_events WHERE task=:task ORDER BY sequence",
                    {"task": task},
                ).mappings()
            ]
            return BusinessData(
                (record | {"handoff": handoff, "events": events},), state=record["phase"]
            )
        fingerprint = operation_fingerprint(operation, target, caller.actor, inputs)
        receipt = one(
            tx, "SELECT * FROM execution_receipts WHERE id=:id", {"id": inputs["operation_id"]}
        )
        if receipt is not None:
            require(receipt["task"] == task and receipt["fingerprint"] == fingerprint)
            _, record = self.load(task, tx)
            return BusinessData(
                (
                    record
                    | {
                        "replayed": True,
                        "stop_acknowledged": operation == Operation.EXECUTION_STOP,
                    },
                ),
                state=record["phase"],
            )
        if operation == Operation.EXECUTION_RUN:
            require(prepared is not None, Reason.UNAVAILABLE)
            require(one(tx, "SELECT task FROM execution_runs WHERE held=1") is None)
            require(
                one(tx, "SELECT task FROM execution_runs WHERE task=:task", {"task": task})
                is None
            )
            require(self.access.permits(proof, Operation.DISPATCH, target, tx), Reason.REFUSED)
            assignment = coordinator._fact(tx, task, "allocate")
            require(assignment["owner"] == caller.actor.value, Reason.REFUSED)
            require(assignment["snapshot"]["mode"] == "supervised-fixture-v1", Reason.REFUSED)
            require(inputs["attempt_id"] == assignment["inputs"]["attempt_id"])
            supplied = coordinator._fact(tx, task, "supply")["inputs"]["work"]
            content = supplied["inputs"][0]["content"]
            require(len(content.encode()) <= self.settings["input_bytes"], Reason.INVALID_INPUT)
            directory = Path(self.settings["data_dir"])
            require(
                directory.parent == self.private.directory
                and directory.name not in {"credentials", "execution-worker.lock"},
                Reason.INVALID_INPUT,
            )
            nonce = uuid4().hex
            handoff = {
                "task": task,
                "assignment": assignment["inputs"]["assignment_id"],
                "attempt": inputs["attempt_id"],
                "owner": caller.actor.value,
                "worker": "local-docker",
                "settings": self.settings,
                "prepared": prepared,
                "input": supplied["inputs"][0],
                "configuration": assignment["snapshot"],
                "mode": inputs["mode"],
                "name": "mobiraeon-fixture-" + nonce,
                "nonce": nonce,
            }
            record = {
                "task": task,
                "assignment": handoff["assignment"],
                "worker": handoff["worker"],
                "phase": "reserved",
                "outcome": "unknown",
                "generation": 1,
                "held": True,
                "terminal": False,
                "artifact_valid": False,
                "cleanup": "unverified",
                "stop_intent": False,
                "attempt": handoff["attempt"],
                "new_reservation": False,
            }
            execute(
                tx,
                "INSERT INTO execution_runs VALUES(:task,:attempt,:handoff,1,1,:record)",
                {
                    "task": task,
                    "attempt": handoff["attempt"],
                    "handoff": canonical(handoff),
                    "record": canonical(record),
                },
            )
            coordinator.execution_dispatch = True  # trusted reservation, never a public field
            coordinator._handle(
                Operation.DISPATCH,
                caller,
                proof,
                tx,
                target,
                {
                    "operation_id": "execution-" + nonce,
                    "expected_version": inputs["expected_version"],
                    "attempt_id": inputs["attempt_id"],
                },
                invocation,
            )
            self.event(
                tx,
                task,
                {
                    "event": "reserved",
                    "actor": caller.actor.value,
                    "operation_id": inputs["operation_id"],
                    "handoff": handoff,
                },
            )
            returned = record | {"new_reservation": True}
        else:
            handoff, record = self.load(task, tx)
            require(inputs["attempt_id"] == handoff["attempt"])
            if not record.get("terminal") and not record["stop_intent"]:
                record |= {"stop_intent": True, "generation": record["generation"] + 1}
                execute(
                    tx,
                    "UPDATE execution_runs SET generation=:gen,record=:record WHERE task=:task",
                    {"gen": record["generation"], "record": canonical(record), "task": task},
                )
                self.event(
                    tx,
                    task,
                    {
                        "event": "stop_intent",
                        "actor": caller.actor.value,
                        "reason": inputs["reason"],
                        "generation": record["generation"],
                    },
                )
            returned = record | {"stop_acknowledged": True}
        execute(
            tx,
            "INSERT INTO execution_receipts VALUES(:id,:task,:fingerprint)",
            {"id": inputs["operation_id"], "task": task, "fingerprint": fingerprint},
        )
        return BusinessData((returned,), state=returned["phase"])

    def cleanup_only(self, task):
        try:
            with actuation_lock(self.private):
                handoff, record = self.load(task)
                if record.get("terminal"):
                    return
                worker = self.worker_type(handoff["settings"])
                cleaned = worker.cleanup(handoff, record)
                self.update(
                    task,
                    record["generation"],
                    {
                        "phase": "terminal" if cleaned else "unresolved",
                        "held": not cleaned,
                        "cleanup": "verified" if cleaned else "unverified",
                        "terminal": cleaned,
                        "outcome": "unknown",
                        "artifact_valid": False,
                    },
                    "cleanup_only",
                )
        except Exception:
            # Retain the hold and evidence; unknown cleanup is not a release.
            return

    def supervise(self, target, proof, progress):
        with execution_signals() as interruption:
            trace = None
            try:
                trace = BoundaryTrace(self.load(target.identity)[0])
            except Exception:
                pass  # Diagnostic availability never grants or changes execution authority.
            with use_trace(trace):
                try:
                    self._supervise(target, proof, progress, interruption)
                finally:
                    try:
                        current = self.load(target.identity)[1]
                        boundary_event(
                            "final_projection",
                            critical=True,
                            facts={
                                k: current.get(k)
                                for k in (
                                    "outcome",
                                    "cleanup",
                                    "terminal",
                                    "held",
                                    "seal",
                                    "attachment_exit_code",
                                )
                            },
                            completion_state={
                                k: v
                                for k, v in (current.get("completion_state") or {}).items()
                                if k
                                in {
                                    "Running",
                                    "ExitCode",
                                    "FinishedAt",
                                    "StartedAt",
                                    "OOMKilled",
                                    "Status",
                                }
                            },
                        )
                    except Exception as error:
                        boundary_event(
                            "final_projection_unavailable",
                            critical=True,
                            exception_type=type(error).__name__,
                        )
                    self.last_boundary_diagnostic = (
                        trace.export()
                        if trace
                        else {"available": False, "reason": "trace_initialization_failed"}
                    )

    def _supervise(self, target, proof, progress, interruption):
        task = target.identity
        handoff, record = self.load(task)
        generation = record["generation"]
        worker = self.worker_type(handoff["settings"])
        s = handoff["settings"]
        process = None
        readers = []
        buffers = {"stdout": bytearray(), "stderr": bytearray()}
        overflow = threading.Event()
        capture_failed = threading.Event()
        channels = {name: "pending" for name in buffers}
        capture_lock = threading.Lock()
        outcome = "unknown"
        completion_state = None
        attachment_exit = None
        state = None
        startup_end = time.monotonic() + s["startup_seconds"]
        boundary_event("run_start", critical=True, startup_deadline=startup_end)

        def interrupted():
            if interruption.is_set():
                raise KeyboardInterrupt

        def record_interruption():
            # Never publish under a cleanup taker's newer generation.
            self.update(task, generation, {"stop_intent": True}, "interrupted")

        try:
            with actuation_lock(self.private):
                interrupted()
                _, current = self.load(task)
                require(
                    current["generation"] == generation and not current["stop_intent"],
                    Reason.REFUSED,
                )
                self.update(
                    task,
                    generation,
                    {"create_intent": True, "phase": "creating"},
                    "create_intent",
                )
                self.hook("before_create")
                interrupted()
                identity = worker.create(
                    handoff, timeout=max(0.05, startup_end - time.monotonic())
                )
                self.hook("after_create")
                self.update(
                    task, generation, {"container_id": identity, "create_ack": True}, "created"
                )
                self.hook("before_start_authorization")
                interrupted()
                # This short transaction is the start/stop ordering point. No Docker in it.
                with self.store.transaction() as tx:
                    _, current = self.load(task, tx)
                    require(
                        current["generation"] == generation and not current["stop_intent"],
                        Reason.REFUSED,
                    )
                    require(
                        self.access.permits(proof, Operation.DISPATCH, target, tx),
                        Reason.REFUSED,
                    )
                    require(
                        self.access.permits(proof, Operation.EXECUTION_RUN, target, tx),
                        Reason.REFUSED,
                    )
                    current |= {"start_authorized": True, "phase": "start_authorized"}
                    execute(
                        tx,
                        "UPDATE execution_runs SET record=:record WHERE task=:task",
                        {"task": task, "record": canonical(current)},
                    )
                    self.event(
                        tx, task, {"event": "start_authorized", "generation": generation}
                    )
                self.hook("after_start_authorization")
                _, current = self.load(task)
                require(
                    current["generation"] == generation and not current["stop_intent"],
                    Reason.REFUSED,
                )
                self.hook("before_start_delivery")
                interrupted()
                process = worker.start(
                    identity, timeout=max(0.05, startup_end - time.monotonic())
                )

                def read(name, stream):
                    try:
                        while True:
                            chunk = stream.read(4096)
                            with capture_lock:
                                if not chunk:
                                    channels[name] = "eof"
                                    break
                                remaining = s["capture_bytes"] - sum(map(len, buffers.values()))
                                if name == "stdout":
                                    remaining = min(
                                        remaining, s["result_bytes"] - len(buffers[name])
                                    )
                                buffers[name].extend(chunk[: max(0, remaining)])
                                if len(chunk) > remaining:
                                    overflow.set()
                    except Exception:
                        with capture_lock:
                            channels[name] = "failed"
                            capture_failed.set()
                    finally:
                        try:
                            stream.close()
                        except Exception:
                            with capture_lock:
                                channels[name] = "failed"
                                capture_failed.set()

                for name in buffers:
                    thread = threading.Thread(
                        target=read, args=(name, getattr(process, name)), daemon=True
                    )
                    thread.start()
                    readers.append(thread)

                def send_input():
                    try:
                        process.stdin.write(handoff["input"]["content"].encode())
                        process.stdin.close()
                    except OSError, ValueError:
                        pass

                sender = threading.Thread(target=send_input, daemon=True)
                sender.start()
                readers.append(sender)
                while time.monotonic() < startup_end:
                    interrupted()
                    if capture_failed.is_set():
                        raise CaptureFailure
                    state = worker.inspect(
                        handoff, identity, timeout=max(0.05, startup_end - time.monotonic())
                    )
                    if state and state["State"]["StartedAt"][:4] != "0001":
                        break
                    if process.poll() is not None and state and state["State"].get("Error"):
                        raise SafeError(Reason.EXECUTION_FAILED)
                    time.sleep(0.05)
                else:
                    raise SafeError(Reason.UNCERTAIN)
                boundary_event("observed_start_processing", critical=True)
                self.hook("after_start")
                self.update(
                    task,
                    generation,
                    {"phase": "running", "observed_start": state["State"]["StartedAt"]},
                    "observed_start",
                )
            boundary_event("before_progress", critical=True)
            if progress:
                progress(
                    OperationResult(
                        uuid4(),
                        Operation.EXECUTION_RUN,
                        Outcome.SUCCESS,
                        Reason.OK,
                        actor=EntityId("human", handoff["owner"]),
                        target=target,
                        data=BusinessData((self.load(task)[1],), state="running"),
                    )
                )
            boundary_event("progress_returned", critical=True)
            deadline = time.monotonic() + s["execution_seconds"]
            boundary_event("execution_deadline", critical=True, execution_deadline=deadline)
            while True:
                interrupted()
                _, current = self.load(task)
                if current["generation"] != generation or current["stop_intent"]:
                    outcome = "stopped"
                    break
                if overflow.is_set():
                    outcome = "output_limit"
                    break
                if capture_failed.is_set():
                    raise CaptureFailure
                attachment_exit = process.poll()
                boundary_event(
                    "attachment_poll",
                    critical=attachment_exit is not None,
                    exit_code=attachment_exit,
                )
                if attachment_exit is not None:
                    with (
                        boundary_phase("completion", deadline),
                        completion_deadline(deadline) as remaining,
                    ):
                        state = worker.inspect(handoff, identity, timeout=remaining())
                        observed = state["State"] if state else {}
                        finished = observed.get("FinishedAt")
                        boundary_event(
                            "completion_predicates",
                            critical=True,
                            non_running=observed.get("Running") is False,
                            finished=isinstance(finished, str)
                            and bool(finished)
                            and not finished.startswith("0001"),
                            strict_exit=type(observed.get("ExitCode")) is int,
                            state={
                                k: v
                                for k, v in observed.items()
                                if k
                                in {
                                    "Running",
                                    "ExitCode",
                                    "FinishedAt",
                                    "StartedAt",
                                    "OOMKilled",
                                }
                            },
                        )
                        remaining()
                        if (
                            observed.get("Running") is False
                            and isinstance(finished, str)
                            and finished
                            and not finished.startswith("0001")
                            and type(observed.get("ExitCode")) is int
                        ):
                            completion_state = dict(observed)
                            outcome = "succeeded" if observed["ExitCode"] == 0 else "failed"
                    break
                if time.monotonic() >= deadline:
                    outcome = "timeout"
                    break
                time.sleep(0.05)
        except KeyboardInterrupt:
            # Confined safety stop remains possible even if the caller was revoked.
            try:
                record_interruption()
                started = state and state["State"].get("StartedAt")
                outcome = "stopped" if started and not started.startswith("0001") else "unknown"
            except Exception:
                pass
        except CaptureFailure:
            outcome = "capture_failed"
        except SafeError as error:
            boundary_event(
                "supervision_safe_error",
                critical=True,
                exception_type=type(error).__name__,
                reason=error.reason.value,
            )
            outcome = "startup_failed" if error.reason == Reason.EXECUTION_FAILED else "unknown"
        except Exception as error:
            boundary_event(
                "supervision_exception", critical=True, exception_type=type(error).__name__
            )
            outcome = "unknown"
        finally:
            cleanup_end = time.monotonic() + s["grace_seconds"] + s["cleanup_seconds"]
            boundary_event(
                "cleanup_begin",
                critical=True,
                cleanup_deadline=cleanup_end,
                outcome=outcome,
                attachment_exit=attachment_exit,
                has_completion=completion_state is not None,
            )
            try:
                with actuation_lock(self.private):
                    _, current = self.load(task)
                    if not current.get("terminal"):
                        with boundary_phase("cleanup", cleanup_end):
                            cleaned = worker.cleanup(handoff, current)
                        boundary_event("cleanup_result", critical=True, cleaned=cleaned)
                        state = getattr(worker, "last_state", None) or state
                        if process:
                            try:
                                process.wait(timeout=max(0.05, cleanup_end - time.monotonic()))
                            except subprocess.TimeoutExpired:
                                process.kill()
                                process.wait(timeout=2)
                        for reader in readers:
                            reader.join(timeout=max(0.05, cleanup_end - time.monotonic()))
                        with capture_lock:
                            capture_channels = dict(channels)
                            capture_complete = (
                                bool(process)
                                and attachment_exit == 0
                                and completion_state is not None
                                and all(not t.is_alive() for t in readers)
                                and all(value == "eof" for value in capture_channels.values())
                            )
                            raw = bytes(buffers["stdout"])
                            stderr = bytes(buffers["stderr"])
                        if not capture_complete and outcome == "succeeded":
                            outcome = "capture_failed"
                        if overflow.is_set():
                            outcome = "output_limit"
                        # Stop before terminal sealing wins, including after exit 0.
                        if current["stop_intent"]:
                            outcome = "stopped" if outcome != "unknown" else "unknown"
                        if current["generation"] != generation:
                            # Confined physical cleanup is allowed, but a fenced
                            # supervisor cannot publish under the new generation.
                            raise SafeError(Reason.REFUSED)
                        artifact = None
                        valid = outcome == "succeeded" and cleaned and capture_complete
                        if valid:
                            try:
                                expected = summary(handoff["input"]["content"])

                                def unique(items):
                                    result = dict(items)
                                    require(len(result) == len(items))
                                    return result

                                parsed = json.loads(raw, object_pairs_hook=unique)
                                require(
                                    parsed == expected
                                    and all(
                                        type(parsed[k]) is int
                                        for k in ("utf8_bytes", "characters", "lines", "words")
                                    )
                                )
                                artifact = {
                                    "identity": "fixture-summary",
                                    "revision": "sha256-" + hashlib.sha256(raw).hexdigest(),
                                    "sha256": hashlib.sha256(raw).hexdigest(),
                                    "content": raw.decode(),
                                }
                            except Exception:
                                valid = False
                                outcome = "invalid_output"
                        directory = Path(s["data_dir"])
                        directory.mkdir(mode=0o700, exist_ok=True)
                        harden(directory)
                        protected(directory, directory=True)
                        capture_path = directory / (handoff["nonce"] + ".json")
                        durable_new(
                            capture_path,
                            canonical(
                                {
                                    "stdout": raw.decode(errors="replace"),
                                    "stderr": stderr.decode(errors="replace"),
                                    "truncated": overflow.is_set(),
                                    "channels": capture_channels,
                                }
                            ).encode(),
                        )
                        artifact_path = None
                        if artifact:
                            artifact_path = directory / (handoff["nonce"] + ".txt")
                            durable_new(artifact_path, raw)
                        self.hook("before_seal")
                        if interruption.is_set():
                            record_interruption()
                            _, current = self.load(task)
                            outcome = "stopped" if outcome != "unknown" else "unknown"
                            valid = False
                        self.update(
                            task,
                            current["generation"],
                            {
                                "phase": "terminal" if cleaned else "unresolved",
                                "terminal": cleaned,
                                "held": not cleaned,
                                "cleanup": "verified" if cleaned else "unverified",
                                "outcome": outcome,
                                "artifact_valid": valid,
                                "artifact": artifact if valid else None,
                                "artifact_path": str(artifact_path) if artifact_path else None,
                                "capture_path": str(capture_path),
                                "truncated": overflow.is_set(),
                                "capture_complete": capture_complete,
                                "capture_channels": capture_channels,
                                "retired": cleaned,
                                "seal": uuid4().hex,
                                "runtime_state": state["State"] if state else None,
                                "completion_state": completion_state,
                                "attachment_exit_code": attachment_exit,
                            },
                            "sealed",
                        )
            except Exception:
                # A failed seal/cleanup cannot establish terminal completion or release.
                if process and process.poll() is None:
                    process.kill()
                    process.wait(timeout=2)
            finally:
                if process:
                    for stream in (process.stdin, process.stdout, process.stderr):
                        if stream and not stream.closed:
                            stream.close()
        _, current = self.load(task)
        if (
            current.get("terminal")
            and current.get("seal")
            and current.get("cleanup") == "verified"
            and current.get("outcome") != "unknown"
        ):
            coordinator = Coordinator(self.store, self.private)
            with self.store.engine.connect() as tx:
                version = one(
                    tx, "SELECT version FROM coordination_tasks WHERE id=:task", {"task": task}
                )["version"]
            observed_result = coordinator.invoke(
                Operation.OBSERVE,
                target,
                {
                    "operation_id": "observe-" + handoff["nonce"],
                    "expected_version": version,
                    "attempt_id": handoff["attempt"],
                    "observation": (
                        "succeeded"
                        if current["outcome"] == "succeeded" and current["artifact_valid"]
                        else "failed"
                    ),
                    "detail": current["seal"],
                },
                proof=proof,
            )
            boundary_event(
                "coordination_observation_result",
                critical=True,
                outcome=observed_result.outcome.value,
            )


def summary(text):
    raw = text.encode()
    return {
        "schema": "fixture-summary-v1",
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "utf8_bytes": len(raw),
        "characters": len(text),
        "lines": len(text.splitlines()),
        "words": len(text.split()),
    }
