"""Finite fixture settings, separate from API timeout rules."""

import math
import re

from mobiraeon.errors import Reason, SafeError

MIB = 1024 * 1024
DEFAULTS = {
    "startup_seconds": 100.0,
    "execution_seconds": 100.0,
    "grace_seconds": 5.0,
    "cleanup_seconds": 10.0,
    "cpus": 1.0,
    "memory_bytes": 256 * MIB,
    "pids": 32,
    "input_bytes": 65536,
    "result_bytes": 65536,
    "capture_bytes": 256 * 1024,
    "scratch_bytes": 32 * MIB,
}
KEYS = {*DEFAULTS, "docker_executable", "endpoint", "engine_id", "image_id", "data_dir"}


def setting(key, value, source, directory):
    def invalid():
        raise SafeError(Reason.CONFIG_INVALID, source=source, setting="execution." + key)

    if key in DEFAULTS:
        integer = key.endswith("_bytes") or key == "pids"
        if source == "environment":
            try:
                value = int(value) if integer else float(value)
            except ValueError, OverflowError:
                invalid()
        if type(value) not in ((int,) if integer else (int, float)) or (
            type(value) is float and not math.isfinite(value)
        ):
            invalid()
        ranges = {
            "cpus": (0.01, 16),
            "memory_bytes": (32 * MIB, 1024 * MIB),
            "pids": (8, 256),
            "input_bytes": (1, 131072),
            "result_bytes": (1, 131072),
            "capture_bytes": (256, 2 * MIB),
            "scratch_bytes": (4 * MIB, 256 * MIB),
        }
        low, high = ranges.get(key, (0.05, 600))
        if not low <= value <= high:
            invalid()
        return value
    if not isinstance(value, str) or not value.strip() or "\0" in value:
        invalid()
    if key == "image_id" and not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
        invalid()
    if key == "endpoint" and not re.fullmatch(r"unix:///[^\s]+", value):
        invalid()
    if key in {"data_dir", "docker_executable"}:
        return str((directory / value).absolute())
    return value


def effective(values):
    result = DEFAULTS | values
    if result["scratch_bytes"] + 16 * MIB > result["memory_bytes"]:
        raise SafeError(Reason.CONFIG_INVALID, setting="execution.memory_bytes")
    return result
