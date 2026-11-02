"""FR-04: strict safe API configuration classification, including overrides."""

import json
import os
import subprocess
import sys

import pytest

from mobiraeon.configuration import resolve_configuration
from mobiraeon.errors import Reason, SafeError

CASES = [
    ("client_url", "https://["),
    ("port", int("9" * 401)),
    ("startup_timeout_seconds", int("9" * 401)),
    ("drain_timeout_seconds", int("9" * 401)),
]


@pytest.mark.parametrize("setting,value", CASES)
@pytest.mark.parametrize("source", ["file", "environment"])
def test_fr04_safe_configuration(tmp_path, setting, value, source):
    db = tmp_path / "absent.db"
    config = tmp_path / "invalid.toml"
    config.write_text("[api]\n" + setting + " = " + json.dumps(value) + "\n")
    env = {"MOBIRAEON_API_" + setting.upper(): str(value)} if source == "environment" else {}
    options = {"database": str(db)} | ({"config": str(config)} if source == "file" else {})
    with pytest.raises(SafeError) as error:
        resolve_configuration(options=options, environ=env)
    assert (error.value.reason, error.value.source, error.value.setting) == (
        Reason.CONFIG_INVALID,
        source,
        "api." + setting,
    )
    environment = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("MOBIRAEON_") and k != "PYTHONPATH"
    } | env
    command = [
        sys.executable,
        "-m",
        "mobiraeon",
        "--database",
        str(db),
        *(["--config", str(config)] if source == "file" else []),
        "check",
    ]
    r = subprocess.run(
        command, cwd=tmp_path, env=environment, capture_output=True, text=True, timeout=15
    )
    records = [json.loads(line) for line in r.stdout.splitlines()]
    assert r.returncode == 2 and len(records) == 1, (r.stdout, r.stderr)
    assert (records[0]["phase"], records[0]["outcome"], records[0]["reason"]) == (
        "terminal",
        "invalid_input",
        "configuration_invalid",
    )
    diagnostic = [
        json.loads(line)
        for line in r.stderr.splitlines()
        if json.loads(line).get("event") == "command_error"
    ][-1]
    assert diagnostic["setting"] == "api." + setting and diagnostic["source"] == source
    assert str(value) not in r.stdout + r.stderr and "Traceback" not in r.stderr
    assert not db.exists() and set(p.name for p in tmp_path.iterdir()) == {"invalid.toml"}
    if source == "file":
        with pytest.raises(SafeError):
            resolve_configuration(
                options=options,
                environ={
                    "MOBIRAEON_API_" + setting.upper(): "https://localhost"
                    if setting == "client_url"
                    else "1"
                },
            )


@pytest.mark.parametrize(
    "setting", ["port", "startup_timeout_seconds", "drain_timeout_seconds"]
)
def test_fr04_boolean_and_boundaries(tmp_path, setting):
    p = tmp_path / "settings.toml"
    for value in [True, False]:
        p.write_text("[api]\n" + setting + " = " + str(value).lower())
        with pytest.raises(SafeError):
            resolve_configuration(
                options={"config": str(p), "database": str(tmp_path / "db")}, environ={}
            )
    for value in [1, 65535] if setting == "port" else [0.01, 60]:
        p.write_text("[api]\n" + setting + " = " + str(value))
        assert (
            resolve_configuration(
                options={"config": str(p), "database": str(tmp_path / "db")}, environ={}
            ).api[setting]
            == value
        )


@pytest.mark.parametrize(
    "setting", ["port", "startup_timeout_seconds", "drain_timeout_seconds"]
)
def test_fr04_environment_strict_boundaries(tmp_path, setting):
    options = {"database": str(tmp_path / "absent.db")}
    for value in ["true", "false"]:
        with pytest.raises(SafeError) as error:
            resolve_configuration(
                options=options, environ={"MOBIRAEON_API_" + setting.upper(): value}
            )
        assert error.value.source == "environment" and error.value.setting == "api." + setting
    for value in [1, 65535] if setting == "port" else [0.01, 60]:
        resolved = resolve_configuration(
            options=options, environ={"MOBIRAEON_API_" + setting.upper(): str(value)}
        )
        assert resolved.api[setting] == value
