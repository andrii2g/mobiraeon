"""Trusted disposable bridge fixtures, runnable with runtime dependencies only.

The loopback fixture uses the production HTTPX2 transport, service and CLI. It is
not a provider qualification or a production identity/qualification bypass.
"""

import argparse
import json
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from mobiraeon.access import credential_proof
from mobiraeon.catalog import RegistryService
from mobiraeon.contracts import FORGE_ACTIONS, Operation, Outcome
from mobiraeon.coordination import Coordinator
from mobiraeon.forge import ForgeService, sha
from mobiraeon.forge_credentials import import_token
from mobiraeon.forge_schema import DEFAULT_LIMITS
from mobiraeon.persistence import Store
from mobiraeon.private_state import PrivateState, durable_new, harden
from mobiraeon.registry_schema import ACCESS_ACTIONS
from mobiraeon.scenario import FixtureConfiguration, fixture_ref

TARGET = {"kind": "entity", "entity_kind": "project", "identity": "project-1"}
TASK = {"kind": "entity", "entity_kind": "task", "identity": "task-1"}


def definition(origin):
    return {
        "provider": "gitea",
        "origin": origin,
        "allow_loopback_http": True,
        "repository": {"id": "1", "owner": "fixture", "name": "bridge"},
        "account": {"id": "2", "name": "bridge-bot"},
        "credential": {"name": "forge-v1", "revision": "v1"},
        "tls_ca_file": None,
        "limits": dict(DEFAULT_LIMITS),
    }


class Loopback:
    def __init__(self):
        self.token = secrets.token_urlsafe(32)
        self.comments = []
        self.writes = []
        self.routes = []
        self.mode = None
        self.next_id = 1
        self.issue_state = "open"
        self.issue_extra = {}
        self.list_count = None
        self.version = "28.2.0"
        self.started = threading.Event()
        self.release = threading.Event()
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                self.handle_request("GET")

            def do_POST(self):
                self.handle_request("POST")

            def do_PATCH(self):
                self.handle_request("PATCH")

            def handle_request(self, method):
                try:
                    self.dispatch(method)
                except BrokenPipeError, ConnectionResetError, OSError:
                    pass

            def dispatch(self, method):
                path = self.path.removeprefix("/api/v1")
                fixture.routes.append((method, path))
                if self.headers.get("Authorization") != "token " + fixture.token:
                    return self.reply(401, {"message": "denied"})
                if method == "GET":
                    if fixture.mode == "cycle":
                        time.sleep(0.55)
                    if path == "/version":
                        if fixture.mode == "redirect":
                            return self.reply(302, {}, {"Location": "http://example.invalid/"})
                        if fixture.mode == "compressed":
                            return self.reply(200, {}, {"Content-Encoding": "gzip"})
                        if fixture.mode in {"slow", "stall"}:
                            self.send_response(200)
                            self.end_headers()
                            for _ in range(20):
                                time.sleep(0.06 if fixture.mode == "slow" else 0.2)
                                self.wfile.write(b" ")
                                self.wfile.flush()
                            return
                        if fixture.mode == "oversize":
                            return self.reply(200, {"padding": "x" * 20000})
                        return self.reply(200, {"version": fixture.version})
                    if path == "/user":
                        return self.reply(200, {"id": 2, "login": "bridge-bot"})
                    if path == "/repos/fixture/bridge":
                        return self.reply(
                            200, {"id": 1, "name": "bridge", "owner": {"login": "fixture"}}
                        )
                    if path == "/repos/fixture/bridge/issues/1":
                        return self.reply(
                            200,
                            {
                                "id": 3,
                                "number": 1,
                                "state": fixture.issue_state,
                                "title": "Human title",
                                "body": "Human body",
                                "labels": ["human"],
                                "html_url": fixture.origin + "/fixture/bridge/issues/1",
                            }
                            | fixture.issue_extra,
                        )
                    if path == "/repos/fixture/bridge/issues/1/comments":
                        return self.reply(
                            200,
                            fixture.comments,
                            {
                                "X-Total-Count": str(
                                    fixture.list_count
                                    if fixture.list_count is not None
                                    else len(fixture.comments)
                                )
                            },
                        )
                    if path.startswith("/repos/fixture/bridge/issues/comments/"):
                        comment = next(
                            (
                                c
                                for c in fixture.comments
                                if str(c["id"]) == path.rsplit("/", 1)[1]
                            ),
                            None,
                        )
                        return self.reply(200 if comment else 404, comment or {})
                else:
                    body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                    assert set(body) == {"body"}
                    fixture.started.set()
                    if fixture.mode in {"block", "delayed"}:
                        fixture.release.wait(5)
                    if method == "POST":
                        comment = {
                            "id": fixture.next_id,
                            "body": body["body"],
                            "user": {"id": 2},
                            "issue_url": fixture.origin + "/fixture/bridge/issues/1",
                            "pull_request_url": None,
                        }
                        fixture.next_id += 1
                        fixture.comments.append(comment)
                    else:
                        comment = next(
                            c
                            for c in fixture.comments
                            if str(c["id"]) == path.rsplit("/", 1)[1]
                        )
                        comment["body"] = body["body"]
                    fixture.writes.append((method, comment["id"]))
                    if fixture.mode == "write-oversize-error":
                        return self.reply(503, {"padding": "x" * 20000})
                    if fixture.mode == "write-redirect":
                        return self.reply(302, {}, {"Location": "http://example.invalid/"})
                    if fixture.mode == "write-malformed":
                        self.send_response(201)
                        self.send_header("Content-Length", "1")
                        self.end_headers()
                        self.wfile.write(b"{")
                        return
                    if fixture.mode == "lost":
                        self.connection.shutdown(socket.SHUT_RDWR)
                        self.connection.close()
                        return
                    return self.reply(201 if method == "POST" else 200, comment)
                return self.reply(404, {})

            def reply(self, status, data, headers=None):
                raw = json.dumps(data).encode()
                self.send_response(status)
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Content-Type", "application/json")
                for key, value in (headers or {}).items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(raw)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.origin = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.release.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)


class Installation:
    def __init__(self, directory, config, token):
        self.directory = Path(directory)
        self.private = PrivateState(
            self.directory / "private", self.directory / "private/state.db"
        )
        self.private.provision()
        self.store = Store(self.private.database)
        self.store.initialize()
        harden(self.private.database)
        self.registry = RegistryService(self.store, self.private)
        grants = [
            {"action": a.value, "scope": "*"}
            for a in sorted(
                ACCESS_ACTIONS
                | FORGE_ACTIONS
                | {
                    Operation.REGISTRY_READ,
                    Operation.SUPPLY,
                    Operation.STATUS,
                    Operation.ALLOCATE,
                    Operation.DISPATCH,
                    Operation.OBSERVE,
                }
            )
        ]
        result = self.registry.invoke(
            Operation.SETUP,
            {"kind": "access", "entity_kind": "installation", "identity": "owner"},
            {
                "destination": "owner.token",
                "lifetime_seconds": 3600,
                "allow_self_review": True,
                "grants": grants,
            },
            proof=self.registry.access.owner_proof(),
        )
        assert result.outcome == Outcome.SUCCESS, asdict(result)
        self.proof = credential_proof(
            self.private.read_credential(self.private.credential_path("owner.token"))
        )
        source = self.directory / "source-token"
        durable_new(source, token.encode() + b"\n")
        import_token(self.store, self.private, source, "forge-v1")
        self.coordinator = Coordinator(
            self.store, self.private, configuration_source=FixtureConfiguration()
        )
        text = "Synthetic forge verification input."
        work = dict(
            project="project-1",
            request="request-1",
            initiative="initiative-1",
            objective="Demonstrate forge bridge",
            scope="One fixture",
            exclusions="No real Agents",
            project_context="Isolated fixture",
            request_outcome="Bridge",
            initiative_outcome="Bridge",
            deliverables=["result"],
            role=fixture_ref("role"),
            inputs=[dict(identity="brief", revision="v1", sha256=sha(text), content=text)],
            criteria={
                "criterion": dict(requirement="Retain exact evidence", evidence="result")
            },
        )
        supplied = self.coordinator.invoke(
            Operation.SUPPLY, TASK, {"operation_id": "supply", "work": work}, proof=self.proof
        )
        assert supplied.outcome == Outcome.SUCCESS, asdict(supplied)
        self.service = ForgeService(self.store, self.private)
        configured = self.call(
            "forge.connection.configure",
            operation_id="configure",
            expected_version=0,
            connection=config,
        )
        assert configured.outcome == Outcome.SUCCESS, asdict(configured)
        self.revision = configured.data.reference
        self.config = self.directory / "settings.toml"
        self.config.write_text(
            "[database]\npath="
            + json.dumps(str(self.private.database))
            + "\n[access]\nprivate_dir="
            + json.dumps(str(self.private.directory))
            + "\ncredential_file="
            + json.dumps(str(self.private.credential_path("owner.token")))
            + "\n"
        )

    def call(self, operation, **inputs):
        return self.service.invoke(operation, TARGET, inputs, proof=self.proof)

    def cli(self, operation, *, python=sys.executable, **inputs):
        request = self.directory / (secrets.token_hex(8) + ".json")
        request.write_text(json.dumps(dict(operation=operation, target=TARGET, inputs=inputs)))
        return subprocess.run(
            [
                str(python),
                "-m",
                "mobiraeon",
                "--config",
                str(self.config),
                "--request-file",
                str(request),
                "forge",
            ],
            capture_output=True,
            text=True,
            cwd=self.directory,
            timeout=15,
        )

    def link(self, operation_id="link"):
        return self.call(
            "forge.link",
            operation_id=operation_id,
            expected_version=0,
            task_id="task-1",
            connection_revision=self.revision,
            issue_number=1,
        )

    def status(self):
        return self.call("forge.status", task_id="task-1")

    def sync(self, operation_id):
        version = self.status().data.version
        return self.call(
            "forge.sync",
            operation_id=operation_id,
            expected_version=version,
            task_id="task-1",
            connection_revision=self.revision,
        )

    def progress(self):
        for action, inputs in (
            (
                Operation.ALLOCATE,
                dict(
                    operation_id="allocate",
                    expected_version=1,
                    assignment_id="a1",
                    attempt_id="attempt-1",
                    configuration={
                        k: fixture_ref(k) for k in ("agent", "profile", "role", "context")
                    },
                ),
            ),
            (
                Operation.DISPATCH,
                dict(operation_id="dispatch", expected_version=2, attempt_id="attempt-1"),
            ),
            (
                Operation.OBSERVE,
                dict(
                    operation_id="observe",
                    expected_version=3,
                    attempt_id="attempt-1",
                    observation="succeeded",
                    detail="Recorded fixture result",
                ),
            ),
        ):
            result = self.coordinator.invoke(action, TASK, inputs, proof=self.proof)
            assert result.outcome == Outcome.SUCCESS, asdict(result)

    def close(self):
        self.store.close()


@contextmanager
def fixture(configure=None):
    with (
        tempfile.TemporaryDirectory(prefix="mobiraeon-forge-") as temporary,
        Loopback() as server,
    ):
        directory = Path(temporary)
        harden(directory)
        config = definition(server.origin)
        if configure:
            configure(config)
        installation = Installation(directory, config, server.token)
        try:
            yield installation, server
        finally:
            installation.close()


def exercise():
    checks = []
    with fixture() as (app, server):
        assert app.link().outcome == Outcome.SUCCESS
        assert not server.writes
        checks.append("link_publishes_nothing")
        first = app.sync("sync-1")
        assert first.outcome == Outcome.SUCCESS and first.data.state == "published", asdict(
            first
        )
        assert server.writes == [("POST", 1)]
        assert app.sync("sync-2").data.state == "unchanged"
        checks.append("create_then_semantic_unchanged")
        app.progress()
        assert app.sync("sync-3").outcome == Outcome.SUCCESS
        assert server.writes == [("POST", 1), ("PATCH", 1)]
        checks.append("fixture_progress_updates_same_comment")
        result = app.cli(
            "forge.sync",
            operation_id="sync-4",
            expected_version=app.status().data.version,
            task_id="task-1",
            connection_revision=app.revision,
        )
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["data"]["state"] == "unchanged"
        checks.append("restarted_cli_no_duplicate")
        server.comments[0]["body"] += "human edit"
        held = app.sync("sync-5")
        assert held.outcome != Outcome.SUCCESS
        status = app.status()
        conflict = status.data.records[0]["conflict"]
        assert conflict
        approved = app.call(
            "forge.resolve",
            operation_id="approve",
            expected_version=status.data.version,
            task_id="task-1",
            conflict_id=conflict,
            action="refresh",
            rationale="Restore projection",
        )
        assert approved.data.state == "approval_recorded"
        assert app.sync("sync-6").outcome == Outcome.SUCCESS
        checks.append("observed_edit_remote_free_approval_refresh")
        server.comments.clear()
        assert app.sync("sync-7").outcome != Outcome.SUCCESS
        status = app.status()
        app.call(
            "forge.resolve",
            operation_id="replace",
            expected_version=status.data.version,
            task_id="task-1",
            conflict_id=status.data.records[0]["conflict"],
            action="replace",
            rationale="Replace confirmed deletion",
        )
        server.mode = "lost"
        lost = app.sync("sync-8")
        assert lost.outcome == Outcome.UNCERTAIN, asdict(lost)
        count = len(server.writes)
        server.mode = None
        assert app.sync("sync-9").outcome == Outcome.SUCCESS
        assert len(server.writes) == count
        checks.append("applied_create_lost_ack_read_only_reconciliation")
        assert app.sync("sync-10").data.state == "unchanged"
        checks.append("post_reconciliation_unchanged")
        raw = app.private.database.read_bytes()
        assert server.token.encode() not in raw
        checks.append("no_service_token_in_database")

    def short(config):
        config["limits"]["request_seconds"] = 0.15

    with fixture(short) as (app, server):
        app.link()
        app.sync("initial")
        app.progress()
        server.mode = "delayed"
        assert app.sync("delayed").outcome == Outcome.UNCERTAIN
        assert app.sync("old-body").outcome == Outcome.UNCERTAIN
        assert len(server.writes) == 1
        server.release.set()
        for _ in range(100):
            if len(server.writes) == 2:
                break
            time.sleep(0.01)
        server.mode = None
        assert app.sync("reconcile").outcome == Outcome.SUCCESS
        assert len(server.writes) == 2
        checks.append("delayed_patch_old_body_never_resends")
    with fixture() as (app, server):
        app.link()

        def fault(phase):
            if phase == "armed_committed":
                raise RuntimeError("trusted interrupted arm")

        app.service.fault = fault
        assert app.sync("arm-interrupted").outcome == Outcome.UNCERTAIN
        app.service.fault = lambda _: None
        assert app.sync("zero-matches").outcome == Outcome.UNCERTAIN
        assert not server.writes
        checks.append("armed_intent_zero_matches_retains_hold")
    return {
        "result": "passed",
        "checks": checks,
        "count": len(checks),
        "module": __file__,
        "transport": "production httpx2 over loopback TCP",
        "provider_qualified": False,
    }


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    try:
        report = exercise()
    except Exception as error:
        report = {"result": "failed", "failure_type": type(error).__name__}
    print(json.dumps(report))
    return int(report["result"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
