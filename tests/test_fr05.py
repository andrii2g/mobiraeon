"""FR-05 tooling runs only in disposable Git fixtures; never mutates project Git."""

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def checkout(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "tools").mkdir()
    for name in ["capture_submission.py", "source_integrity.py"]:
        if (ROOT / "tools" / name).exists():
            shutil.copyfile(ROOT / "tools" / name, root / "tools" / name)

    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=root, check=True, capture_output=True, timeout=15
        )

    git("init")
    git("config", "user.email", "fixture@example.invalid")
    git("config", "user.name", "Disposable Fixture")
    (root / ".gitignore").write_text("submissions/\n__pycache__/\n")
    (root / "old.txt").write_text("original")
    git("add", ".")
    git("commit", "-m", "fixture only")
    return root, git


def capture(root, injection=None):
    command = [
        sys.executable,
        str(root / "tools/capture_submission.py"),
        "--output-directory",
        str(root / "submissions/run"),
    ]
    if injection:
        command = [sys.executable, "-c", injection, *command[1:]]
    return subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=20)


def verifier():
    p = ROOT / "tools/source_integrity.py"
    assert p.exists(), "deletion verifier missing"
    spec = importlib.util.spec_from_file_location("fixture_integrity", p)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.verify_source


@pytest.mark.parametrize(
    "change",
    [
        "unchanged",
        "unstaged_delete",
        "staged_delete",
        "unstaged_rename",
        "staged_rename",
        "mixed",
    ],
)
def test_fr05_combined_checkout(checkout, tmp_path, change):
    root, git = checkout
    if "rename" in change:
        (root / "old.txt").rename(root / "new.txt")
    elif "delete" in change:
        (root / "old.txt").unlink()
    elif change == "mixed":
        (root / "old.txt").write_text("modified")
        (root / "new.txt").write_text("untracked")
    if change.startswith("staged"):
        git("add", "-A")
    before = git("status", "--porcelain=v1", "-z").stdout
    r = capture(root)
    assert r.returncode == 0, (r.stdout, r.stderr)
    output = root / "submissions/run"
    m = json.loads((output / "source-manifest.json").read_text())
    assert m.get("deleted_paths", []) == (
        ["old.txt"] if "delete" in change or "rename" in change else []
    )
    assert (
        all("old.txt" != n for n in m.get("deleted_paths", []))
        if change in ["unchanged", "mixed"]
        else "old.txt" not in m["files"]
    )
    extract = tmp_path / "extract"
    extract.mkdir()
    with zipfile.ZipFile(output / "source.zip") as z:
        z.extractall(extract)
    verify = verifier()
    verify(extract, m)
    assert before == git("status", "--porcelain=v1", "-z").stdout
    if m.get("deleted_paths"):
        (extract / "old.txt").write_text("restored stale file")
        with pytest.raises(ValueError):
            verify(extract, m)
    else:
        legacy = dict(m)
        legacy.pop("deleted_paths", None)
        verify(extract, legacy)


@pytest.mark.parametrize("failure", ["unreadable", "unexpected", "secret"])
def test_fr05_failure_and_prior_preservation(checkout, failure):
    root, _ = checkout
    assert capture(root).returncode == 0
    old = (root / "submissions/run/source.zip").read_bytes()
    if failure == "secret":
        (root / "secret.token").write_text("synthetic private input")
        injection = None
    else:
        exception = "PermissionError" if failure == "unreadable" else "OSError"
        injection = (
            "import pathlib,runpy,sys;original=pathlib.Path.read_bytes\n"
            "def read(p):\n if p.name=='old.txt':raise "
            + exception
            + "('trusted injected read failure')\n return original(p)\n"
            "pathlib.Path.read_bytes=read\nsys.argv=sys.argv[1:];"
            "runpy.run_path(sys.argv[0],run_name='__main__')"
        )
        injection = "import sys;sys.path.insert(0,'tools');" + injection
    r = capture(root, injection)
    assert r.returncode != 0
    output = root / "submissions/run"
    assert not (output / "source-manifest.json").exists()
    assert not (output / "source.zip.pending").exists()
    preserved = list((output / "archive").glob("*/source.zip"))
    assert len(preserved) == 1 and preserved[0].read_bytes() == old
    m = json.loads(preserved[0].with_name("source-manifest.json").read_text())
    assert hashlib.sha256(old).hexdigest() == m["archive_sha256"]


@pytest.mark.parametrize(
    "deleted",
    [
        ["../outside"],
        ["/absolute"],
        ["C:/bad"],
        ["a\\b"],
        [".git/config"],
        ["a", "a"],
        ["z", "a"],
        ["./a"],
        [None],
        "a",
    ],
)
def test_fr05_reject_unsafe_declarations(tmp_path, deleted):
    with pytest.raises(ValueError):
        verifier()(tmp_path, {"files": {}, "deleted_paths": deleted})


def test_fr05_platform_consumer_refuses_restored_deletion(tmp_path):
    import ast

    module = ast.parse((ROOT / "tools/verify_platform.py").read_text())
    function = next(
        n
        for n in ast.walk(module)
        if isinstance(n, ast.FunctionDef) and n.name == "verify_source"
    )
    (tmp_path / "stale.txt").write_text("must remain present and be refused")
    environment = {
        "root": tmp_path,
        "manifest": {"files": {}, "deleted_paths": ["stale.txt"]},
        "check_source": verifier(),
        "hashlib": hashlib,
    }
    exec(
        compile(
            ast.Module(body=[function], type_ignores=[]), "candidate-platform-verifier", "exec"
        ),
        environment,
    )
    with pytest.raises(ValueError):
        environment["verify_source"]()
    assert (tmp_path / "stale.txt").read_text() == "must remain present and be refused"
