"""Packaged preparation/build helper for a NEW isolated supervised fixture installation."""

import argparse
import json
import shutil
import tempfile
from importlib.resources import files
from pathlib import Path

from mobiraeon.catalog import RegistryService
from mobiraeon.configuration import resolve_configuration
from mobiraeon.contracts import EXECUTION_ACTIONS, Operation, Outcome
from mobiraeon.coordination import Coordinator, require
from mobiraeon.docker_worker import DockerWorker, asset_hashes, build_digest
from mobiraeon.execution import SupervisedConfiguration
from mobiraeon.execution_schema import decode, reference
from mobiraeon.execution_settings import DEFAULTS
from mobiraeon.persistence import Store
from mobiraeon.private_state import PrivateState, durable_new
from mobiraeon.scenario import AUTHOR_ACTIONS, TARGET, proof_for, setup


def discover(image_id):
    settings = DEFAULTS | {
        "docker_executable": shutil.which("docker") or "/snap/bin/docker",
        "endpoint": "unix:///var/run/docker.sock",
        "image_id": image_id,
    }
    worker = DockerWorker(settings)
    info = json.loads(worker.call("info", "--format", "json").stdout)
    settings["engine_id"] = info["ID"]
    return settings


def build():
    worker = DockerWorker(discover(""))
    logs = []
    base = "python:3.14.10-slim-trixie"
    result = worker.call("pull", base, timeout=600)
    logs.append(
        {
            "command": worker.base + ["pull", base],
            "stdout": result.stdout.decode(),
            "stderr": result.stderr.decode(),
            "exit_code": result.returncode,
        }
    )
    image = json.loads(worker.call("image", "inspect", base).stdout)[0]
    digest = next(d for d in image["RepoDigests"] if d.startswith("python@sha256:"))
    with tempfile.TemporaryDirectory(
        prefix="mobiraeon-fixture-build-", dir=Path.home()
    ) as temporary:
        directory = Path(temporary)
        for name in asset_hashes():
            (directory / name).write_bytes(
                files("mobiraeon").joinpath("fixture_assets", name).read_bytes()
            )
        args = [
            "build",
            "--network=none",
            "--build-arg",
            "BASE_IMAGE=" + digest,
            "--label",
            "name.mobiraeon.fixture-inputs=" + build_digest(),
            "--label",
            "name.mobiraeon.fixture-base=" + digest,
            "--iidfile",
            str(directory / "image-id"),
            str(directory),
        ]
        result = worker.call(*args, timeout=600, check=False)
        logs.append(
            {
                "command": worker.base + args,
                "stdout": result.stdout.decode(),
                "stderr": result.stderr.decode(),
                "exit_code": result.returncode,
            }
        )
        if result.returncode:
            return {"result": "failed", "checks": logs, "base_digest": digest}
        identity = (directory / "image-id").read_text().strip()
    return {
        "image_id": identity,
        "base_digest": digest,
        "asset_hashes": asset_hashes(),
        "build_digest": build_digest(),
        "engine_id": worker.settings["engine_id"],
        "endpoint": worker.settings["endpoint"],
        "version": json.loads(worker.call("version", "--format", "json").stdout),
        "checks": logs,
    }


def prepare(directory, input_file, catalog_input, image_id, *, overrides=None):
    require(not directory.exists())
    payload = json.loads(input_file.read_bytes())
    require(set(payload) == {"work"})
    # Decode through the scoped one-MiB bridge, not Registry's 64-KiB envelope.
    supplied = {
        "operation": "coordination.supply",
        "target": TARGET,
        "inputs": {"operation_id": "supply-1", "work": payload["work"]},
    }
    decode(json.dumps(supplied).encode())
    settings = discover(image_id) | (overrides or {})
    DockerWorker(settings).preflight()
    setup(directory, catalog_input)
    private = PrivateState(directory, directory / "scenario.db")
    store = Store(private.database)
    try:
        registry = RegistryService(store, private)
        author = proof_for(private, "author")
        result = registry.invoke(
            "access.grants",
            {"kind": "access", "entity_kind": "credential", "identity": author.identifier},
            {
                "expected_version": 1,
                "grants": [
                    {"action": action.value, "scope": "task:task-1"}
                    for action in sorted(AUTHOR_ACTIONS | EXECUTION_ACTIONS)
                ]
                + [{"action": "registry.read", "scope": "*"}],
            },
            proof=proof_for(private, "admin"),
        )
        require(result.outcome == Outcome.SUCCESS)
        coordinator = Coordinator(
            store,
            private,
            configuration_source=SupervisedConfiguration(),
            content_limits=settings,
        )
        result = coordinator.invoke(
            supplied["operation"], TARGET, supplied["inputs"], proof=author
        )
        require(result.outcome == Outcome.SUCCESS)
        result = coordinator.invoke(
            Operation.ALLOCATE,
            TARGET,
            {
                "operation_id": "allocate-1",
                "expected_version": 1,
                "assignment_id": "assignment-1",
                "attempt_id": "attempt-1",
                "configuration": {
                    kind: reference(kind) for kind in ("agent", "profile", "role", "context")
                },
            },
            proof=author,
        )
        require(result.outcome == Outcome.SUCCESS)
        settings["data_dir"] = str(directory / "execution-data")
        text = (
            "[database]\npath="
            + json.dumps(str(private.database))
            + "\n[access]\nprivate_dir="
            + json.dumps(str(directory))
            + "\ncredential_file="
            + json.dumps(str(private.credential_path("author.token")))
            + "\n[execution]\n"
        )
        text += (
            "\n".join(key + "=" + json.dumps(value) for key, value in settings.items()) + "\n"
        )
        durable_new(directory / "settings.toml", text.encode())
        # Resolve the actual generated configuration through the normal strict resolver.
        resolve_configuration(options={"config": str(directory / "settings.toml")})
        requests = {
            "run": {
                "operation_id": "launch-1",
                "expected_version": result.data.version,
                "attempt_id": "attempt-1",
                "mode": "success",
            },
            "status": {"attempt_id": "attempt-1"},
            "stop": {
                "operation_id": "stop-1",
                "attempt_id": "attempt-1",
                "reason": "operator requested stop",
            },
        }
        for action, inputs in requests.items():
            durable_new(
                directory / (action + ".json"),
                json.dumps(
                    {"operation": "execution." + action, "target": TARGET, "inputs": inputs}
                ).encode(),
            )
        return {
            "settings": str(directory / "settings.toml"),
            "requests": {a: str(directory / (a + ".json")) for a in requests},
            "task": "task-1",
            "assignment": "assignment-1",
            "attempt": "attempt-1",
            "version": result.data.version,
            "image_id": image_id,
            "engine_id": settings["engine_id"],
        }
    finally:
        store.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "build"])
    parser.add_argument("--directory", type=Path)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--catalog-input", type=Path)
    parser.add_argument("--image-id")
    args = parser.parse_args()
    if args.command == "build":
        result = build()
    else:
        if None in (args.directory, args.input, args.catalog_input, args.image_id):
            parser.error("prepare requires directory, input, catalog-input and image-id")
        result = prepare(
            args.directory.resolve(), args.input, args.catalog_input, args.image_id
        )
    print(json.dumps(result))
    if result.get("result") == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
