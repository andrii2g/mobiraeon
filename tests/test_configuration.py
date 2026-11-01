import pytest

from mobiraeon.configuration import resolve_configuration
from mobiraeon.errors import SafeError


def resolve(tmp_path, options=None, env=None):
    return resolve_configuration(options=options or {}, environ=env or {}, cwd=tmp_path)


def test_precedence_absent_overrides_and_source_relative_paths(tmp_path):
    folder = tmp_path / "config"
    folder.mkdir()
    file = folder / "app.toml"
    file.write_text('[database]\npath="../data/store.db"\ntimeout_seconds=2\n')
    config = resolve(tmp_path, {"config": "config/app.toml"})
    assert config.database_path == tmp_path / "data" / "store.db"
    assert config.timeout_seconds == 2
    assert config.log_level == "INFO"
    env = {
        "MOBIRAEON_CONFIG": "config/app.toml",
        "MOBIRAEON_DATABASE_PATH": "env.db",
        "MOBIRAEON_LOG_LEVEL": "debug",
    }
    config = resolve(tmp_path, {"database_timeout_seconds": "3"}, env)
    assert config.database_path == tmp_path / "env.db"
    assert config.timeout_seconds == 3
    assert config.log_level == "DEBUG"
    assert resolve(tmp_path, {"database": "cli.db"}, env).database_path == tmp_path / "cli.db"
    assert not (tmp_path / "data").exists()


@pytest.mark.parametrize(
    "value", ["", ":memory:", "file:test?mode=memory", "sqlite:///a", "\x00"]
)
def test_invalid_paths(tmp_path, value):
    with pytest.raises(SafeError):
        resolve(tmp_path, {"database": value})


@pytest.mark.parametrize("value", [True, False, 0, -1, 61, "nan", "inf", "secret", [], {}])
def test_invalid_timeouts(tmp_path, value):
    with pytest.raises(SafeError):
        resolve(tmp_path, {"database": "a", "database_timeout_seconds": value})


@pytest.mark.parametrize(
    "contents",
    [
        "[database",
        '[unknown]\nsecret="s"',
        '[database]\nunknown="s"',
        "[database]\npath=true",
        '[database]\npath="a"\ntimeout_seconds=true',
        '[database]\npath="a"\ntimeout_seconds="2"',
        "[logging]\nlevel=2",
        '[logging]\nlevel="secret"',
        'database="secret"',
    ],
)
def test_invalid_file_is_rejected_even_when_overridden(tmp_path, contents):
    (tmp_path / "config.toml").write_text(contents)
    with pytest.raises(SafeError):
        resolve(tmp_path, {"config": "config.toml", "database": "valid", "log_level": "INFO"})


def test_invalid_lower_environment_source_and_unknown_names(tmp_path):
    with pytest.raises(SafeError):
        resolve(tmp_path, {"database": "good"}, {"MOBIRAEON_DATABASE_PATH": ""})
    with pytest.raises(SafeError):
        resolve(tmp_path, {"database": "good"}, {"MOBIRAEON_SECRET": "s"})
    assert resolve(tmp_path, {"database": "good"}, {"OTHER_SECRET": "s"})


def test_missing_required_path_and_selected_missing_file(tmp_path):
    with pytest.raises(SafeError):
        resolve(tmp_path)
    with pytest.raises(SafeError):
        resolve(tmp_path, {"config": "missing", "database": "good"})


def test_restart_resolves_changes_without_mutating_previous_configuration(tmp_path):
    first = resolve(tmp_path, {"database": "first"})
    second = resolve(tmp_path, {"database": "second"})
    assert first.database_path != second.database_path
    assert first.database_path.name == "first"


def test_selected_unreadable_file_and_config_selector_precedence(tmp_path):
    with pytest.raises(SafeError):
        resolve(tmp_path, {"config": ".", "database": "good"})
    (tmp_path / "selected.toml").write_text('[database]\npath="selected.db"')
    config = resolve(
        tmp_path, {"config": "selected.toml"}, {"MOBIRAEON_CONFIG": "not-selected"}
    )
    assert config.database_path == tmp_path / "selected.db"
