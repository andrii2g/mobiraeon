"""Internal final-07 required-behavior controls; never public workflow authority.

Portable nested tests compose the real parent helper/main with trusted observations,
not Docker or real identities. Tool tests identify the separately captured source tool.
"""

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from mobiraeon import execution_diagnostics as diagnostics
from mobiraeon import execution_repair_verification as nested
from mobiraeon import execution_verification as parent
from mobiraeon.access import credential_proof, execute
from mobiraeon.configuration import resolve_configuration
from mobiraeon.contracts import Outcome
from mobiraeon.errors import Reason, SafeError
from mobiraeon.forge import ForgeService
from mobiraeon.forge_verification import Installation, Loopback
from mobiraeon.persistence import Store
from mobiraeon.private_state import PrivateState, durable_new, harden
from mobiraeon.verification_repair_controls import miniature_fixture, operation

OUT = "F7_NESTED_STDOUT_SENTINEL"
ERR = "F7_NESTED_STDERR_SENTINEL"


def nested_control(case):
    """Execute actual packaged parent main and its actual nested integration helper."""
    if case == "optional_exit":
        checks = diagnostics.CheckLog("controlled-image")
        with patch.object(
            diagnostics.subprocess,
            "run",
            return_value=subprocess.CompletedProcess(
                ["trusted"], 1, '{"outcome":"success"}', ""
            ),
        ):
            result = checks.command(
                ["trusted"], cwd=Path(tempfile.gettempdir()), env={}, expect=None
            )
            strict_refused = False
            try:
                checks.command(["trusted"], cwd=Path(tempfile.gettempdir()), env={})
            except AssertionError:
                strict_refused = True
        return {
            "required_behavior": result == {"outcome": "success"} and strict_refused,
            "scope": "trusted explicit optional exit and strict default control",
            "checks": checks,
        }
    if case == "passing":
        roots = []

        def nested_success(*args):
            checks = diagnostics.CheckLog("controlled-image", module=nested.__file__)
            with diagnostics.verification_workspace(checks) as root:
                roots.append(root)
                checks.append({"case": "trusted_passing_nested", "result": "passed"})
            return {"result": "passed", "checks": checks, "image_id": "controlled-image"}

        def composed_success(*args, **kwargs):
            checks = diagnostics.CheckLog("controlled-image")
            checks.append({"case": "earlier_uuid", "operation": asdict(operation())})
            with diagnostics.verification_workspace(checks) as root:
                roots.append(root)
                parent.verify_nested_repairs(
                    checks, Path("input"), Path("catalog"), "controlled-image"
                )
            return {"result": "passed", "checks": checks, "image_id": "controlled-image"}

        output = io.StringIO()
        with (
            patch.object(parent, "exercise", composed_success),
            patch.object(nested, "exercise", nested_success),
            patch.object(
                sys,
                "argv",
                [
                    "trusted-parent",
                    "--input",
                    "input",
                    "--catalog-input",
                    "catalog",
                    "--image-id",
                    "controlled-image",
                ],
            ),
            contextlib.redirect_stdout(output),
        ):
            code = parent.main()
        report = json.loads(output.getvalue())
        return {
            "required_behavior": code == 0
            and report["result"] == "passed"
            and len(report["checks"]) == 2
            and len(report["checks"][-1]["regressions"]["checks"]) == 1
            and len(roots) == 2
            and not any(p.exists() for p in roots),
            "child_main_exit": code,
            "parent_report": report,
            "scope": "trusted passing parent/shared workspace; real cases qualified separately",
        }
    observations = {}
    record = dict(
        outcome="unknown",
        cleanup="unverified",
        artifact_valid=False,
        held=True,
        terminal=False,
        capture_complete=True,
        capture_channels={"stdout": "failed", "stderr": "eof"},
        seal="controlled-seal",
    )

    class ObservedExecution:
        def __init__(self, *args, **kwargs):
            pass

        def invoke(self, *args, **kwargs):
            return operation(Outcome.FAILURE if case == "later" else Outcome.SUCCESS)

        def load(self, *args):
            observed = record.copy()
            if case == "later" and observations["nested_directory"].name == "capture-stdout":
                observed.update(
                    cleanup="verified", held=False, terminal=True, capture_complete=False
                )
            return {}, observed

    def run(command, **kwargs):
        if command[1:3] == ["-m", "mobiraeon.execution_fixture"]:
            directory = Path(command[command.index("--directory") + 1])
            observations["nested_directory"] = directory
            if case in {"caught", "later", "cleanup_failure"}:
                prepared_record = record.copy()
                if case == "later" and directory.name == "capture-stdout":
                    prepared_record.update(
                        cleanup="verified", held=False, terminal=True, capture_complete=False
                    )
                miniature_fixture(directory, record=prepared_record)
                output, code = '{"prepared":true}', 0
            else:
                directory.mkdir()
                output, code = OUT, 17
            (directory / "partial-control-marker").write_text("nonsecret trusted partial state")
            if case == "timeout":
                raise subprocess.TimeoutExpired(
                    command, 240, output=OUT.encode(), stderr=ERR.encode()
                )
            if case == "launch":
                raise OSError("trusted launch unavailable")
            if case in {"malformed", "missing_json"}:
                output, code = ("INVALID_JSON" if case == "malformed" else ""), 0
            if case == "unexpected_exit":
                output, code = '{"prepared":true}', 7
            if case == "oversized":
                output = OUT + "x" * 300000
            return subprocess.CompletedProcess(command, code, output, ERR)
        assert command[-2:] == ["execution", "stop"], "control must never run a real child"
        observations["cleanup_requested"] = True
        if case == "cleanup_failure":
            raise OSError("trusted cleanup observation unavailable")
        (observations["nested_directory"] / "cleanup-observed").write_text(
            "cleanup after snapshot"
        )
        return subprocess.CompletedProcess(
            command,
            0,
            json.dumps(
                {
                    "data": {
                        "records": [
                            record | {"cleanup": "verified", "held": False, "terminal": True}
                        ]
                    }
                }
            ),
            "",
        )

    def composed(*args, **kwargs):
        checks = diagnostics.CheckLog("controlled-image")
        checks.append({"case": "earlier_outer_uuid", "operation": asdict(operation())})
        with diagnostics.verification_workspace(checks) as root:
            observations["parent_root"] = root
            parent.verify_nested_repairs(
                checks, Path("input.json"), Path("catalog.json"), "controlled-image"
            )
        return {"result": "passed", "checks": checks, "image_id": "controlled-image"}

    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.ExitStack() as stack:
        stack.enter_context(patch.object(sys, "platform", "linux"))
        stack.enter_context(patch.object(parent, "exercise", composed))
        stack.enter_context(patch.object(nested.subprocess, "run", side_effect=run))
        stack.enter_context(patch.object(nested, "ExecutionService", ObservedExecution))
        stack.enter_context(
            patch.object(nested, "PrivateState", return_value=SimpleNamespace())
        )
        stack.enter_context(
            patch.object(nested, "proof_for", return_value="trusted-observation")
        )
        stack.enter_context(
            patch.object(
                sys,
                "argv",
                [
                    "trusted-parent",
                    "--input",
                    "input.json",
                    "--catalog-input",
                    "catalog.json",
                    "--image-id",
                    "controlled-image",
                ],
            )
        )
        if case == "storage_failure":
            stack.enter_context(
                patch.object(
                    diagnostics,
                    "durable_new",
                    side_effect=OSError("trusted storage unavailable"),
                )
            )
        stack.enter_context(contextlib.redirect_stdout(stdout))
        stack.enter_context(contextlib.redirect_stderr(stderr))
        code = parent.main()
    report = json.loads(stdout.getvalue())
    nested_report = report["checks"][-1]["regressions"]
    nested_root = Path(nested_report["protected_state"]["directory"])
    parent_root = Path(report["protected_state"]["directory"])
    expected_type = {
        "timeout": "TimeoutExpired",
        "launch": "OSError",
        "malformed": "JSONDecodeError",
        "missing_json": "IndexError",
    }.get(case, "AssertionError")
    state_exists = (observations["nested_directory"] / "partial-control-marker").is_file()
    saved = {}
    for label, item in [("parent", report), ("nested", nested_report)]:
        path = Path(item["protected_state"]["directory"]) / "verification-failure.json"
        saved[label] = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
    required = (
        code != 0
        and report["result"] == "failed"
        and report["failure_type"] == expected_type
        and report["active"] == nested_report["active"]
        and report["failure_site"] == nested_report["failure_site"]
        and report["module"] == nested.__file__
        and state_exists
        and report["checks"][0]["case"] == "earlier_outer_uuid"
        and report["active"]["directory"] == str(observations["nested_directory"])
        and report["package_hashes"]["execution_repair_verification.py"]
        == hashlib.sha256(Path(nested.__file__).read_bytes()).hexdigest()
    )
    required &= report["active"]["variant"] == "capture_read_failure"
    required &= report["active"]["mode"] == "success"
    required &= report["active"]["phase"] == ("stderr" if case == "later" else "stdout")
    required &= report["active"]["case"] == (
        "capture_stderr_read_failure" if case == "later" else "capture_stdout_read_failure"
    )
    if case == "storage_failure":
        required &= all(
            not item["diagnostic_storage"]["available"] for item in [report, nested_report]
        ) and not any(saved.values())
    else:
        required &= (
            saved["parent"] == report
            and saved["nested"] == nested_report
            and parent_root != nested_root
        )
    if case in {"caught", "later", "cleanup_failure"}:
        required &= report["active"]["stage"] == "capture_assertions"
        required &= nested_report["checks"][1]["operation"]["invocation_id"] is not None
        required &= nested_report["pre_cleanup_snapshot"]["record"]["cleanup"] == "unverified"
        required &= any(
            x["stage"] == "before_authorized_cleanup" for x in report["cleanup_observations"]
        )
        if case == "cleanup_failure":
            required &= (
                report["cleanup_observations"][-1]["stage"] == "authorized_cleanup_failed"
            )
        if case == "later":
            required &= report["expected_condition"] == 'record["capture_complete"] is False'
    else:
        required &= (
            report["active"]["stage"] == "preparation" and not report["terminal_available"]
        )
        command = nested_report["checks"][-1]
        if case in {"preparation", "storage_failure", "timeout", "oversized"}:
            required &= OUT in command["stdout"] and ERR in command["stderr"]
        if case == "oversized":
            retained_stdout = command["stdout"]
            if command.get("stdout_evidence"):
                retained_stdout = Path(command["stdout_evidence"]["path"]).read_text(
                    encoding="utf-8"
                )
                required &= (
                    command["stdout_evidence"]["sha256"]
                    == hashlib.sha256(retained_stdout.encode()).hexdigest()
                )
            required &= len(retained_stdout) == 262144 and command["stdout_truncated"]
    if case == "launch":
        command = nested_report["checks"][-1]
        required &= (
            command["parse_status"] == "process_unavailable"
            and command["stdout"] == command["stderr"] == ""
            and not command["stdout_truncated"]
            and not command["stderr_truncated"]
        )
    result = {
        "required_behavior": bool(required),
        "child_main_exit": code,
        "scope": (
            "trusted Linux reporting composition; no actual Worker "
            "or historical failure reproduction"
        ),
        "parent_report": report,
        "durable": saved,
        "needed_state_existed_at_export": state_exists,
        "captured_stderr": stderr.getvalue(),
    }
    for root in {parent_root, nested_root}:
        assert root.parent.resolve() == Path(tempfile.gettempdir()).resolve()
        assert root.name.startswith("mobiraeon-execution-check-")
        shutil.rmtree(root)
    result["controlled_cleanup"] = "synthetic no-credential state removed only after export"
    return result


def interruption_control(tool, case, api=False):
    """Actual source-tool main; native Windows or labelled trusted branch simulation."""
    tool = Path(tool).resolve()
    spec = importlib.util.spec_from_file_location("trusted_interruption_tool", tool)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    passed = {"result": "passed", "checks": [{"sentinel": "completed_child_check"}]}
    bodies = {
        "positive": passed,
        "nonzero_pass": passed,
        "nonzero_failed": {"result": "failed"},
        "zero_failed": {"result": "failed"},
        "array": [],
        "string": "passed",
        "null": None,
        "missing": {},
        "unsupported": {"result": "other"},
        "checks_junk": {"result": "passed", "checks": "junk"},
        "checks_empty": {"result": "passed", "checks": []},
        "checks_bad_entry": {"result": "passed", "checks": [None]},
    }
    child_stdout = (
        "INVALID_JSON"
        if case in {"malformed", "timeout", "launch"}
        else json.dumps(bodies[case])
    )
    child_exit = 7 if case in {"nonzero_pass", "nonzero_failed"} else 0
    observed = []
    actual_run = subprocess.run

    def controller(command, **kwargs):
        if "--controller" not in command or Path(command[1]).resolve() != tool:
            return actual_run(command, **kwargs)
        observed.append({"command": command, "timeout": kwargs["timeout"]})
        if case == "timeout":
            raise subprocess.TimeoutExpired(
                command, 90, output=b"PARTIAL_CONTROLLER_OUT", stderr=b"PARTIAL_CONTROLLER_ERR"
            )
        if case == "launch":
            raise OSError("trusted controller unavailable")
        return subprocess.CompletedProcess(
            command, child_exit, child_stdout, "CONTROLLER_STDERR"
        )

    stdout = io.StringIO()
    with tempfile.TemporaryDirectory(prefix="mobiraeon-tool-control-") as temporary:
        output = Path(temporary) / "report.json"
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(module, "os", SimpleNamespace(name="nt")))
            if os.name != "nt":
                stack.enter_context(
                    patch.object(
                        subprocess,
                        "STARTUPINFO",
                        lambda: SimpleNamespace(dwFlags=0),
                        create=True,
                    )
                )
                stack.enter_context(
                    patch.object(subprocess, "STARTF_USESHOWWINDOW", 1, create=True)
                )
                stack.enter_context(
                    patch.object(subprocess, "CREATE_NEW_CONSOLE", 16, create=True)
                )
            stack.enter_context(patch.object(module.subprocess, "run", side_effect=controller))
            stack.enter_context(
                patch.object(
                    sys,
                    "argv",
                    [
                        str(tool),
                        "--target-python",
                        sys.executable,
                        "--output",
                        str(output),
                        *(["--api"] if api else []),
                    ],
                )
            )
            stack.enter_context(contextlib.redirect_stdout(stdout))
            try:
                code = module.main()
                report = json.loads(stdout.getvalue())
            except Exception as error:
                return {
                    "required_behavior": False,
                    "scope": "trusted controller observation",
                    "unstructured_error_type": type(error).__name__,
                    "observed_commands": observed,
                }
        saved = json.loads(output.read_text(encoding="utf-8"))
    required = (
        report == saved
        and len(observed) == 1
        and observed[0]["timeout"] == 90
        and (
            code == 0 and report["result"] == "passed"
            if case == "positive"
            else code != 0 and report["result"] == "failed"
        )
    )
    if case == "positive":
        required &= report["checks"] == passed["checks"]
    if case == "nonzero_pass" and required:
        required &= (
            report["controller"]["exit_code"] == 7
            and report["controller"]["child_report"] == passed
        )
        required &= report["controller"]["stderr"] == "CONTROLLER_STDERR"
    if case == "timeout" and required:
        required &= (
            report["controller"]["timed_out"]
            and report["controller"]["stdout"] == "PARTIAL_CONTROLLER_OUT"
        )
    if case == "launch" and required:
        required &= report["controller"]["parse_status"] == "process_unavailable"
        required &= report["controller"]["stdout"] == report["controller"]["stderr"] == ""
    if case in {"nonzero_failed", "zero_failed"} and required:
        required &= report["controller"]["exit_code"] == child_exit
        required &= report["controller"]["child_report"]["result"] == "failed"
    return {
        "required_behavior": bool(required),
        "wrapper_exit": code,
        "report": report,
        "api": api,
        "observed_commands": observed,
        "tool": str(tool),
        "tool_sha256": hashlib.sha256(tool.read_bytes()).hexdigest(),
        "scope": "native Windows controller branch observation"
        if os.name == "nt"
        else "trusted Windows-branch simulation on POSIX; no native qualification",
    }


BOOTSTRAP_CHILD = """import os,sys
from pathlib import Path
from mobiraeon.forge_verification import Installation, definition
from mobiraeon.forge import ForgeService
app=Installation(Path(sys.argv[1]),definition(sys.argv[2]),Path(sys.argv[3]).read_text())
assert app.link().outcome.value=='success'
if sys.argv[4]=='setup':
 app.close();raise SystemExit(0)
def fault(phase):
 if phase==sys.argv[4]:os._exit(86)
app.service=ForgeService(app.store,app.private,fault=fault)
app.sync('original-request')
os._exit(87)
"""

CRASH_CHILD = """import os,sys,json
from mobiraeon.access import credential_proof
from mobiraeon.configuration import resolve_configuration
from mobiraeon.forge import ForgeService
from mobiraeon.forge_verification import TARGET
from mobiraeon.persistence import Store
from mobiraeon.private_state import PrivateState
c=resolve_configuration(options={'config':sys.argv[1]});p=PrivateState(c.private_dir,c.database_path)
s=Store(c.database_path);proof=credential_proof(p.read_credential(c.credential_file))
def fault(phase):
 if phase=='prepared_committed':os._exit(86)
ForgeService(s,p,fault=fault).invoke('forge.sync',TARGET,json.loads(sys.argv[2]),proof=proof)
os._exit(87)
"""


def forge_recovery_control(case="recovery", *, original_python=None):
    """Disk SQLite and real child death; optional verified old runtime creates upgrade state."""
    original_python = str(original_python or sys.executable)
    commands = []
    with (
        tempfile.TemporaryDirectory(prefix="mobiraeon-forge-f7-") as temporary,
        Loopback() as server,
    ):
        directory = Path(temporary)
        harden(directory)
        secret_source = directory / "bootstrap-source"
        durable_new(secret_source, server.token.encode())
        phase = "armed_committed" if case == "armed" else "prepared_committed"
        setup_only = case in {"approval", "same_refused", "same_conflict"}
        argv = [
            original_python,
            "-c",
            BOOTSTRAP_CHILD,
            str(directory),
            server.origin,
            str(secret_source),
            "setup" if setup_only else phase,
        ]
        child = subprocess.run(argv, cwd=directory, capture_output=True, text=True, timeout=30)
        commands.append(
            dict(
                command=argv,
                cwd=str(directory),
                exit_code=child.returncode,
                stdout=child.stdout,
                stderr=child.stderr,
            )
        )
        assert child.returncode == (0 if setup_only else 86)
        config = resolve_configuration(options={"config": str(directory / "settings.toml")})
        app = Installation.__new__(Installation)
        app.directory, app.config = directory, directory / "settings.toml"
        app.private = PrivateState(config.private_dir, config.database_path)
        app.store = Store(config.database_path)
        app.proof = credential_proof(app.private.read_credential(config.credential_file))
        app.service = ForgeService(app.store, app.private)
        with app.store.engine.connect() as tx:
            app.revision = tx.exec_driver_sql("SELECT revision FROM forge_connections").scalar()

        def rows(sql):
            with app.store.engine.connect() as tx:
                return [dict(x) for x in tx.exec_driver_sql(sql).mappings()]

        def remove(action):
            with app.store.transaction() as tx:
                grants = json.loads(
                    execute(tx, "SELECT grants FROM access_credentials").scalar()
                )
                execute(
                    tx,
                    "UPDATE access_credentials SET grants=:g",
                    {"g": json.dumps([g for g in grants if g["action"] != action])},
                )

        try:
            if case == "approval":
                assert app.sync("first-publication").outcome == Outcome.SUCCESS
                server.comments[0]["body"] = "human edit"
                assert app.sync("detect-edit").outcome != Outcome.SUCCESS
                status = app.status().data
                conflict = status.records[0]["conflict"]
                assert (
                    app.call(
                        "forge.resolve",
                        operation_id="approve-refresh",
                        expected_version=status.version,
                        task_id="task-1",
                        conflict_id=conflict,
                        action="refresh",
                        rationale="trusted control approval",
                    ).outcome
                    == Outcome.SUCCESS
                )
                inputs = dict(
                    operation_id="original-request",
                    expected_version=app.status().data.version,
                    task_id="task-1",
                    connection_revision=app.revision,
                )
                argv = [original_python, "-c", CRASH_CHILD, str(app.config), json.dumps(inputs)]
                child = subprocess.run(
                    argv, cwd=directory, capture_output=True, text=True, timeout=30
                )
                commands.append(
                    dict(
                        command=argv,
                        cwd=str(directory),
                        exit_code=child.returncode,
                        stdout=child.stdout,
                        stderr=child.stderr,
                    )
                )
                assert child.returncode == 86
            if case in {"same_refused", "same_conflict"}:
                reason = Reason.REFUSED if case == "same_refused" else Reason.CONFLICT

                def refuse(phase):
                    if phase == "prepared_committed":
                        raise SafeError(reason)

                app.service = ForgeService(app.store, app.private, fault=refuse)
                result = app.sync("original-request")
                receipts = rows("SELECT * FROM forge_receipts WHERE id='original-request'")
                receipt = json.loads(receipts[0]["result"])
                expected = Outcome.REFUSED if case == "same_refused" else Outcome.FAILURE
                return {
                    "required_behavior": result.outcome == expected
                    and receipt["reason"] == reason.value
                    and receipt["data"]["version"] == 2
                    and receipt["data"]["state"] == "not_attempted"
                    and len(receipts) == 1
                    and not server.writes,
                    "result": diagnostics.json_observation(asdict(result)),
                    "receipt": receipt,
                    "commands": commands,
                    "scope": "trusted same-request pre-arm failure",
                }

            initial = rows(
                "SELECT i.id,i.cycle,i.record,s.state,s.generation FROM forge_intents i "
                "JOIN forge_intent_state s ON s.id=i.id "
                "WHERE s.state IN ('prepared','armed')"
            )[0]
            immutable_record = initial["record"]
            original_cycle = rows(
                "SELECT * FROM forge_cycles WHERE request='original-request'"
            )[0]
            original_inputs = dict(
                operation_id="original-request",
                expected_version=original_cycle["version"] - 1,
                task_id="task-1",
                connection_revision=app.revision,
            )
            assert not rows("SELECT * FROM forge_receipts WHERE id='original-request'")
            routes_before_replay = len(server.routes)
            before = app.call("forge.sync", **original_inputs)
            assert (
                before.outcome == Outcome.UNCERTAIN
                and len(server.routes) == routes_before_replay
            )
            original_bytes_before = None
            if case in {"existing_receipt", "incompatible_receipt"}:
                with app.store.transaction() as tx:
                    app.service._complete(
                        tx,
                        "original-request",
                        "not_attempted",
                        original_cycle["link"],
                        original_cycle["version"] if case == "existing_receipt" else 999,
                        outcome=Outcome.UNAVAILABLE,
                        reason=Reason.UNAVAILABLE,
                    )
                original_bytes_before = rows(
                    "SELECT result FROM forge_receipts WHERE id='original-request'"
                )[0]["result"]
            recovery_inputs = dict(
                operation_id="recovery-request",
                expected_version=original_cycle["version"],
                task_id="task-1",
                connection_revision=app.revision,
            )
            task_version = rows("SELECT version FROM coordination_tasks")[0]["version"]
            consumptions = rows("SELECT * FROM forge_consumptions")
            writes_before = len(server.writes)
            route_start = len(server.routes)
            if case in {"recover_without_project", "recover_without_task"}:
                remove("forge.sync" if case.endswith("project") else "coordination.status")
                result = app.call("forge.sync", **recovery_inputs)
                return {
                    "required_behavior": result.outcome == Outcome.REFUSED
                    and len(server.routes) == route_start
                    and not rows(
                        "SELECT * FROM forge_receipts "
                        "WHERE id IN ('original-request','recovery-request')"
                    )
                    and rows(
                        "SELECT state FROM forge_intent_state WHERE id='" + initial["id"] + "'"
                    )[0]["state"]
                    == "prepared",
                    "result": diagnostics.json_observation(asdict(result)),
                    "commands": commands,
                    "routes_before_recovery": route_start,
                    "recovery_routes": server.routes[route_start:],
                    "scope": "trusted missing authority; no protected business response",
                }
            triggered = []

            def fault(phase):
                if phase == "admission_committed" and (
                    case.startswith("error") or case == "revoke_admission"
                ):
                    if not triggered:
                        triggered.append(phase)
                        if case == "revoke_admission":
                            remove("forge.sync")
                        raise SafeError(
                            Reason.REFUSED
                            if case in {"error_refused", "revoke_admission"}
                            else Reason.CONFLICT
                            if case == "error_conflict"
                            else Reason.UNAVAILABLE
                        )
                if phase == "preflight_observed" and case == "revoke_preflight":
                    triggered.append(len(server.routes))
                    remove("coordination.status")
                    raise SafeError(Reason.REFUSED)
                if phase == "not_attempted_committed" and case == "lost_ack":
                    triggered.append(phase)
                    raise RuntimeError("trusted committed acknowledgement lost")

            app.service = ForgeService(app.store, app.private, fault=fault)
            actual_complete, actual_history = app.service._complete, app.service._history
            actual_error = app.service._record_error
            recording_calls, injected_failures, replay_observations = [], [], []

            def record_error(*args, **kwargs):
                recording_calls.append("fresh_trusted_error_recording")
                return actual_error(*args, **kwargs)

            def complete(tx, request, *args, **kwargs):
                if ("atomic_original" in case and request == "original-request") or (
                    "atomic_recovery" in case and request == "recovery-request"
                ):
                    injected_failures.append(request)
                    raise SafeError(Reason.UNAVAILABLE)
                return actual_complete(tx, request, *args, **kwargs)

            def history(*args, **kwargs):
                if "atomic_history" in case and args[5] == "not_attempted":
                    injected_failures.append("known_unarmed_closure_history")
                    raise SafeError(Reason.UNAVAILABLE)
                return actual_history(*args, **kwargs)

            with (
                patch.object(app.service, "_complete", side_effect=complete),
                patch.object(app.service, "_history", side_effect=history),
                patch.object(app.service, "_record_error", side_effect=record_error),
            ):
                recovered = app.call("forge.sync", **recovery_inputs)
            recovery_routes = list(server.routes[route_start:])
            receipts = rows(
                "SELECT * FROM forge_receipts "
                "WHERE id IN ('original-request','recovery-request') ORDER BY id"
            )
            closed = rows(
                "SELECT state,generation FROM forge_intent_state WHERE id='"
                + initial["id"]
                + "'"
            )[0]
            closure = rows(
                "SELECT invocation,actor,record FROM forge_history WHERE kind='not_attempted'"
            )
            actual = {r["id"]: json.loads(r["result"]) for r in receipts}
            unchanged = (
                rows("SELECT record FROM forge_intents WHERE id='" + initial["id"] + "'")[0][
                    "record"
                ]
                == immutable_record
            )
            required = (
                len(server.writes) == writes_before
                and unchanged
                and rows("SELECT version FROM coordination_tasks")[0]["version"] == task_version
                and rows("SELECT * FROM forge_consumptions") == consumptions
            )
            if case == "armed":
                required &= (
                    recovered.outcome == Outcome.UNCERTAIN
                    and closed["state"] in {"armed", "uncertain"}
                    and not receipts
                    and not closure
                )
            elif "atomic" in case or case == "incompatible_receipt":
                required &= (
                    closed["state"] == "prepared"
                    and not closure
                    and "recovery-request" not in actual
                )
                required &= len(receipts) == (1 if original_bytes_before else 0)
                required &= (
                    rows("SELECT version FROM forge_links")[0]["version"]
                    == original_cycle["version"] + 1
                )
                required &= closed["generation"] != original_cycle["id"]
                if "atomic" in case:
                    required &= len(injected_failures) >= (1 if case.startswith("error") else 2)
            else:
                required &= (
                    closed["state"] == "not_attempted"
                    and set(actual) == {"original-request", "recovery-request"}
                    and len(closure) == 1
                )
                if set(actual) == {"original-request", "recovery-request"}:
                    orig, rec = actual["original-request"], actual["recovery-request"]
                    required &= (
                        orig["outcome"] == Outcome.UNAVAILABLE
                        and orig["reason"] == Reason.UNAVAILABLE
                        and orig["data"]["state"] == "not_attempted"
                        and orig["data"]["version"] == original_cycle["version"]
                    )
                    required &= rec["data"]["version"] == original_cycle["version"] + 1
                    if case in {"error_refused", "revoke_admission", "revoke_preflight"}:
                        required &= (
                            rec["outcome"] == Outcome.REFUSED
                            and rec["reason"] == Reason.REFUSED
                            and recovered.outcome == Outcome.REFUSED
                            and not (recovered.data and recovered.data.records)
                        )
                    elif case == "error_conflict":
                        required &= (
                            rec["outcome"] == Outcome.FAILURE
                            and rec["reason"] == Reason.CONFLICT
                        )
                    else:
                        required &= (
                            rec["outcome"] == Outcome.UNAVAILABLE
                            and rec["reason"] == Reason.UNAVAILABLE
                        )
                    h = json.loads(closure[0]["record"])
                    required &= (
                        h["original_request"] == "original-request"
                        and h["original_cycle"] == original_cycle["id"]
                        and h["recovery_request"] == "recovery-request"
                        and closure[0]["invocation"] == str(recovered.invocation_id)
                    )
                if case.startswith("error") or case == "revoke_admission":
                    required &= len(server.routes) == route_start
                if case == "revoke_preflight":
                    required &= len(server.routes) == triggered[-1]
                if case not in {"revoke_admission", "revoke_preflight"} and set(actual) == {
                    "original-request",
                    "recovery-request",
                }:
                    old_receipts = list(receipts)
                    for _ in range(2):
                        prior_routes = len(server.routes)
                        version = rows("SELECT version FROM forge_links")[0]["version"]
                        cycles_before = rows(
                            "SELECT id,request,version FROM forge_cycles ORDER BY id"
                        )
                        required &= (
                            app.call("forge.sync", **original_inputs).outcome
                            == Outcome.UNAVAILABLE
                        )
                        required &= (
                            app.call("forge.sync", **recovery_inputs).outcome
                            != Outcome.UNCERTAIN
                        )
                        required &= (
                            len(server.routes) == prior_routes
                            and rows("SELECT version FROM forge_links")[0]["version"] == version
                            and rows("SELECT id,request,version FROM forge_cycles ORDER BY id")
                            == cycles_before
                        )
                        replay_observations.append(
                            {
                                "routes_before": prior_routes,
                                "routes_after": len(server.routes),
                                "link_version": version,
                                "cycles_unchanged": rows(
                                    "SELECT id,request,version FROM forge_cycles ORDER BY id"
                                )
                                == cycles_before,
                            }
                        )
                    if case in {"replay_without_project", "replay_without_task"}:
                        remove(
                            "forge.sync" if case.endswith("project") else "coordination.status"
                        )
                        prior_routes = len(server.routes)
                        result = app.call("forge.sync", **original_inputs)
                        required &= (
                            result.outcome == Outcome.REFUSED
                            and len(server.routes) == prior_routes
                        )
                    elif case == "fingerprint":
                        prior_routes = len(server.routes)
                        result = app.call(
                            "forge.sync", **(original_inputs | {"expected_version": 999})
                        )
                        required &= (
                            result.outcome == Outcome.FAILURE
                            and len(server.routes) == prior_routes
                        )
                    elif case == "approval":
                        required &= (
                            bool(consumptions)
                            and app.sync("cannot-reuse-approval").outcome != Outcome.SUCCESS
                            and len(server.writes) == writes_before
                        )
                    else:
                        required &= (
                            app.sync("later-fresh-publication").outcome == Outcome.SUCCESS
                            and len(server.writes) == writes_before + 1
                        )
                        prior_routes = len(server.routes)
                        cycles_before = rows(
                            "SELECT id,request,version FROM forge_cycles ORDER BY id"
                        )
                        required &= (
                            app.call("forge.sync", **original_inputs).outcome
                            == Outcome.UNAVAILABLE
                            and len(server.routes) == prior_routes
                            and rows("SELECT id,request,version FROM forge_cycles ORDER BY id")
                            == cycles_before
                        )
                    required &= (
                        rows(
                            "SELECT * FROM forge_receipts "
                            "WHERE id IN ('original-request','recovery-request') ORDER BY id"
                        )
                        == old_receipts
                    )
            if original_bytes_before:
                required &= (
                    actual["original-request"]
                    and rows("SELECT result FROM forge_receipts WHERE id='original-request'")[
                        0
                    ]["result"]
                    == original_bytes_before
                )
            if case == "lost_ack":
                required &= (
                    triggered == ["not_attempted_committed"] and len(recording_calls) == 1
                )
            return {
                "required_behavior": bool(required),
                "commands": commands,
                "initial_intent_state": initial["state"],
                "original_receipt_initially_absent": True,
                "original_replay_before_recovery": diagnostics.json_observation(asdict(before)),
                "routes_before_recovery": route_start,
                "recovery_routes": recovery_routes,
                "replay_observations": replay_observations,
                "fault_observations": triggered,
                "injected_recording_failures": injected_failures,
                "fresh_error_recording_calls": recording_calls,
                "result": diagnostics.json_observation(asdict(recovered)),
                "receipts": actual,
                "original_cycle_version": original_cycle["version"],
                "intent_state": closed,
                "closure_history": closure,
                "intent_immutable": unchanged,
                "task_version_unchanged": True,
                "writes_before_recovery": writes_before,
                "writes_after_control": len(server.writes),
                "original_python": original_python,
                "scope": (
                    "synthetic protected disk, real process death; "
                    "no actual Gitea/Worker qualification"
                ),
            }
        finally:
            app.close()
