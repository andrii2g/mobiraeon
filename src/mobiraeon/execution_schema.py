"""Fixture-only request/content bridge. Registry limits are unchanged."""

import copy
import hashlib
import json

from mobiraeon.contracts import EXECUTION_ACTIONS, BusinessTarget, Operation, _token
from mobiraeon.errors import SafeError
from mobiraeon.registry_schema import fields, integer, invalid, load_json, safe_json, string

REVISION = "supervised-fixture-v1"
MODES = {"success", "failure", "wait", "excess_output", "stubborn_child"}
ENVELOPE = 1024 * 1024


def reference(kind):
    return {"kind": kind, "identity": "supervised-fixture-" + kind, "revision": REVISION}


def supervised(work):
    return isinstance(work, dict) and work.get("role") == reference("role")


def bridge_metadata(inputs):
    metadata = copy.deepcopy(inputs)
    groups = []
    if "work" in metadata:
        work = metadata["work"]
        if not supervised(work):
            invalid()
        if work.get("deliverables") != ["fixture-summary"] or any(
            not isinstance(c, dict) or c.get("evidence") != "fixture-summary"
            for c in work.get("criteria", {}).values()
        ):
            invalid()
        groups.append((work.get("inputs"), "fixture-input"))
    for key in ("artifacts", "evidence"):
        if key in metadata:
            groups.append((metadata[key], "fixture-summary"))
    for artifacts, identity in groups:
        if not isinstance(artifacts, list) or len(artifacts) != 1:
            invalid()
        item = artifacts[0]
        if not isinstance(item, dict) or item.get("identity") != identity:
            invalid()
        content = item.get("content")
        if not isinstance(content, str) or not content or "\0" in content:
            invalid()
        raw = content.encode("utf-8")
        if len(raw) > 131072 or item.get("sha256") != hashlib.sha256(raw).hexdigest():
            invalid()
        # Validate all metadata and secret-shaped content with the existing checks,
        # in chunks; only the fixed artifact's content gets the wider byte limit.
        for offset in range(0, len(content), 4000):
            safe_json(content[max(0, offset - 128) : offset + 4000])
        item["content"] = "content"
        item["sha256"] = hashlib.sha256(b"content").hexdigest()
    if (
        len(json.dumps(metadata).encode()) > 32768
        or len(json.dumps(inputs).encode()) > ENVELOPE
    ):
        invalid()
    return metadata


def decode(content):
    if len(content) > ENVELOPE:
        invalid()
    try:
        return load_json(content)
    except SafeError:
        pass

    # Preserve duplicate-key and nonfinite rejection without broadening Registry decoding.
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                invalid()
            result[key] = value
        return result

    try:
        document = json.loads(
            content, object_pairs_hook=pairs, parse_constant=lambda value: invalid()
        )
        fields(document, {"operation", "target", "inputs"}, {"operation", "target", "inputs"})
        reduced = copy.deepcopy(document)
        reduced["inputs"] = bridge_metadata(document["inputs"])
        load_json(json.dumps(reduced).encode())
        return document
    except ValueError, TypeError, UnicodeError, RecursionError:
        invalid()


def validate(operation, target, inputs):
    if operation not in EXECUTION_ACTIONS or not isinstance(target, BusinessTarget):
        invalid()
    if (target.kind, target.entity_kind, target.revision) != ("entity", "task", None):
        invalid()
    required = {
        Operation.EXECUTION_RUN: {"operation_id", "expected_version", "attempt_id", "mode"},
        Operation.EXECUTION_STATUS: {"attempt_id"},
        Operation.EXECUTION_STOP: {"operation_id", "attempt_id", "reason"},
    }[operation]
    fields(inputs, required, required)
    safe_json(inputs)
    for key in ("attempt_id", "operation_id"):
        if key in inputs:
            _token(inputs[key])
    if "expected_version" in inputs:
        integer(inputs["expected_version"])
    if "mode" in inputs and inputs["mode"] not in MODES:
        invalid()
    if "reason" in inputs:
        string(inputs["reason"], maximum=512)
