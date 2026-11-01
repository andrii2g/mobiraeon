"""Real CLI, persisted catalog, direct TLS, trust failures, outside-checkout probes."""

import argparse
import json
import os
import queue
import signal
import socket
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from tls_fixture import certificate

from mobiraeon.registry_schema import GRANTABLE


def exercise(python, package):
    environment = {k: v for k, v in os.environ.items() if not k.startswith("MOBIRAEON_")}
    environment.pop("PYTHONPATH", None)
    commands = []
    with tempfile.TemporaryDirectory(prefix="mobiraeon-registry-") as temporary:
        outside = Path(temporary)
        private = outside / "private"
        config = outside / "settings.toml"
        cert, key = certificate(outside, include_ip=False)
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        # JSON string syntax is valid for these TOML strings on both platforms.
        config.write_text(
            f"""[database]
path = {json.dumps(str(private / "catalog.db"))}
[access]
private_dir = {json.dumps(str(private))}
credential_file = {json.dumps(str(private / "credentials/owner.token"))}
[api]
enabled = true
port = {port}
cert_file = {json.dumps(str(cert))}
key_file = {json.dumps(str(key))}
client_ca = {json.dumps(str(cert))}
client_url = "https://localhost:{port}"
""",
            encoding="utf-8",
        )
        base = [str(python), "-m", "mobiraeon", "--config", str(config)]

        def run(*args, expect=0):
            process = subprocess.run(
                [*base, *map(str, args)],
                cwd=outside,
                env=environment,
                capture_output=True,
                text=True,
                timeout=90,
            )
            commands.append(
                {
                    "arguments": list(map(str, args)),
                    "exit_code": process.returncode,
                    "stdout": process.stdout,
                    "stderr": process.stderr,
                }
            )
            assert process.returncode == expect, process.stderr + process.stdout
            return json.loads(process.stdout)

        assert run("provision")["data"]["audit_status"] == "not_applicable"
        run("initialize")
        setup = outside / "setup.json"
        setup.write_text(
            json.dumps(
                {
                    "operation": "access.setup",
                    "target": {
                        "kind": "access",
                        "entity_kind": "installation",
                        "identity": "owner",
                    },
                    "inputs": {
                        "destination": "owner.token",
                        "lifetime_seconds": 3600,
                        "allow_self_review": True,
                        "grants": [
                            {"action": x.value, "scope": "*"} for x in sorted(GRANTABLE)
                        ],
                    },
                }
            )
        )
        run("--request-file", setup, "setup")
        for name, content in (
            ("malformed", b'{"synthetic-sensitive":'),
            ("encoding", b"\xffsynthetic-sensitive"),
            ("structure", b"[]"),
        ):
            invalid = outside / (name + ".json")
            invalid.write_bytes(content)
            result = run("--input-file", invalid, "prepare", expect=2)
            assert result["outcome"] == "invalid_input" and result["reason"] == "invalid_input"
        first = run("--input-file", package, "prepare")["data"]["records"][0]
        second = run("--input-file", package, "prepare")["data"]["records"][0]
        assert first == second
        assert len([x for x in first["publications"] if x["kind"] == "agent"]) == 5
        # Each subprocess restart proves persistence and explicit supplied inputs.
        request = outside / "read.json"
        request.write_text(
            json.dumps(
                {
                    "operation": "registry.read",
                    "target": {
                        "kind": "control",
                        "entity_kind": "agent",
                        "identity": "orchestrator-01",
                    },
                    "inputs": {},
                }
            )
        )
        local = run("--request-file", request, "registry")
        assert local["data"]["records"][0]["enabled"] is False
        enable_request = outside / "enable.json"
        enable_request.write_text(
            json.dumps(
                {
                    "operation": "registry.enable",
                    "target": {
                        "kind": "control",
                        "entity_kind": "agent",
                        "identity": "orchestrator-01",
                    },
                    "inputs": {"expected_version": local["data"]["version"]},
                }
            )
        )
        assert (
            run("--request-file", enable_request, "registry", expect=1)["outcome"]
            == "unavailable"
        )
        issue_request = outside / "reader.json"
        issue_request.write_text(
            json.dumps(
                {
                    "operation": "access.issue",
                    "target": {
                        "kind": "access",
                        "entity_kind": "credential",
                        "identity": "reader",
                    },
                    "inputs": {
                        "destination": "reader.token",
                        "lifetime_seconds": 300,
                        "grants": [{"action": "registry.read", "scope": "*"}],
                    },
                }
            )
        )
        reader_id = run("--request-file", issue_request, "registry")["data"]["reference"]
        server = subprocess.Popen(
            [*base, "start"],
            cwd=outside,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            inbox = queue.Queue()
            threading.Thread(
                target=lambda: inbox.put(server.stdout.readline()), daemon=True
            ).start()
            ready = json.loads(inbox.get(timeout=20))
            assert ready["phase"] == "ready"
            remote = run("--request-file", request, "remote")
            assert all(
                remote[key] == local[key] for key in ("operation", "actor", "target", "data")
            )
            assert (
                run("--request-file", enable_request, "remote", expect=1)["outcome"]
                == "unavailable"
            )
            owner_settings = config.read_text()
            config.write_text(owner_settings.replace("owner.token", "reader.token"))
            for command in ("registry", "remote"):
                assert (
                    run("--request-file", enable_request, command, expect=1)["outcome"]
                    == "refused"
                )
            config.write_text(owner_settings)
            assert run("--request-file", request, "registry")["data"] == local["data"]
            config.write_text(
                owner_settings.replace("https://localhost:", "https://127.0.0.1:")
            )
            assert (
                run("--request-file", request, "remote", expect=1)["outcome"]
                == "uncertain_effects"
            )
            config.write_text(owner_settings)
            revoke_request = outside / "revoke.json"
            revoke_request.write_text(
                json.dumps(
                    {
                        "operation": "access.revoke",
                        "target": {
                            "kind": "access",
                            "entity_kind": "credential",
                            "identity": reader_id,
                        },
                        "inputs": {"expected_version": 1},
                    }
                )
            )
            run("--request-file", revoke_request, "registry")
            cleanup_request = outside / "cleanup.json"
            cleanup_request.write_text(
                json.dumps(
                    {
                        "operation": "access.reconcile",
                        "target": {
                            "kind": "access",
                            "entity_kind": "credential",
                            "identity": reader_id,
                        },
                        "inputs": {},
                    }
                )
            )
            run(
                "--request-file",
                cleanup_request,
                "--credential-name",
                "reader.token",
                "cleanup",
            )
            assert not (private / "credentials/reader.token").exists()
            assert run("--request-file", request, "registry")["data"] == local["data"]
            # Wrong CA trust must fail closed and never become an insecure retry.
            alternate = outside / "alternate"
            alternate.mkdir()
            wrong_cert, _ = certificate(alternate)
            # Change client CA only; server already holds its original certificate.
            config.write_text(
                config.read_text().replace(
                    "client_ca = " + json.dumps(str(cert)),
                    "client_ca = " + json.dumps(str(wrong_cert)),
                )
            )
            assert (
                run("--request-file", request, "remote", expect=1)["outcome"]
                == "uncertain_effects"
            )
        finally:
            if os.name == "nt":
                # Native console events are exercised separately by verify_interruptions.
                server.kill()
            else:
                server.send_signal(signal.SIGTERM)
            stdout, stderr = server.communicate(timeout=20)
            if os.name != "nt":
                assert server.returncode == 0
                assert json.loads(stdout.splitlines()[-1])["outcome"] == "success"
            commands.append(
                {
                    "server_exit_code": server.returncode,
                    "stdout": stdout,
                    "stderr": stderr,
                    "termination": "forced cleanup on Windows; native console probe separate"
                    if os.name == "nt"
                    else "SIGTERM",
                }
            )
    return {"result": "passed", "checks": commands, "catalog": first}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument(
        "--input", type=Path, default=Path(__file__).parents[1] / "bootstrap/initial-test.json"
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = exercise(args.python, args.input.resolve())
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
