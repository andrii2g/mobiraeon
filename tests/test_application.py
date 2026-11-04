import json
import os
import signal
import subprocess
import sys

import pytest

from mobiraeon import cli

SECRET = "SYNTHETIC_SENSITIVE_9f0e"


def clean_env():
    return {k: v for k, v in os.environ.items() if not k.startswith("MOBIRAEON_")}


def run(*args, cwd=None, env=None):
    return subprocess.run(
        [sys.executable, "-m", "mobiraeon", *map(str, args)],
        cwd=cwd,
        env=clean_env() | (env or {}),
        capture_output=True,
        text=True,
        timeout=15,
    )


def test_cli_lifecycle_and_restart_outside_checkout(tmp_path):
    database = tmp_path / "app.db"
    assert run("--help", cwd=tmp_path).returncode == 0
    assert run("--version", cwd=tmp_path).stdout.strip() == "0.1.0"
    missing = run("--database", database, "check", cwd=tmp_path)
    assert missing.returncode != 0
    assert not database.exists()
    for command in ("initialize", "initialize", "upgrade", "check"):
        result = run("--database", database, command, cwd=tmp_path)
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["schema_revision"] == "0005"
    # A subprocess runs the real CLI/host with a controlled stop event on Windows,
    # where CI may lack a console for Ctrl+Break delivery. No production stop flag.
    script = """
import threading
from mobiraeon import cli
stop = threading.Event()
original = cli.serve
cli.serve = lambda: original(stop)
threading.Timer(0.4, stop.set).start()
raise SystemExit(cli.main())
"""
    for _ in range(2):
        process = subprocess.run(
            [
                sys.executable,
                "-c",
                script,
                "--database",
                str(database),
                "--log-level",
                "CRITICAL",
                "start",
            ],
            cwd=tmp_path,
            env=clean_env(),
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert process.returncode == 0, process.stderr
        output, terminal = [json.loads(line) for line in process.stdout.splitlines()]
        assert output["foundation_ready"] is True
        assert output["phase"] == "ready"
        assert terminal["phase"] == "terminal" and terminal["outcome"] == "success"
        assert terminal["foundation_ready"] is False
        assert (
            output["capabilities"]["registry_business_operations"]
            == "authenticated_administration"
        )
        assert output["capabilities"]["agent_execution"] == "unavailable"
        events = [json.loads(line)["event"] for line in process.stderr.splitlines()]
        assert events == ["foundation_ready", "stopped"]
    assert run("--database", database, "check", cwd=tmp_path).returncode == 0


@pytest.mark.parametrize(
    "signum", [signal.SIGINT, signal.SIGTERM] + ([signal.SIGBREAK] if os.name == "nt" else [])
)
def test_signal_handler_requests_clean_shutdown(monkeypatch, signum):
    handlers = {}

    def register(signum, handler):
        previous = handlers.get(signum, signal.SIG_DFL)
        handlers[signum] = handler
        return previous

    class Stop:
        stopped = False

        def set(self):
            self.stopped = True

        def wait(self, timeout):
            assert 0 < timeout <= 1
            handlers[signum](signum, None)
            # Native callbacks only record intent; normal flow sets the event.
            return self.stopped

    monkeypatch.setattr(signal, "signal", register)
    cli.serve(Stop())
    assert set(handlers.values()) == {signal.SIG_DFL}


@pytest.mark.parametrize(
    "args,env,contents",
    [
        (["--" + SECRET], {}, None),
        ([SECRET], {}, None),
        (["--database"], {}, None),
        (["--database-timeout-seconds", SECRET, "check"], {}, None),
        (["check"], {"MOBIRAEON_" + SECRET: SECRET}, None),
        (["check"], {"MOBIRAEON_DATABASE_TIMEOUT_SECONDS": SECRET}, None),
        (["check"], {}, '[database]\npath="' + SECRET + '"\ntimeout_seconds=true'),
        (["check"], {}, "[" + SECRET),
        (["check"], {}, "[" + SECRET + ']\nvalue="' + SECRET + '"'),
    ],
)
def test_parser_configuration_diagnostics_never_echo_sensitive_values(
    tmp_path, args, env, contents
):
    if contents is not None:
        config = tmp_path / "config.toml"
        config.write_text(contents)
        args = ["--config", str(config), *args]
    process = run(*args, env=env, cwd=tmp_path)
    assert process.returncode != 0
    assert SECRET not in process.stdout + process.stderr
    assert "foundation_ready" not in process.stdout + process.stderr
    assert json.loads(process.stderr)["event"] == "command_error"


def test_real_configuration_precedence_reaches_storage_from_another_cwd(tmp_path):
    directory = tmp_path / "config"
    directory.mkdir()
    config = directory / "app.toml"
    config.write_text('[database]\npath="file.db"\ntimeout_seconds=0.1')
    assert run("--config", config, "initialize", cwd=tmp_path).returncode == 0
    assert (directory / "file.db").exists()
    env = {"MOBIRAEON_CONFIG": str(config), "MOBIRAEON_DATABASE_PATH": "env.db"}
    assert run("initialize", env=env, cwd=tmp_path).returncode == 0
    assert (tmp_path / "env.db").exists()
    assert run("--database", "cli.db", "initialize", env=env, cwd=tmp_path).returncode == 0
    assert (tmp_path / "cli.db").exists()


def test_invalid_configuration_never_constructs_application(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        cli, "Application", lambda config: pytest.fail("initialized dependency")
    )
    monkeypatch.setattr(os, "environ", clean_env())
    assert cli.main(["--database-timeout-seconds", "0", "initialize"]) == 2
    assert json.loads(capsys.readouterr().err)["reason"] == "configuration_invalid"


def test_storage_exception_is_sanitized_and_cleanup_allows_restart(store, monkeypatch, capsys):
    monkeypatch.setattr(os, "environ", clean_env())

    def fail(self):
        raise RuntimeError(SECRET)

    with monkeypatch.context() as scoped:
        scoped.setattr("mobiraeon.persistence.Store.check", fail)
        assert cli.main(["--database", str(store.path), "start"]) == 1
        output = capsys.readouterr()
        assert SECRET not in output.out + output.err
        assert "foundation_ready" not in output.out + output.err
    assert cli.main(["--database", str(store.path), "check"]) == 0


def test_missing_store_and_secret_path_are_safe_even_at_debug(tmp_path):
    result = run("--database", tmp_path / SECRET, "--log-level", "DEBUG", "start", cwd=tmp_path)
    assert result.returncode != 0
    assert SECRET not in result.stdout + result.stderr
    assert "foundation_ready" not in result.stdout + result.stderr
    assert not (tmp_path / SECRET).exists()


@pytest.mark.parametrize("source", ["cli", "environment", "file"])
def test_success_status_never_exposes_setting_values(tmp_path, source):
    args = ["--log-level", "DEBUG"]
    env = {}
    if source == "cli":
        args += ["--database", SECRET]
    elif source == "environment":
        env = {"MOBIRAEON_DATABASE_PATH": SECRET}
    else:
        config = tmp_path / "config.toml"
        config.write_text('[database]\npath="' + SECRET + '"')
        args += ["--config", str(config)]
    for command in ("initialize", "check"):
        result = run(*args, command, cwd=tmp_path, env=env)
        assert result.returncode == 0, result.stderr
        assert SECRET not in result.stdout + result.stderr
        assert json.loads(result.stdout)["outcome"] == "success"
