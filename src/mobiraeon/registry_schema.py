"""Storage-independent strict Registry wire/document contracts."""

import hashlib
import json
import math
import re
from urllib.parse import urlsplit

from mobiraeon.contracts import (
    EXECUTION_ACTIONS,
    FORGE_ACTIONS,
    WORKFLOW_ACTIONS,
    BusinessTarget,
    Operation,
    _token,
)
from mobiraeon.errors import Reason, SafeError

KINDS = {
    "agent",
    "profile",
    "instruction",
    "role",
    "capability",
    "policy",
    "connection",
    "transport",
    "context",
    "output",
}
LIMITS = {
    "duration_seconds": (1, 86400),
    "retries": (0, 10),
    "tokens": (1, 10000000),
    "cost_microusd": (0, 1000000000),
    "concurrency": (1, 64),
}
CATALOG_ACTIONS = {
    Operation.CREATE,
    Operation.EDIT,
    Operation.DISCARD,
    Operation.VALIDATE,
    Operation.REVIEW,
    Operation.PUBLISH,
    Operation.REGISTRY_READ,
    Operation.HISTORY,
    Operation.SELECT,
    Operation.ENABLE,
    Operation.DISABLE,
    Operation.RECONCILE,
}
ACCESS_ACTIONS = {
    Operation.ISSUE,
    Operation.ROTATE,
    Operation.GRANTS,
    Operation.REVOKE,
    Operation.ACCESS_RECONCILE,
}
GRANTABLE = (
    CATALOG_ACTIONS | ACCESS_ACTIONS | WORKFLOW_ACTIONS | EXECUTION_ACTIONS | FORGE_ACTIONS
)
PROFILE_REFS = {
    "roleRef": "role",
    "contextPolicyRef": "context",
    "runnerTransportRef": "transport",
    "providerConnectionRef": "connection",
    "capabilityRequirementsRef": "capability",
    "outputContractRef": "output",
    "toolPolicyRef": "policy",
    "authorityPolicyRef": "policy",
}
SCHEMAS = {
    "agent": {"profileRef", "overrides", "configuration_stage"},
    "profile": {
        *PROFILE_REFS,
        "instructionsRefs",
        "runtime",
        "provider",
        "model",
        "reasoning",
        "runtimeOptions",
        "providerOptions",
        "secretRefs",
        "limits",
        "fallbackPolicyRef",
        "configuration_stage",
    },
    "capability": {
        "runtime",
        "provider",
        "models",
        "reasoning",
        "runtime_options",
        "provider_options",
        "enforcement",
    },
    "connection": {"endpoint", "accountRef", "credentialRef", "availability"},
    "transport": {"name", "version", "text"},
    "instruction": {"text", "source"},
    "role": {"text", "source"},
    "policy": {"text", "source", "policy_type"},
    "context": {"text", "source"},
    "output": {"text", "source"},
}


def invalid(reason=Reason.INVALID_INPUT):
    raise SafeError(reason)


def canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def load_json(content):
    if len(content) > 65536:
        invalid()

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                invalid()
            result[key] = value
        return result

    try:
        value = json.loads(
            content, object_pairs_hook=pairs, parse_constant=lambda value: invalid()
        )
        safe_json(value)
        return value
    except ValueError, TypeError, RecursionError:
        invalid()


def safe_json(value, depth=0):
    if depth > 20:
        invalid()
    if isinstance(value, str):
        if len(value) > 60000 or re.search(r"mbr_[a-f0-9]{32}_[A-Za-z0-9_-]{43}", value):
            invalid()
        if "-----BEGIN " in value and "PRIVATE KEY-----" in value:
            invalid()
    elif isinstance(value, dict):
        if len(value) > 256 or any(not isinstance(k, str) for k in value):
            invalid()
        for key, child in value.items():
            safe_json(key, depth + 1)
            safe_json(child, depth + 1)
    elif isinstance(value, list):
        if len(value) > 256:
            invalid()
        for child in value:
            safe_json(child, depth + 1)
    elif value is not None and type(value) not in (bool, int, float):
        invalid()
    elif isinstance(value, float) and not math.isfinite(value):
        invalid()


def fields(value, allowed, required=None):
    if not isinstance(value, dict) or set(value) - set(allowed):
        invalid()
    if required is not None and set(required) - set(value):
        invalid()


def string(value, *, maximum=4096):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        invalid()
    return value


def integer(value, minimum=1, maximum=2147483647):
    if type(value) is not int or not minimum <= value <= maximum:
        invalid()
    return value


def reference(value, kind=None):
    fields(value, {"kind", "identity", "revision"}, {"kind", "identity", "revision"})
    if value["kind"] not in KINDS or (kind is not None and value["kind"] != kind):
        invalid()
    for name in ("identity", "revision"):
        _token(value[name])
    return value


def limits(value, complete=True):
    fields(value, LIMITS)
    if complete and set(value) != set(LIMITS):
        invalid(Reason.INCOMPLETE)
    for key, number in value.items():
        integer(number, *LIMITS[key])


def validate_document(kind, document, *, complete=False):
    if kind not in KINDS:
        invalid()
    safe_json(document)
    fields(document, SCHEMAS[kind])
    if complete and set(SCHEMAS[kind]) - {"fallbackPolicyRef", "configuration_stage"} - set(
        document
    ):
        invalid(Reason.INCOMPLETE)
    dependencies = []

    def ref(value, expected=None):
        dependencies.append(reference(value, expected))

    for key, value in document.items():
        if value is None:
            if complete:
                invalid(Reason.INCOMPLETE)
            continue
        if kind == "profile" and key in PROFILE_REFS:
            ref(value, PROFILE_REFS[key])
        elif key == "profileRef":
            ref(value, "profile")
        elif key == "fallbackPolicyRef":
            ref(value, "policy")
        elif key == "instructionsRefs":
            if not isinstance(value, list) or (complete and not value):
                invalid()
            for item in value:
                ref(item, "instruction")
        elif key == "runtime" and kind == "profile":
            fields(
                value,
                {"name", "version", "capabilityRef"},
                {"name", "version", "capabilityRef"},
            )
            string(value["name"])
            string(value["version"])
            ref(value["capabilityRef"], "capability")
        elif key in {"limits", "overrides"}:
            limits(value, complete=key == "limits" and complete)
        elif key == "source":
            fields(value, {"uri", "revision", "sha256"}, {"uri", "revision", "sha256"})
            string(value["uri"])
            string(value["revision"])
            if not re.fullmatch("[0-9a-f]{64}", value["sha256"]):
                invalid()
            if (
                "text" in document
                and value["sha256"] != hashlib.sha256(document["text"].encode()).hexdigest()
            ):
                invalid()
        elif key == "configuration_stage":
            if value not in {"initial_test", "candidate"}:
                invalid()
        elif key == "availability":
            if value not in {"unprovisioned", "declared"}:
                invalid()
        elif key == "endpoint":
            parts = urlsplit(string(value))
            if (
                parts.scheme != "https"
                or not parts.hostname
                or parts.username
                or parts.password
                or parts.query
                or parts.fragment
            ):
                invalid()
        elif key == "secretRefs":
            if not isinstance(value, list):
                invalid()
            for item in value:
                string(item)
        elif kind == "capability" and key in {"models", "reasoning"}:
            if (
                not isinstance(value, list)
                or not value
                or any(not isinstance(x, str) or not x for x in value)
            ):
                invalid()
        elif key in {
            "runtimeOptions",
            "providerOptions",
            "runtime_options",
            "provider_options",
        }:
            fields(
                value,
                {"json", "ephemeral", "ignore_user_config", "sandbox"}
                if "runtime" in key.lower()
                else {"service_tier"},
            )
            for option, option_value in value.items():
                if key.endswith("_options"):
                    if not isinstance(option_value, list) or not option_value:
                        invalid()
                elif option in {"json", "ephemeral", "ignore_user_config"}:
                    if type(option_value) is not bool:
                        invalid()
                else:
                    string(option_value)
        elif key == "enforcement":
            fields(value, LIMITS)
            if complete and set(value) != set(LIMITS):
                invalid(Reason.INCOMPLETE)
            if any(x not in {"declared", "unavailable", "unverified"} for x in value.values()):
                invalid()
        elif key == "policy_type":
            if value not in {"tool", "authority", "fallback"}:
                invalid()
        else:
            string(value, maximum=60000 if key == "text" else 4096)
    seen = {}
    for dep in dependencies:
        key = (dep["kind"], dep["identity"])
        if key in seen and seen[key] != dep["revision"]:
            invalid()
        seen[key] = dep["revision"]
    return dependencies


def validate_grants(grants):
    if not isinstance(grants, list) or not grants:
        invalid()
    seen = set()
    for grant in grants:
        fields(grant, {"action", "scope"}, {"action", "scope"})
        if grant["action"] not in GRANTABLE:
            invalid()
        scope = grant["scope"]
        if scope != "*":
            if not isinstance(scope, str) or scope.count(":") != 1:
                invalid()
            kind, identity = scope.split(":")
            if kind not in KINDS | {"credential", "audit", "task", "project"}:
                invalid()
            if identity != "*":
                _token(identity)
        pair = (grant["action"], scope)
        if pair in seen:
            invalid()
        seen.add(pair)


def validate_request(operation, target, inputs):
    if not isinstance(target, BusinessTarget) or not isinstance(inputs, dict):
        invalid()
    safe_json(inputs)
    if target.entity_kind not in KINDS | {"credential", "audit", "installation"}:
        invalid()
    if operation in ACCESS_ACTIONS | {Operation.SETUP, Operation.RECOVER}:
        expected_kind = (
            "installation"
            if operation in {Operation.SETUP, Operation.RECOVER}
            else "credential"
        )
        if target.kind != "access" or target.entity_kind != expected_kind:
            invalid()
    elif operation == Operation.RECONCILE:
        if target.entity_kind != "audit":
            invalid()
    elif target.entity_kind not in KINDS:
        invalid()
    if target.kind == "control" and target.entity_kind != "agent":
        invalid()
    required = {}
    target_kind = None
    if operation == Operation.CREATE:
        required, target_kind = {"document"}, "entity"
    elif operation == Operation.EDIT:
        required, target_kind = {"expected_version", "document"}, "draft"
    elif operation in {
        Operation.DISCARD,
        Operation.VALIDATE,
        Operation.REVIEW,
        Operation.PUBLISH,
    }:
        required, target_kind = {"expected_version"}, "draft"
        if operation == Operation.REVIEW:
            required |= {"decision", "rationale"}
        if operation == Operation.PUBLISH:
            required |= {"review_id"}
    elif operation in {Operation.SELECT, Operation.ENABLE, Operation.DISABLE}:
        required, target_kind = {"expected_version"}, "control"
        if target.entity_kind != "agent":
            invalid()
        if operation == Operation.SELECT:
            required |= {"revision"}
    elif operation in {Operation.ISSUE, Operation.ROTATE, Operation.SETUP, Operation.RECOVER}:
        required, target_kind = {"destination", "lifetime_seconds", "grants"}, "access"
        if operation == Operation.SETUP:
            required |= {"allow_self_review"}
        if operation == Operation.ROTATE:
            required |= {"expected_version"}
    elif operation in {Operation.GRANTS, Operation.REVOKE}:
        required, target_kind = {"expected_version"}, "access"
        if operation == Operation.GRANTS:
            required |= {"grants"}
    elif operation in {
        Operation.REGISTRY_READ,
        Operation.HISTORY,
        Operation.RECONCILE,
        Operation.ACCESS_RECONCILE,
    }:
        required = set()
    else:
        invalid()
    fields(inputs, required, required)
    if target_kind and target.kind != target_kind:
        invalid()
    if operation == Operation.REGISTRY_READ and target.kind not in {
        "entity",
        "draft",
        "publication",
        "control",
    }:
        invalid()
    if operation == Operation.HISTORY and target.kind != "entity":
        invalid()
    if operation == Operation.RECONCILE and target.kind != "audit":
        invalid()
    if operation == Operation.ACCESS_RECONCILE and target.kind != "access":
        invalid()
    if (target.kind == "publication") != (target.revision is not None):
        invalid()
    if "expected_version" in inputs:
        integer(inputs["expected_version"])
    if "document" in inputs:
        validate_document(target.entity_kind, inputs["document"])
    if "decision" in inputs and inputs["decision"] != "approve":
        invalid()
    for key in {"rationale", "review_id", "revision"} & set(inputs):
        string(inputs[key])
    if "grants" in inputs:
        validate_grants(inputs["grants"])
        integer(
            inputs["lifetime_seconds"], 300, 2592000
        ) if "lifetime_seconds" in inputs else None
    if "destination" in inputs:
        _token(inputs["destination"])
    if "allow_self_review" in inputs and type(inputs["allow_self_review"]) is not bool:
        invalid()
