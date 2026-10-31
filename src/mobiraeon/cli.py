import argparse
import json
import os
import signal
import sqlite3
import sys
import threading
from dataclasses import asdict, replace
from uuid import uuid4

from mobiraeon import __version__
from mobiraeon.application import CAPABILITIES, Application
from mobiraeon.configuration import resolve_configuration
from mobiraeon.contracts import OperationResult, Outcome
from mobiraeon.diagnostics import Diagnostics
from mobiraeon.errors import Reason, SafeError


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse messages can contain the full argument or raw option value.
        raise SafeError(Reason.INVALID_INPUT, source="cli")


def parser():
    result = SafeParser(description="Möbiræon local application foundation", allow_abbrev=False)
    result.add_argument("--version", action="version", version=__version__)
    result.add_argument("--config", default=argparse.SUPPRESS)
    result.add_argument("--database", default=argparse.SUPPRESS)
    result.add_argument("--database-timeout-seconds", default=argparse.SUPPRESS)
    result.add_argument("--log-level", default=argparse.SUPPRESS)
    result.add_argument("command", choices=["initialize", "upgrade", "check", "start"])
    return result


def serve(stop=None):
    """Foreground only; SIGINT/SIGTERM (and Windows Ctrl+Break) stop cleanly."""
    stop = stop or threading.Event()
    previous = {}

    def request_stop(signum, frame):
        stop.set()

    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.signal(signum, request_stop)
        if os.name == "nt":
            previous[signal.SIGBREAK] = signal.signal(signal.SIGBREAK, request_stop)
        # Windows SIGBREAK can remain pending during an indefinite lock wait.
        # Bounded waits let Python dispatch it and request the same clean stop.
        while not stop.wait(0.2):
            pass
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


def main(argv=None):
    diagnostics = Diagnostics(sys.stderr, "INFO")
    invocation = uuid4()
    application = None
    result = OperationResult(invocation, None, Outcome.UNCERTAIN, Reason.INTERNAL)
    metadata = {"version": __version__, "sqlite_version": sqlite3.sqlite_version}
    command = None
    diagnostic_error = None
    exit_code = 1

    def emit(*, ready=False):
        output = asdict(result) | metadata
        output["phase"] = "ready" if ready else "terminal"
        if ready or result.outcome == Outcome.SUCCESS:
            output["foundation_ready"] = ready or command == "check"
            output["capabilities"] = CAPABILITIES
        print(json.dumps(output, default=str), flush=True)

    try:
        options = vars(parser().parse_args(argv))
        command = options["command"]
        configuration = resolve_configuration(options=options)
        diagnostics = Diagnostics(sys.stderr, configuration.log_level)
        application = Application(configuration)
        result = application.operations.invoke(command)
        invocation = result.invocation_id
        metadata["schema_revision"] = application.store.recorded_revision()
        exit_code = 0 if result.outcome == Outcome.SUCCESS else 1
        if command == "start" and exit_code == 0:
            # This is an intermediate readiness observation, not command completion.
            emit(ready=True)
            diagnostics.event("foundation_ready", invocation)
            try:
                serve()
            except KeyboardInterrupt:
                pass
    except SafeError as error:
        result = replace(result, outcome=Outcome.INVALID, reason=error.reason)
        diagnostic_error = error
        exit_code = 2
    except Exception:
        result = replace(result, outcome=Outcome.UNCERTAIN, reason=Reason.INTERNAL)
        exit_code = 1
    finally:
        if application is not None:
            try:
                application.close()
            except Exception:
                result = replace(
                    result, outcome=Outcome.UNCERTAIN, reason=Reason.CLEANUP_FAILED
                )
                diagnostic_error = None
                exit_code = 1

    # Exactly one finalization attempt precedes terminal reporting, on every path.
    if exit_code:
        diagnostics.event(
            "command_error",
            invocation,
            reason=result.reason,
            outcome=result.outcome,
            error=diagnostic_error,
        )
    elif command == "start":
        diagnostics.event("stopped", invocation)
    emit()
    return exit_code
