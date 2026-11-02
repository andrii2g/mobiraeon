import json
import logging
from datetime import UTC, datetime

from mobiraeon.errors import SafeError


class JsonFormatter(logging.Formatter):
    def format(self, record):
        # No arbitrary message, exception text, or extra dictionary is serialized.
        return json.dumps(record.safe_event)


class Diagnostics:
    def __init__(self, stream, level):
        self.logger = logging.Logger("mobiraeon", level=level)
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JsonFormatter())
        self.logger.addHandler(handler)
        self.logger.propagate = False

    def event(self, event, invocation_id, *, reason=None, outcome=None, error=None):
        fields = {
            "timestamp": datetime.now(UTC).isoformat(),
            "severity": "ERROR" if event == "command_error" else "INFO",
            "event": event,
            "component": "application",
            "invocation_id": str(invocation_id),
        }
        if reason is not None:
            fields["reason"] = reason.value
        if outcome is not None:
            fields["outcome"] = outcome.value
        if isinstance(error, SafeError):
            if error.source in {"file", "environment", "cli", "selector", "effective"}:
                fields["source"] = error.source
            if error.setting in {
                "database.path",
                "database.timeout_seconds",
                "logging.level",
                "api.client_url",
                "api.port",
                "api.startup_timeout_seconds",
                "api.drain_timeout_seconds",
            }:
                fields["setting"] = error.setting
        if event == "command_error":
            fields["action"] = (
                "Check documented configuration and storage lifecycle; "
                "correct the reported condition before retrying."
            )
        # Readiness, shutdown, and terminal failures bypass the log threshold.
        record = self.logger.makeRecord("mobiraeon", logging.INFO, "", 0, "", (), None)
        record.safe_event = fields
        self.logger.handle(record)
