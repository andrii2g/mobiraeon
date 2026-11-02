"""Run identical repair expectations against source or a clean installed package."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


def exercise(python, candidate_root, *, suite_root=None, include_tools=True):
    candidate_root = Path(candidate_root)
    suite_root = Path(suite_root or candidate_root)
    environment = {k: v for k, v in os.environ.items() if not k.startswith("MOBIRAEON_")}
    environment.pop("PYTHONPATH", None)
    with tempfile.TemporaryDirectory(prefix="mobiraeon-fr-regressions-") as temporary:
        outside = Path(temporary)
        (outside / "tests").mkdir()
        (outside / "tools").mkdir()
        for folder in ["examples", "bootstrap"]:
            shutil.copytree(candidate_root / folder, outside / folder)
        names = ["test_fr01.py", "test_fr02.py", "test_fr03.py", "test_fr04.py"]
        if include_tools:
            names.extend(["test_fr05.py", "test_fr06.py"])
        copied = {}
        for name in names + [
            "test_execution.py",
            "test_registry.py",
            "test_increment2_repairs.py",
        ]:
            data = (suite_root / "tests" / name).read_bytes()
            (outside / "tests" / name).write_bytes(data)
            copied[name] = hashlib.sha256(data).hexdigest()
        for name in [
            "capture_submission.py",
            "source_integrity.py",
            "verify_platform.py",
            "verify_foundation.py",
            "verify_fr_repairs.py",
            "verify_wheel.py",
        ]:
            if (candidate_root / "tools" / name).exists():
                shutil.copyfile(candidate_root / "tools" / name, outside / "tools" / name)
        shutil.copyfile(
            suite_root / "tools/foundation_signal_verification.py",
            outside / "tools/foundation_signal_verification.py",
        )
        # This pure checker belongs to the regression harness. Baseline capture
        # remains byte-identical and still must declare its own deletions.
        shutil.copyfile(
            suite_root / "tools/source_integrity.py", outside / "tools/source_integrity.py"
        )
        imported = subprocess.run(
            [
                str(python),
                "-c",
                'import mobiraeon,json;print(json.dumps({"module":mobiraeon.__file__}))',
            ],
            cwd=outside,
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert imported.returncode == 0, imported.stderr
        command = [
            str(python),
            "-m",
            "pytest",
            "-q",
            "--capture=tee-sys",
            "--tb=short",
            "--junitxml",
            str(outside / "cases.xml"),
            *[str(outside / "tests" / name) for name in names],
        ]
        result = subprocess.run(
            command, cwd=outside, env=environment, capture_output=True, text=True, timeout=240
        )
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "probe", suite_root / "tools/foundation_signal_verification.py"
        )
        probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(probe)
        signals = probe.exercise(python=python)
        cases = []
        if (outside / "cases.xml").exists():
            for case in ET.parse(outside / "cases.xml").iter("testcase"):
                cases.append(
                    dict(
                        group=case.get("classname"),
                        case=case.get("name"),
                        result="failed"
                        if case.find("failure") is not None or case.find("error") is not None
                        else "passed",
                    )
                )
        return dict(
            result="passed"
            if result.returncode == 0 and signals["result"] == "passed"
            else "failed",
            command=command,
            cwd=str(outside),
            candidate_root=str(candidate_root),
            suite_root=str(suite_root),
            imported=json.loads(imported.stdout),
            tests_sha256=copied,
            tools_sha256={
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (outside / "tools").glob("*.py")
            },
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            cases=cases,
            foundation_signals=signals,
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-python", default=sys.executable)
    parser.add_argument(
        "--candidate-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--suite-root", type=Path)
    parser.add_argument("--without-tools", action="store_true")
    args = parser.parse_args()
    report = exercise(
        args.target_python,
        args.candidate_root,
        suite_root=args.suite_root,
        include_tools=not args.without_tools,
    )
    print(json.dumps(report, indent=2))
    return int(report["result"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
