import math
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from mobiraeon.errors import Reason, SafeError

ENV_SETTINGS = {
    "MOBIRAEON_DATABASE_PATH": "database.path",
    "MOBIRAEON_DATABASE_TIMEOUT_SECONDS": "database.timeout_seconds",
    "MOBIRAEON_LOG_LEVEL": "logging.level",
}
SCHEMA = {"database": {"path", "timeout_seconds"}, "logging": {"level"}}


@dataclass(frozen=True)
class Configuration:
    database_path: Path
    timeout_seconds: float = 5.0
    log_level: str = "INFO"


def _validate(setting, value, source, directory):
    def invalid():
        raise SafeError(Reason.CONFIG_INVALID, source=source, setting=setting)

    if setting == "database.path":
        if (
            not isinstance(value, str)
            or not value.strip()
            or "\x00" in value
            or value == ":memory:"
            or value.lower().startswith("file:")
            or "://" in value
        ):
            invalid()
        try:
            return (directory / value).resolve()
        except OSError, ValueError:
            invalid()
    if setting == "database.timeout_seconds":
        if isinstance(value, bool) or not isinstance(value, (int, float, str)):
            invalid()
        # Strings belong only to text-based sources, never TOML numeric settings.
        if source == "file" and isinstance(value, str):
            invalid()
        try:
            number = float(value)
        except ValueError, OverflowError:
            invalid()
        if not math.isfinite(number) or not 0 < number <= 60:
            invalid()
        return number
    if setting == "logging.level":
        if not isinstance(value, str) or value.upper() not in {
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL",
        }:
            invalid()
        return value.upper()
    raise SafeError(Reason.UNKNOWN_SETTING, source=source)


def resolve_configuration(*, options, environ=None, cwd=None):
    environ = os.environ if environ is None else environ
    directory = Path.cwd() if cwd is None else Path(cwd)
    values = {"database.timeout_seconds": 5.0, "logging.level": "INFO"}
    for name in environ:
        if name.startswith("MOBIRAEON_") and name not in {*ENV_SETTINGS, "MOBIRAEON_CONFIG"}:
            raise SafeError(Reason.UNKNOWN_SETTING, source="environment")
    # Validate both selectors, including an overridden environment selector.
    for selector in (environ.get("MOBIRAEON_CONFIG"), options.get("config")):
        if selector is not None and (not isinstance(selector, str) or not selector.strip()):
            raise SafeError(Reason.CONFIG_INVALID, source="selector")
    selected = options.get("config", environ.get("MOBIRAEON_CONFIG"))
    if selected is not None:
        try:
            filename = (directory / selected).resolve()
            with filename.open("rb") as stream:
                document = tomllib.load(stream)
        except OSError, ValueError:
            raise SafeError(Reason.CONFIG_FILE, source="file") from None
        for table, entries in document.items():
            if table not in SCHEMA or not isinstance(entries, dict):
                raise SafeError(Reason.UNKNOWN_SETTING, source="file")
            for key, value in entries.items():
                if key not in SCHEMA[table]:
                    raise SafeError(Reason.UNKNOWN_SETTING, source="file")
                setting = f"{table}.{key}"
                values[setting] = _validate(setting, value, "file", filename.parent)
    for name, setting in ENV_SETTINGS.items():
        if name in environ:
            values[setting] = _validate(setting, environ[name], "environment", directory)
    for key, setting in {
        "database": "database.path",
        "database_timeout_seconds": "database.timeout_seconds",
        "log_level": "logging.level",
    }.items():
        if key in options:
            values[setting] = _validate(setting, options[key], "cli", directory)
    if "database.path" not in values:
        raise SafeError(Reason.CONFIG_INVALID, source="effective", setting="database.path")
    return Configuration(
        values["database.path"], values["database.timeout_seconds"], values["logging.level"]
    )
