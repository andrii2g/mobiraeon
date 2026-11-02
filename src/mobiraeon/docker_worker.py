"""One prepared local Docker Worker. No arbitrary commands, pulls or retries at admission."""

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from contextlib import contextmanager
from importlib.resources import files

from mobiraeon.errors import Reason, SafeError
from mobiraeon.execution_settings import MIB
from mobiraeon.private_state import harden, protected


def asset_hashes():
    assets = files("mobiraeon").joinpath("fixture_assets")
    return {
        name: hashlib.sha256(assets.joinpath(name).read_bytes()).hexdigest()
        for name in ("Dockerfile", "program.py", "guard.py")
    }


def build_digest():
    return hashlib.sha256(json.dumps(asset_hashes(), sort_keys=True).encode()).hexdigest()


@contextmanager
def actuation_lock(private):
    if sys.platform != "linux":
        raise SafeError(Reason.UNAVAILABLE)
    import fcntl

    private.verify()
    path = private.directory / "execution-worker.lock"
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        harden(path)
    except FileExistsError:
        protected(path)
        descriptor = os.open(path, os.O_RDWR)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise SafeError(Reason.UNAVAILABLE) from None
        yield
    finally:
        os.close(descriptor)


class DockerWorker:
    def __init__(self, settings):
        self.settings = settings
        self.base = [
            settings.get("docker_executable", "/snap/bin/docker"),
            "--host=" + settings.get("endpoint", "unix:///var/run/docker.sock"),
        ]
        self.environment = {k: v for k, v in os.environ.items() if not k.startswith("DOCKER_")}

    def call(self, *args, timeout=10, check=True):
        if sys.platform != "linux":
            raise SafeError(Reason.UNAVAILABLE)
        try:
            result = subprocess.run(
                [*self.base, *map(str, args)],
                env=self.environment,
                capture_output=True,
                timeout=max(0.05, timeout),
            )
        except OSError, subprocess.TimeoutExpired:
            raise SafeError(Reason.UNCERTAIN) from None
        if check and result.returncode:
            raise SafeError(Reason.UNAVAILABLE)
        return result

    def engine(self, timeout=10):
        info = json.loads(self.call("info", "--format", "json", timeout=timeout).stdout)
        if info["ID"] != self.settings.get("engine_id"):
            raise SafeError(Reason.UNAVAILABLE)
        return info

    def preflight(self):
        info = self.engine()
        required = ("MemoryLimit", "SwapLimit", "CpuCfsPeriod", "CpuCfsQuota", "PidsLimit")
        if (
            info["OSType"] != "linux"
            or info.get("CgroupVersion") != "2"
            or not all(info.get(key) is True for key in required)
        ):
            raise SafeError(Reason.UNAVAILABLE)
        if not any("seccomp" in item for item in info.get("SecurityOptions", [])):
            raise SafeError(Reason.UNAVAILABLE)
        image = json.loads(self.call("image", "inspect", self.settings["image_id"]).stdout)[0]
        if (
            image["Id"] != self.settings["image_id"]
            or image["Config"]["User"] != "65532:65532"
            or image["Config"]["Entrypoint"] != ["python", "-I", "/fixture/guard.py"]
            or image["Config"].get("Labels", {}).get("name.mobiraeon.fixture-inputs")
            != build_digest()
        ):
            raise SafeError(Reason.UNAVAILABLE)
        return {
            "engine_id": info["ID"],
            "version": info["ServerVersion"],
            "os": info["OperatingSystem"],
            "architecture": info["Architecture"],
            "image_id": image["Id"],
            "labels": image["Config"]["Labels"],
        }

    def create(self, handoff, timeout=None):
        deadline = time.monotonic() + (timeout or self.settings["startup_seconds"])
        self.engine(max(0.05, deadline - time.monotonic()))
        s = self.settings
        shm = s["scratch_bytes"] // 4
        temporary = s["scratch_bytes"] - shm - MIB
        lifetime = (
            s["startup_seconds"]
            + s["execution_seconds"]
            + s["grace_seconds"]
            + s["cleanup_seconds"]
        )
        args = [
            "create",
            "--name",
            handoff["name"],
            "--label",
            "name.mobiraeon.nonce=" + handoff["nonce"],
            "--label",
            "name.mobiraeon.attempt=" + handoff["attempt"],
            "--user",
            "65532:65532",
            "--read-only",
            "--network",
            "none",
            "--ipc",
            "private",
            "--cgroupns",
            "private",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges=true",
            "--log-driver",
            "none",
            "--cpus",
            str(s["cpus"]),
            "--memory",
            str(s["memory_bytes"]),
            "--memory-swap",
            str(s["memory_bytes"]),
            "--pids-limit",
            str(s["pids"]),
            "--tmpfs",
            f"/tmp:rw,noexec,nosuid,nodev,size={temporary},mode=1777",
            "--tmpfs",
            f"/dev:rw,noexec,nosuid,size={MIB},mode=755",
            "--mount",
            "type=bind,source=/dev/null,target=/dev/null,readonly",
            "--tmpfs",
            f"/dev/shm:rw,noexec,nosuid,nodev,size={shm},mode=1777",
            "--interactive",
            self.settings["image_id"],
            handoff["mode"],
            str(lifetime),
        ]
        result = self.call(*args, timeout=max(0.05, deadline - time.monotonic()))
        identity = result.stdout.decode().strip()
        if not re.fullmatch(r"[0-9a-f]{64}", identity):
            raise SafeError(Reason.UNCERTAIN)
        return identity

    def inspect(self, handoff, identity=None, timeout=10):
        deadline = time.monotonic() + timeout
        self.engine(timeout)
        result = self.call(
            "container",
            "inspect",
            identity or handoff["name"],
            timeout=max(0.05, deadline - time.monotonic()),
            check=False,
        )
        if result.returncode:
            if b"No such" in result.stderr:
                return None
            raise SafeError(Reason.UNCERTAIN)
        container = json.loads(result.stdout)[0]
        labels = container["Config"].get("Labels", {})
        if (
            container["Name"] != "/" + handoff["name"]
            or container["Image"] != handoff["settings"]["image_id"]
            or labels.get("name.mobiraeon.nonce") != handoff["nonce"]
            or (identity is not None and container["Id"] != identity)
        ):
            raise SafeError(Reason.UNCERTAIN)
        return container

    def start(self, identity, timeout=10):
        deadline = time.monotonic() + timeout
        self.engine(timeout)
        if time.monotonic() >= deadline:
            raise SafeError(Reason.UNCERTAIN)
        return subprocess.Popen(
            [*self.base, "start", "--attach", "--interactive", identity],
            env=self.environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def cleanup(self, handoff, record):
        s = self.settings
        deadline = time.monotonic() + s["grace_seconds"] + s["cleanup_seconds"]

        def remaining():
            return max(0.05, deadline - time.monotonic())

        container = self.inspect(handoff, record.get("container_id"), timeout=remaining())
        if container is None:
            # No create intent means no possible delivery. Otherwise absence of an
            # unacknowledged create is never quiescence evidence.
            return (
                not record.get("create_intent")
                or bool(record.get("retired"))
                or bool(record.get("create_ack") and record.get("container_id"))
            )
        identity = container["Id"]
        if container["State"]["Running"]:
            self.call(
                "stop",
                "--time",
                str(max(0, int(s["grace_seconds"]))),
                identity,
                timeout=remaining(),
                check=False,
            )
        container = self.inspect(handoff, identity, timeout=remaining())
        if container is not None and container["State"]["Running"]:
            self.call("kill", identity, timeout=remaining())
            container = self.inspect(handoff, identity, timeout=remaining())
        self.last_state = container
        # Removing the exact established ID retires its namespace and descendants;
        # stale start delivery to that ID cannot recreate it.
        self.call("rm", "--force", identity, timeout=remaining())
        absent = self.inspect(handoff, identity, timeout=remaining()) is None
        return absent and bool(record.get("create_ack"))
