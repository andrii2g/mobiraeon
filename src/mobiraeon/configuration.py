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
API_DEFAULTS = {
    "enabled": False,
    "host": "127.0.0.1",
    "port": 8443,
    "allow_remote": False,
    "startup_timeout_seconds": 10.0,
    "drain_timeout_seconds": 10.0,
}
SCHEMA.update(
    {
        "access": {"private_dir", "credential_file"},
        "api": {*API_DEFAULTS, "cert_file", "key_file", "client_ca", "client_url"},
    }
)
for _table in ("access", "api"):
    for _key in SCHEMA[_table]:
        ENV_SETTINGS[f"MOBIRAEON_{_table}_{_key}".upper()] = f"{_table}.{_key}"


@dataclass(frozen=True)
class Configuration:
    database_path: Path
    timeout_seconds: float = 5.0
    log_level: str = "INFO"
    private_dir: Path | None = None
    credential_file: Path | None = None
    api: dict | None = None


def _validate(setting, value, source, directory):
    def invalid():
        raise SafeError(Reason.CONFIG_INVALID, source=source, setting=setting)

    if setting.startswith(("access.", "api.")):
        key = setting.split(".")[1]
        if key in {"private_dir", "credential_file", "cert_file", "key_file", "client_ca"}:
            if not isinstance(value, str) or not value.strip() or "\x00" in value:
                invalid()
            return (directory / value).resolve()
        if key in {"enabled", "allow_remote"}:
            if source == "environment" and value in {"true", "false"}:
                return value == "true"
            if type(value) is not bool:
                invalid()
            return value
        if key in {"port", "startup_timeout_seconds", "drain_timeout_seconds"}:
            if source == "environment":
                try:
                    value = int(value) if key == "port" else float(value)
                except ValueError, OverflowError:
                    invalid()
            if type(value) not in (int, float) or not math.isfinite(value):
                invalid()
            if key == "port" and (type(value) is not int or not 1 <= value <= 65535):
                invalid()
            if key != "port" and not 0 < value <= 60:
                invalid()
            return value
        if not isinstance(value, str) or not value.strip():
            invalid()
        if key == "client_url":
            from urllib.parse import urlsplit

            endpoint = urlsplit(value)
            if (
                endpoint.scheme != "https"
                or not endpoint.hostname
                or endpoint.username
                or endpoint.password
                or endpoint.query
                or endpoint.fragment
            ):
                invalid()
        return value

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
        values["database.path"],
        values["database.timeout_seconds"],
        values["logging.level"],
        values.get("access.private_dir"),
        values.get("access.credential_file"),
        API_DEFAULTS
        | {key.split(".")[1]: value for key, value in values.items() if key.startswith("api.")},
    )
