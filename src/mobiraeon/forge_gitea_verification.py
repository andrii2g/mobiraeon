"""Isolated actual Gitea qualification. No owner infrastructure or credentials.

Only fixture composition uses privileged routes/commands. The production adapter
still has its fixed allowlist. Generated password/token output remains in memory.
"""

import json
import os
import platform
import re
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import asdict
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx2

from mobiraeon.contracts import Outcome
from mobiraeon.forge_schema import DEFAULT_LIMITS
from mobiraeon.forge_verification import Installation, definition
from mobiraeon.private_state import harden

IMAGE = "docker.gitea.com/gitea:28.2.0-rootless"
SCOPES = "read:user,read:repository,write:issue"
# A genuine Docker host loopback publication. WSL redirects 127.0.0.1 through
# loopback0 on the qualified host; 127.0.0.2 uses Linux lo. No relay/host change.
PUBLISHED_LOOPBACK = "127.0.0.2"


def published_route(publication, proxy):
    return bool(
        publication["ownership_verified"]
        and publication["running"]
        and publication["ready_on_published_endpoint"]
        and {"HostIp": PUBLISHED_LOOPBACK, "HostPort": str(publication["port"])}
        in publication["inspected_bindings"]
        and proxy.upstream == publication["origin"]
        and proxy.routes
        and all(r["upstream"] == publication["origin"] for r in proxy.routes)
    )


def await_fixture_api(client, published, private, observations):
    """Keep the existing finite startup budget before choosing private fallback."""
    deadline = time.monotonic() + 25
    response = fallback = None
    while (remaining := deadline - time.monotonic()) > 0:
        item = {"utc": datetime.now(UTC).isoformat(), "origin": published}
        try:
            response = client.get(published + "/api/v1/version", timeout=min(1, remaining))
            item["status_code"] = response.status_code
            observations.append(item)
            if response.status_code == 200:
                assert response.json() == {"version": "28.2.0"}
                return response, published
        except httpx2.HTTPError:
            item["result"] = "http_unavailable"
            observations.append(item)
            remaining = deadline - time.monotonic()
            if fallback is None and remaining > 0:
                try:
                    candidate = client.get(
                        private + "/api/v1/version", timeout=min(1, remaining)
                    )
                    observations.append(
                        {
                            "utc": datetime.now(UTC).isoformat(),
                            "origin": private,
                            "status_code": candidate.status_code,
                        }
                    )
                    if candidate.status_code == 200:
                        assert candidate.json() == {"version": "28.2.0"}
                        fallback = candidate
                except httpx2.HTTPError:
                    pass
        time.sleep(min(0.2, max(0, deadline - time.monotonic())))
    return (fallback, private) if fallback is not None else (response, published)


class LostAckProxy:
    def __init__(self, upstream):
        self.upstream = upstream
        self.lose = False
        self.routes = []
        self.lost_applied = 0
        proxy = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                self.forward()

            def do_POST(self):
                self.forward()

            def do_PATCH(self):
                self.forward()

            def do_PUT(self):
                self.forward()

            def do_DELETE(self):
                self.forward()

            def forward(self):
                try:
                    size = int(self.headers.get("Content-Length", 0))
                    assert size <= 131072
                    body = self.rfile.read(size) if size else None
                    proxy.routes.append(
                        {"method": self.command, "path": self.path, "upstream": proxy.upstream}
                    )
                    with httpx2.Client(
                        trust_env=False, follow_redirects=False, timeout=20
                    ) as client:
                        response = client.request(
                            self.command,
                            proxy.upstream + self.path,
                            content=body,
                            headers={
                                key: value
                                for key, value in self.headers.items()
                                if key.lower()
                                in {"authorization", "accept-encoding", "content-type", "host"}
                            },
                        )
                    if (
                        proxy.lose
                        and self.command in {"POST", "PATCH"}
                        and response.status_code in {200, 201}
                    ):
                        proxy.lose = False
                        proxy.lost_applied += 1
                        self.connection.shutdown(socket.SHUT_RDWR)
                        self.connection.close()
                        return
                    self.send_response(response.status_code)
                    for key in ("Content-Type", "X-Total-Count"):
                        if key in response.headers:
                            self.send_header(key, response.headers[key])
                    self.send_header("Content-Length", str(len(response.content)))
                    self.end_headers()
                    self.wfile.write(response.content)
                except OSError, httpx2.HTTPError:
                    self.close_connection = True

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.origin = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)


def exercise(docker="docker"):
    if platform.system() != "Linux":
        raise RuntimeError("real provider mode requires Linux Docker")
    name = "mobiraeon-i5-" + secrets.token_hex(8)
    report = {
        "result": "failed",
        "image": IMAGE,
        "namespace": name,
        "database": "disposable SQLite; not owner's PostgreSQL deployment",
        "host": platform.platform(),
        "scopes": SCOPES.split(","),
        "limits": dict(DEFAULT_LIMITS),
        "checks": [],
        "module": __file__,
        "python": sys.executable,
        "cleanup": "not_started",
        "client_context": {
            "uid": os.getuid(),
            "gid": os.getgid(),
            "network_namespace": os.readlink("/proc/self/ns/net"),
        },
    }
    container = None
    proxy = None
    network_created = False

    def command(*args, timeout=60):
        result = subprocess.run(
            [str(docker), *args], capture_output=True, text=True, timeout=timeout
        )
        if result.returncode:
            raise RuntimeError("isolated docker command failed")
        return result.stdout

    try:
        report["docker_version"] = json.loads(command("version", "--format", "json"))
        report["docker_engine_id"] = json.loads(command("info", "--format", "{{json .ID}}"))
        report["docker_context"] = command("context", "show").strip()
        endpoint = json.loads(
            command(
                "context",
                "inspect",
                report["docker_context"],
                "--format",
                "{{json .Endpoints.docker.Host}}",
            )
        )
        report["docker_endpoint"] = endpoint if "@" not in endpoint else "userinfo_redacted"
        image = json.loads(command("image", "inspect", IMAGE))[0]
        report["image_id"] = image["Id"]
        report["image_digests"] = image["RepoDigests"]
        report["actual_binary_version"] = command(
            "run", "--rm", "--entrypoint", "/usr/local/bin/gitea", IMAGE, "--version"
        ).strip()
        with socket.socket() as reserve:
            reserve.bind((PUBLISHED_LOOPBACK, 0))
            port = reserve.getsockname()[1]
        upstream = f"http://{PUBLISHED_LOOPBACK}:{port}"
        proxy = LostAckProxy(upstream)
        proxy.thread.start()
        command("network", "create", "--label", "mobiraeon.verification=" + name, name)
        network_created = True
        container = command(
            "run",
            "-d",
            "--name",
            name,
            "--label",
            "mobiraeon.verification=" + name,
            "--network",
            name,
            "-p",
            f"{PUBLISHED_LOOPBACK}:{port}:3000",
            "--tmpfs",
            "/var/lib/gitea:uid=1000,gid=1000,mode=0700",
            "--tmpfs",
            "/etc/gitea:uid=1000,gid=1000,mode=0700",
            "-e",
            "GITEA__database__DB_TYPE=sqlite3",
            "-e",
            "GITEA__security__INSTALL_LOCK=true",
            "-e",
            "GITEA__server__DISABLE_SSH=true",
            "-e",
            "GITEA__server__ROOT_URL=" + proxy.origin + "/",
            "-e",
            "GITEA__service__DISABLE_REGISTRATION=true",
            IMAGE,
        ).strip()
        inspected = json.loads(command("inspect", container))[0]
        assert inspected["Config"]["Labels"].get("mobiraeon.verification") == name
        publication = report["publication"] = {
            "container_id": container,
            "namespace": name,
            "origin": upstream,
            "port": port,
            "container_port": "3000/tcp",
            "inspected_bindings": inspected["NetworkSettings"]["Ports"]["3000/tcp"],
            "ownership_verified": True,
            "running": inspected["State"]["Running"],
            "root_url": proxy.origin + "/",
            "proxy_origin": proxy.origin,
            "ready_on_published_endpoint": False,
            "readiness_observations": [],
        }
        with httpx2.Client(trust_env=False, follow_redirects=False, timeout=5) as client:
            address = inspected["NetworkSettings"]["Networks"][name]["IPAddress"]
            response, selected = await_fixture_api(
                client,
                upstream,
                "http://" + address + ":3000",
                publication["readiness_observations"],
            )
            if selected != upstream:
                upstream = proxy.upstream = selected
                report["published_loopback_limitation"] = (
                    "Host could not connect to Docker's loopback-published port within "
                    "the finite startup budget; fixture proxy uses the verified owned "
                    "container private address. Production origin remains the loopback proxy."
                )
            if response is None:
                inspected = json.loads(command("inspect", container))[0]
                report["startup_state"] = {
                    key: inspected["State"][key] for key in ("Status", "ExitCode")
                }
                # No accounts/tokens have been provisioned yet. Retain only known
                # startup diagnostic categories, never arbitrary service log text.
                logs = command("logs", container)
                report["startup_diagnostics"] = [
                    code
                    for code in (
                        "Permission denied",
                        "permission denied",
                        "no such file",
                        "connection refused",
                        "INSTALL_LOCK",
                        "database is locked",
                        "unable to open",
                        "no route to host",
                    )
                    if code in logs
                ]
                raise RuntimeError("isolated Gitea startup unavailable")
            assert response.status_code == 200 and response.json() == {"version": "28.2.0"}
            publication["ready_on_published_endpoint"] = upstream == publication["origin"]
            publication["observed_version"] = response.json()["version"]
            report["actual_api_version"] = response.json()["version"]
            report["stage"] = "api_available"

            def create_user(username, bot=False):
                args = [
                    "exec",
                    container,
                    "gitea",
                    "--config",
                    "/etc/gitea/app.ini",
                    "admin",
                    "user",
                    "create",
                    "--username",
                    username,
                    "--email",
                    username + "@example.invalid",
                    "--access-token",
                ]
                args += (
                    ["--user-type", "Bot", "--access-token-scopes", SCOPES]
                    if bot
                    else ["--admin", "--random-password", "--must-change-password=false"]
                )
                raw = command(*args)
                # Gitea prints the generated access token as the final token line.
                candidates = re.findall(
                    r"(?im)(?:access token[^:\n]*:|token[^:\n]*:)\s*([A-Za-z0-9_-]+)", raw
                )
                if not candidates:
                    candidates = re.findall(r"\b[0-9a-f]{40}\b", raw)
                assert len(candidates) == 1
                return candidates[0]

            admin = create_user("fixture-owner")
            bot = create_user("fixture-bot", bot=True)
            report["stage"] = "users_provisioned"

            def api(method, path, data=None, token=admin, expected=(200, 201, 204)):
                result = client.request(
                    method,
                    proxy.origin + "/api/v1" + path,
                    headers={"Authorization": "token " + token},
                    **({"json": data} if data is not None else {}),
                )
                report.setdefault("fixture_api_results", []).append(
                    {"method": method, "path": path, "status": result.status_code}
                )
                assert result.status_code in expected
                return result.json() if result.content else None

            account = api("GET", "/user", token=bot)
            repository = api(
                "POST", "/user/repos", {"name": "bridge", "private": True, "auto_init": False}
            )
            base = "/repos/fixture-owner/bridge"
            api("PUT", base + "/collaborators/fixture-bot", {"permission": "write"})
            issue = api(
                "POST", base + "/issues", {"title": "Human title", "body": "Human body"}
            )
            report["fixture_identity_observations"] = {
                "account": {k: account.get(k) for k in ("id", "login")},
                "repository": {k: repository.get(k) for k in ("id", "name")},
                "repository_owner_login": repository["owner"].get("login"),
                "issue": {
                    k: issue.get(k)
                    for k in ("id", "number", "html_url", "state", "pull_request")
                },
            }
            human = api("POST", base + "/issues/1/comments", {"body": "Human discussion"})
            # The production token's own native grants must refuse repository creation.
            api("POST", "/user/repos", {"name": "must-not-exist"}, token=bot, expected=(403,))
            report["checks"].append("native_token_scope_refusal")
            with tempfile.TemporaryDirectory(prefix="mobiraeon-real-forge-") as temporary:
                directory = Path(temporary)
                harden(directory)
                config = definition(proxy.origin)
                config["repository"] = {
                    "id": str(repository["id"]),
                    "owner": "fixture-owner",
                    "name": "bridge",
                }
                config["account"] = {"id": str(account["id"]), "name": "fixture-bot"}
                app = Installation(directory, config, bot)
                try:
                    report["stage"] = "link"
                    linked = app.link()
                    report["link_result"] = {
                        "outcome": linked.outcome,
                        "reason": linked.reason,
                        "data": asdict(linked.data) if linked.data else None,
                    }
                    assert linked.outcome == Outcome.SUCCESS
                    report["stage"] = "create"
                    created = app.sync("real-create")
                    report["create_result"] = {
                        "outcome": created.outcome,
                        "reason": created.reason,
                        "data": asdict(created.data) if created.data else None,
                    }
                    assert created.outcome == Outcome.SUCCESS
                    managed = app.status().data.records[0]["comment"]
                    app.progress()
                    assert app.sync("real-update").outcome == Outcome.SUCCESS
                    assert app.status().data.records[0]["comment"] == managed
                    result = app.cli(
                        "forge.sync",
                        operation_id="restart",
                        expected_version=app.status().data.version,
                        task_id="task-1",
                        connection_revision=app.revision,
                    )
                    assert result.returncode == 0
                    report["checks"] += ["stable_ids_create_update", "restart_unchanged"]
                    observed_issue = api("GET", base + "/issues/1")
                    assert all(
                        observed_issue[k] == issue[k]
                        for k in ("title", "body", "labels", "assignees", "state")
                    )
                    assert (
                        api("GET", base + "/issues/comments/" + str(human["id"]))["body"]
                        == "Human discussion"
                    )
                    report["checks"].append("human_fields_and_discussion_preserved")
                    # Human edit uses privileged fixture identity; production retains
                    # its fixed route authority.
                    api(
                        "PATCH",
                        base + "/issues/comments/" + managed,
                        {"body": "Observed human edit"},
                    )
                    assert app.sync("edit-held").outcome != Outcome.SUCCESS
                    status = app.status()
                    assert (
                        app.call(
                            "forge.resolve",
                            operation_id="refresh",
                            expected_version=status.data.version,
                            task_id="task-1",
                            conflict_id=status.data.records[0]["conflict"],
                            action="refresh",
                            rationale="Restore recorded facts",
                        ).outcome
                        == Outcome.SUCCESS
                    )
                    proxy.lose = True
                    assert app.sync("lost-update").outcome == Outcome.UNCERTAIN
                    assert app.sync("reconcile-update").outcome == Outcome.SUCCESS
                    assert proxy.lost_applied == 1
                    report["checks"] += [
                        "observed_edit_approval",
                        "actual_applied_patch_lost_ack_reconciliation",
                    ]
                    api("DELETE", base + "/issues/comments/" + managed)
                    assert app.sync("deletion-held").outcome != Outcome.SUCCESS
                    status = app.status()
                    assert (
                        app.call(
                            "forge.resolve",
                            operation_id="replace",
                            expected_version=status.data.version,
                            task_id="task-1",
                            conflict_id=status.data.records[0]["conflict"],
                            action="replace",
                            rationale="Replace established deletion",
                        ).outcome
                        == Outcome.SUCCESS
                    )
                    proxy.lose = True
                    assert app.sync("lost-create").outcome == Outcome.UNCERTAIN
                    assert app.sync("reconcile-create").outcome == Outcome.SUCCESS
                    assert proxy.lost_applied == 2
                    assert app.status().data.records[0]["comment"] != managed
                    report["checks"] += [
                        "established_deletion_approval",
                        "actual_applied_post_lost_ack_complete_lookup",
                    ]
                    assert any(
                        r["path"].endswith("/issues/1/comments") and r["method"] == "GET"
                        for r in proxy.routes
                    )
                    assert not any("page=" in r["path"] for r in proxy.routes)
                    report["checks"].append("bounded_unpaginated_lookup")
                    report["routes"] = proxy.routes
                    report["stable_ids"] = {
                        "repository": str(repository["id"]),
                        "account": str(account["id"]),
                        "issue": str(issue["id"]),
                    }
                finally:
                    app.close()
            report["api_checks_result"] = "passed"
            publication["proxy_upstream"] = proxy.upstream
            publication["verified_published_loopback_throughout_scenario"] = published_route(
                publication, proxy
            )
            if not publication["verified_published_loopback_throughout_scenario"]:
                report["result"] = "incomplete"
                report["incomplete_checks"] = ["docker_published_loopback_reachability"]
            else:
                report["result"] = "passed"
    except Exception as error:
        report["failure_type"] = type(error).__name__
        report["limitation"] = (
            "Requested real-provider qualification did not complete; no mock substitution."
        )
    finally:
        if proxy:
            report["routes"] = proxy.routes
            proxy.close()
        try:
            if container:
                inspected = json.loads(command("inspect", container))[0]
                assert inspected["Name"] == "/" + name
                assert inspected["Config"]["Labels"].get("mobiraeon.verification") == name
                command("rm", "-f", "-v", container)
            if network_created:
                inspected = json.loads(command("network", "inspect", name))[0]
                assert inspected["Labels"].get("mobiraeon.verification") == name
                command("network", "rm", name)
            report["cleanup"] = "verified_owned_resources_removed"
        except Exception:
            report["cleanup"] = "incomplete"
            report["result"] = "failed"
    return report
