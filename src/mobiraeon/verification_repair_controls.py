"""Trusted no-Docker reporting/observation controls, never live qualification.

The tests call actual verifier entry points and shared assertion paths. Synthetic
observations cannot be selected by an application request or ordinary CLI input.
"""

import contextlib
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import httpx2

import mobiraeon.execution_diagnostics as diagnostics
import mobiraeon.execution_verification as execution
import mobiraeon.forge_gitea_verification as forge
from mobiraeon.contracts import Operation, OperationResult, Outcome
from mobiraeon.errors import Reason
from mobiraeon.persistence import Store
from mobiraeon.private_state import durable_new, harden


def operation(outcome=Outcome.REFUSED):
    return OperationResult(uuid4(), Operation.EXECUTION_RUN, outcome, Reason.REFUSED)


def exported_main(callback):
    output = io.StringIO()
    argv = [
        "trusted-reporting-control",
        "--input",
        "input.json",
        "--catalog-input",
        "catalog.json",
        "--image-id",
        "sha256:" + "a" * 64,
    ]
    with (
        patch.object(sys, "argv", argv),
        patch.object(execution, "exercise", callback),
        contextlib.redirect_stdout(output),
    ):
        code = execution.main()
    return code, json.loads(output.getvalue())


def export_and_retire(report):
    """Only this controller's synthetic state: no real Run, credentials or Docker effects."""
    root = Path(report["protected_state"]["directory"])
    saved = root / "verification-failure.json"
    result = {
        "protected_state_existed_before_cleanup": root.is_dir(),
        "diagnostic_file_existed": saved.is_file(),
        "durable": json.loads(saved.read_text(encoding="utf-8")) if saved.is_file() else None,
    }
    assert root.resolve().parent == Path(tempfile.gettempdir()).resolve()
    assert root.name.startswith("mobiraeon-execution-check-")
    assert not list(root.rglob("*.token")) and not list(root.rglob("credentials"))
    shutil.rmtree(root)
    result["controlled_cleanup"] = "removed_after_export; no real external Run or credentials"
    return result


def uuid_case(prior=True, disk_failure=False):
    earlier = operation()

    def controlled(*args, **kwargs):
        checks = diagnostics.CheckLog("controlled-image")
        if prior:
            checks.append(
                {
                    "case": "registry_admin_without_execution_grants",
                    "result": "passed",
                    "operation": asdict(earlier),
                }
            )
        with diagnostics.verification_workspace(checks):
            diagnostics.check_failure_terminal(
                checks,
                dict(
                    outcome="failed",
                    cleanup="unverified",
                    artifact_valid=False,
                    held=True,
                    terminal=False,
                    attachment_exit_code=17,
                ),
                "failed",
            )

    def unavailable(*args):
        raise OSError("CONTROLLED_STORAGE_UNAVAILABLE")

    with contextlib.ExitStack() as stack:
        if disk_failure:
            stack.enter_context(
                patch.object(diagnostics, "durable_new", side_effect=unavailable)
            )
        code, report = exported_main(controlled)
    exported = export_and_retire(report)
    saved = exported["durable"]
    required = (
        code != 0
        and report["result"] == "failed"
        and report["failure_type"] == "AssertionError"
        and report["observed_terminal"]["cleanup"] == "unverified"
        and exported["protected_state_existed_before_cleanup"]
    )
    if disk_failure:
        required &= not report["diagnostic_storage"]["available"] and saved is None
        required &= report["diagnostic_storage"]["failure_type"] == "OSError"
    else:
        required &= bool(report["diagnostic_storage"]["available"] and saved == report)
    if prior:
        required &= report["checks"][0]["operation"]["invocation_id"] == str(
            earlier.invocation_id
        )
    return dict(
        required_behavior=bool(required), child_main_exit=code, emitted=report, **exported
    )


def miniature_fixture(directory, *, record=None):
    """Synthetic disk SQLite for observation provenance; no access bootstrap."""
    directory.mkdir()
    harden(directory)
    database = directory / "controlled.db"
    store = Store(database)
    store.initialize()
    harden(database)
    with store.engine.begin() as tx:
        tx.exec_driver_sql(
            "INSERT INTO coordination_tasks(id,version,state) VALUES('task-1',3,'allocated')"
        )
        if record is not None:
            tx.exec_driver_sql(
                "INSERT INTO execution_runs(task,attempt,handoff,generation,held,record) "
                "VALUES('task-1','controlled-attempt',?,1,?,?)",
                (
                    json.dumps(
                        {
                            "settings": {
                                "engine_id": "controlled-engine",
                                "image_id": "controlled-image",
                            }
                        }
                    ),
                    int(record["held"]),
                    json.dumps(record),
                ),
            )
            tx.exec_driver_sql(
                "INSERT INTO execution_events(task,record) VALUES('task-1',?)",
                (json.dumps({"event": "controlled_variant_observation", "at": 1}),),
            )
            tx.exec_driver_sql(
                "INSERT INTO coordination_facts(task,stage,identity,record) "
                "VALUES('task-1','observe','controlled-observe',?)",
                (json.dumps({"inputs": {"observation": "failed", "detail": record["seal"]}}),),
            )
    durable_new(
        directory / "settings.toml",
        (
            "[database]\npath="
            + json.dumps(str(database))
            + "\n[access]\nprivate_dir="
            + json.dumps(str(directory))
            + "\n"
        ).encode(),
    )
    durable_new(directory / "run.json", b'{"inputs":{"mode":"success"}}')
    store.close()
    return database


def admission_case(wrong=True):
    prepared = []

    class BoundaryReached(Exception):
        pass

    class ObservedExecution:
        def __init__(self, *args, **kwargs):
            pass

        def invoke(self, *args, **kwargs):
            return operation(Outcome.SUCCESS if wrong else Outcome.REFUSED)

    def preparation(command, **kwargs):
        if command[1:3] != ["-m", "mobiraeon.execution_fixture"]:
            raise BoundaryReached("trusted post-admission boundary; no public Run executed")
        directory = Path(command[command.index("--directory") + 1])
        miniature_fixture(directory)
        prepared.append(str(directory))
        return subprocess.CompletedProcess(command, 0, '{"prepared":true}', "")

    actual = execution.exercise

    def controlled(*args, **kwargs):
        return actual(*args, **kwargs)

    with (
        patch.object(execution.sys, "platform", "linux"),
        patch.object(execution.subprocess, "run", side_effect=preparation),
        patch.object(execution, "PrivateState", return_value=object()),
        patch.object(execution, "ExecutionService", ObservedExecution),
        patch.object(execution, "proof_for", return_value=None),
    ):
        code, report = exported_main(controlled)
    exported = export_and_retire(report)
    if wrong:
        required = (
            code != 0
            and report["failure_type"] == "AssertionError"
            and report["active"]["case"] == "registry_admin_without_execution_grants"
            and report["active"]["stage"] == "admission"
            and report["active"].get("directory") == prepared[0]
            and report["active"]["mode"] == "success"
            and not report["terminal_available"]
            and report["pre_cleanup_snapshot"]["available"]
            and report["pre_cleanup_snapshot"].get("fixture_directory") == prepared[0]
            and report["failure_site"]["function"] == "exercise"
            and "refused.outcome == Outcome.REFUSED" in report["expected_condition"]
            and bool(report["active"]["expected"])
            and exported["durable"] == report
        )
    else:
        required = (
            code != 0
            and report["failure_type"] == "BoundaryReached"
            and any(
                c.get("case") == "registry_admin_without_execution_grants"
                for c in report["checks"]
            )
        )
    return dict(
        required_behavior=bool(required),
        child_main_exit=code,
        emitted=report,
        preparation_succeeded=True,
        **exported,
    )


def variant_case(wrong=True):
    if not hasattr(execution, "verify_trusted_variant"):
        return dict(
            required_behavior=False,
            baseline_shared_helper_unavailable=True,
            reason="baseline R3 uses actual admission; no mirrored variant assertion",
        )
    earlier = operation()
    observed = dict(
        outcome="failed",
        cleanup="verified",
        artifact_valid=False,
        held=False,
        terminal=True,
        seal="controlled-seal",
        attachment_exit_code=1,
    )
    roots = []

    def controlled(*args, **kwargs):
        checks = diagnostics.CheckLog("controlled-image")
        checks.append(
            {"case": "earlier_operation", "result": "passed", "operation": asdict(earlier)}
        )
        with diagnostics.verification_workspace(checks) as root:
            roots.append(root)
            directory = root / "controlled-variant"
            record = observed | {"capture_path": str(directory / "capture.json")}
            database = miniature_fixture(directory, record=record)
            durable_new(
                directory / "capture.json",
                b'{"stdout":"","stderr":"CONTROLLED_VARIANT_SENTINEL","complete":true}',
            )
            fake = SimpleNamespace(
                invoke=lambda *a, **k: operation(Outcome.SUCCESS if wrong else Outcome.FAILURE),
                load=lambda task: ({}, record),
            )
            store = Store(database)
            try:
                execution.verify_trusted_variant(
                    checks, directory, "invalid", store, object(), fake
                )
            finally:
                store.close()
            return {"result": "passed", "checks": checks, "active": checks.active}

    with patch.object(execution, "proof_for", return_value=None):
        code, report = exported_main(controlled)
    if not wrong:
        return dict(
            required_behavior=code == 0
            and report["result"] == "passed"
            and not roots[0].exists(),
            child_main_exit=code,
            emitted=report,
            controlled_cleanup="successful synthetic state removed",
        )
    exported = export_and_retire(report)
    required = (
        code != 0
        and report["failure_type"] == "AssertionError"
        and report["active"]["case"] == "trusted_variant"
        and report["active"]["stage"] == "terminal_assertion"
        and report["active"]["variant"] == "invalid"
        and report["active"]["mode"] == "success"
        and report["active"]["directory"].endswith("controlled-variant")
        and report["pre_cleanup_snapshot"]["fixture_directory"] == report["active"]["directory"]
        and report["pre_cleanup_snapshot"]["record"]["seal"] == observed["seal"]
        and report["pre_cleanup_snapshot"]["events"][0]["event"]
        == "controlled_variant_observation"
        and report["terminal_available"]
        and report["observed_terminal"]["cleanup"] == "verified"
        and report["failure_site"]["function"] == "verify_trusted_variant"
        and report["checks"][0]["operation"]["invocation_id"] == str(earlier.invocation_id)
        and exported["durable"] == report
    )
    return dict(
        required_behavior=bool(required), child_main_exit=code, emitted=report, **exported
    )


def readiness_case(kind):
    clock = SimpleNamespace(now=0.0)
    state = {"name": None, "port": None, "provisioning_attempted": False, "calls": []}
    proxies = []

    class BoundaryReached(Exception):
        pass

    class Reserve:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def bind(self, address):
            pass

        def getsockname(self):
            return ("127.0.0.2", 31001)

    class Proxy:
        def __init__(self, upstream):
            self.upstream = upstream
            self.origin = "http://127.0.0.1:31002"
            self.routes = []
            self.thread = SimpleNamespace(start=lambda: None)
            proxies.append(self)

        def close(self):
            pass

    def docker(argv, **kwargs):
        args = argv[1:]
        body = ""
        if args[0] == "version":
            body = json.dumps({"Client": {"Version": "controlled"}})
        elif args[0] == "info":
            body = json.dumps("controlled-engine")
        elif args[:2] == ["context", "show"]:
            body = "controlled"
        elif args[:2] == ["context", "inspect"]:
            body = json.dumps("unix:///controlled.sock")
        elif args[:2] == ["image", "inspect"]:
            body = json.dumps(
                [{"Id": "controlled-image", "RepoDigests": ["controlled-digest"]}]
            )
        elif args[0] == "run" and "--rm" in args:
            body = "gitea version 28.2.0 (controlled)"
        elif args[:2] == ["network", "create"]:
            state["name"] = args[-1]
            body = state["name"]
        elif args[0] == "run":
            state["port"] = args[args.index("-p") + 1].split(":")[1]
            body = "controlled-container"
        elif args[0] == "inspect":
            body = json.dumps(
                [
                    {
                        "Name": "/" + state["name"],
                        "Config": {"Labels": {"mobiraeon.verification": state["name"]}},
                        "State": {"Running": True, "Status": "running", "ExitCode": 0},
                        "NetworkSettings": {
                            "Ports": {
                                "3000/tcp": [{"HostIp": "127.0.0.2", "HostPort": state["port"]}]
                            },
                            "Networks": {state["name"]: {"IPAddress": "172.30.0.2"}},
                        },
                    }
                ]
            )
        elif args[:2] == ["network", "inspect"]:
            body = json.dumps([{"Labels": {"mobiraeon.verification": state["name"]}}])
        elif args[0] == "exec":
            state["provisioning_attempted"] = True
            raise BoundaryReached(
                "trusted acceptance boundary; no users/tokens or provider assertions"
            )
        return subprocess.CompletedProcess(argv, 0, body, "")

    class Client:
        published_calls = 0

        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, url, *, timeout):
            assert 0 < timeout <= 1
            clock.now += min(0.05, timeout)
            state["calls"].append(url)
            published = url.startswith("http://127.0.0.2:")
            if published:
                self.published_calls += 1
            if kind == "unavailable" or (
                published
                and (kind == "private" or (kind == "transient" and self.published_calls <= 2))
            ):
                raise httpx2.ConnectError("controlled refusal")
            if kind == "malformed":
                return httpx2.Response(200, content=b"NOT_JSON")
            return httpx2.Response(
                503 if kind == "non_200" else 200,
                json={"version": "29.0.0" if kind == "wrong_version" else "28.2.0"},
            )

    with (
        patch.object(forge.platform, "system", return_value="Linux"),
        patch.object(forge.platform, "platform", return_value="controlled startup composition"),
        patch.object(forge.os, "getuid", return_value=1000, create=True),
        patch.object(forge.os, "getgid", return_value=1000, create=True),
        patch.object(forge.os, "readlink", return_value="controlled-netns"),
        patch.object(forge.socket, "socket", Reserve),
        patch.object(forge, "LostAckProxy", Proxy),
        patch.object(forge.subprocess, "run", side_effect=docker),
        patch.object(forge.httpx2, "Client", Client),
        patch.object(forge.time, "monotonic", lambda: clock.now),
        patch.object(forge.time, "sleep", lambda n: setattr(clock, "now", clock.now + n)),
    ):
        report = forge.exercise("controlled-docker")
    pub = report.get("publication", {})
    route = (
        forge.published_route(
            pub,
            SimpleNamespace(
                upstream=proxies[0].upstream, routes=[{"upstream": proxies[0].upstream}]
            ),
        )
        if pub
        else False
    )
    if kind in {"positive", "transient"}:
        required = bool(
            pub.get("ready_on_published_endpoint")
            and report.get("stage") == "api_available"
            and state["provisioning_attempted"]
            and route
        )
    elif kind == "private":
        required = bool(
            not pub.get("ready_on_published_endpoint")
            and report.get("published_loopback_limitation")
            and not route
            and state["provisioning_attempted"]
        )
    else:
        required = bool(
            not pub.get("ready_on_published_endpoint")
            and not report.get("actual_api_version")
            and report.get("stage") != "api_available"
            and not state["provisioning_attempted"]
            and not route
        )
    required &= (
        report["result"] != "passed"
        and report["cleanup"] == "verified_owned_resources_removed"
        and clock.now <= 25.000001
    )
    if kind in {"non_200", "private", "unavailable"}:
        required &= clock.now >= 25
    return dict(
        required_behavior=bool(required),
        fixture_report=report,
        elapsed_fake_seconds=clock.now,
        provisioning_attempted=state["provisioning_attempted"],
        published_route_predicate=route,
        later_provider_assertions_executed=False,
    )


def run_case(name):
    if name == "uuid":
        result = uuid_case()
    elif name == "no_uuid":
        result = uuid_case(prior=False)
    elif name == "disk_failure":
        result = uuid_case(prior=False, disk_failure=True)
    elif name == "uuid_disk_failure":
        result = uuid_case(prior=True, disk_failure=True)
    elif name == "admission":
        result = admission_case()
    elif name == "admission_pass":
        result = admission_case(wrong=False)
    elif name == "variant":
        result = variant_case()
    elif name == "variant_pass":
        result = variant_case(wrong=False)
    else:
        result = readiness_case(name)
    result.update(
        scope=(
            "trusted reporting/observation injection; "
            "not application authority or live provider/Worker qualification"
        ),
        module_paths={
            "diagnostics": diagnostics.__file__,
            "execution": execution.__file__,
            "gitea": forge.__file__,
        },
    )
    result["module_hashes"] = {
        name: hashlib.sha256(Path(path).read_bytes()).hexdigest()
        for name, path in result["module_paths"].items()
    }
    return result
