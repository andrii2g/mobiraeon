"""Strict wire contracts; normalized native IDs remain opaque to Coordination."""

import ipaddress
import json
import math
import re
from pathlib import Path
from urllib.parse import urlsplit

from mobiraeon.contracts import FORGE_ACTIONS, BusinessTarget, Operation, _token
from mobiraeon.registry_schema import fields, safe_json

DEFAULT_LIMITS = dict(
    cycle_seconds=100,
    request_seconds=10,
    finalization_seconds=1,
    max_requests=20,
    max_pages=5,
    response_bytes=1048576,
    total_read_bytes=5242880,
    comment_bytes=16384,
)


def need(value):
    if value is not True:
        raise ValueError("invalid forge value")


def strict_int(value, low=1, high=2**63 - 1):
    need(type(value) is int and low <= value <= high)
    return value


def native(value):
    need(isinstance(value, str) and re.fullmatch(r"[1-9][0-9]{0,18}", value) is not None)
    need(int(value) <= 2**63 - 1)
    return value


def component(value):
    need(isinstance(value, str) and 1 <= len(value) <= 100 and value not in {".", ".."})
    need(not any(ord(c) < 32 or 0x7F <= ord(c) <= 0x9F or c in "/\\" for c in value))
    return value


def pairs(items):
    result = {}
    for key, value in items:
        need(key not in result)
        result[key] = value
    return result


def decode(raw, maximum=131072):
    need(isinstance(raw, bytes) and len(raw) <= maximum)
    try:
        return json.loads(
            raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=lambda _: need(False)
        )
    except ValueError, RecursionError:
        raise ValueError("invalid forge JSON") from None


def connection(value):
    fields(
        value,
        {
            "provider",
            "origin",
            "allow_loopback_http",
            "repository",
            "account",
            "credential",
            "tls_ca_file",
            "limits",
        },
        {
            "provider",
            "origin",
            "allow_loopback_http",
            "repository",
            "account",
            "credential",
            "tls_ca_file",
            "limits",
        },
    )
    need(value["provider"] == "gitea" and type(value["allow_loopback_http"]) is bool)
    origin = value["origin"]
    need(isinstance(origin, str) and len(origin.encode()) <= 2048)
    need("?" not in origin and "#" not in origin)
    need(not any(ord(c) <= 32 or ord(c) == 127 for c in origin))
    url = urlsplit(origin)
    need(
        url.scheme in {"http", "https"}
        and bool(url.hostname)
        and url.username is None
        and url.password is None
        and not url.query
        and not url.fragment
        and url.path in {"", "/"}
    )
    host = url.hostname.lower()
    port = url.port if url.port is not None else (443 if url.scheme == "https" else 80)
    need(1 <= port <= 65535)
    if url.scheme == "http":
        try:
            loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            loopback = host == "localhost"
        need(value["allow_loopback_http"] and loopback)
    if ":" in host:
        host = "[" + host + "]"
    for key, names in (
        ("repository", {"id", "owner", "name"}),
        ("account", {"id", "name"}),
        ("credential", {"name", "revision"}),
    ):
        fields(value[key], names, names)
    for key in ("repository", "account"):
        native(value[key]["id"])
        component(value[key]["name"])
    component(value["repository"]["owner"])
    for item in value["credential"].values():
        _token(item)
        need(".." not in item)
    ca = value["tls_ca_file"]
    need(
        ca is None
        or (
            isinstance(ca, str)
            and 0 < len(ca.encode()) <= 4096
            and Path(ca).is_absolute()
            and "\x00" not in ca
        )
    )
    limits = value["limits"]
    fields(limits, set(DEFAULT_LIMITS), set(DEFAULT_LIMITS))
    for key, low, high in (
        ("cycle_seconds", 2, 3600),
        ("request_seconds", 0.1, 300),
        ("finalization_seconds", 0.1, 10),
    ):
        number = limits[key]
        need(type(number) in {int, float} and math.isfinite(number) and low <= number <= high)
    need(limits["finalization_seconds"] < limits["cycle_seconds"])
    need(limits["request_seconds"] <= limits["cycle_seconds"] - limits["finalization_seconds"])
    for key, low, high in (
        ("max_requests", 1, 100),
        ("max_pages", 1, 20),
        ("response_bytes", 1024, 8388608),
        ("total_read_bytes", limits["response_bytes"], 33554432),
        ("comment_bytes", 1024, 65536),
    ):
        strict_int(limits[key], low, high)
    return value | {"origin": f"{url.scheme}://{host}:{port}"}


def validate(operation, target, inputs):
    safe_json(inputs)
    need(
        operation in FORGE_ACTIONS
        and isinstance(target, BusinessTarget)
        and target.kind == "entity"
        and target.entity_kind == "project"
        and target.revision is None
    )
    names = {
        Operation.FORGE_CONFIGURE: {"operation_id", "expected_version", "connection"},
        Operation.FORGE_READ: set(inputs) if isinstance(inputs, dict) else set(),
        Operation.FORGE_LINK: {
            "operation_id",
            "expected_version",
            "task_id",
            "connection_revision",
            "issue_number",
        },
        Operation.FORGE_STATUS: {"task_id"},
        Operation.FORGE_SYNC: {
            "operation_id",
            "expected_version",
            "task_id",
            "connection_revision",
        },
        Operation.FORGE_RESOLVE: {
            "operation_id",
            "expected_version",
            "task_id",
            "conflict_id",
            "action",
            "rationale",
        },
    }[operation]
    if operation == Operation.FORGE_READ:
        need(names in (set(), {"connection_revision"}))
    fields(inputs, names, names)
    for key in names & {"operation_id", "task_id", "connection_revision", "conflict_id"}:
        _token(inputs[key])
    if "connection_revision" in names:
        need(inputs["connection_revision"] != "latest")
    if "expected_version" in names:
        minimum = 0 if operation in {Operation.FORGE_CONFIGURE, Operation.FORGE_LINK} else 1
        need(type(inputs["expected_version"]) is int and inputs["expected_version"] >= minimum)
    if "issue_number" in names:
        strict_int(inputs["issue_number"])
    if operation == Operation.FORGE_CONFIGURE:
        connection(inputs["connection"])
    if operation == Operation.FORGE_RESOLVE:
        need(inputs["action"] in {"refresh", "replace"})
        need(
            isinstance(inputs["rationale"], str)
            and bool(inputs["rationale"].strip())
            and len(inputs["rationale"].encode()) <= 4096
        )
