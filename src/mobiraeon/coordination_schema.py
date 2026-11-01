"""Strict bounded workflow inputs; content is small, supplied and hash verified."""

import hashlib

from mobiraeon.contracts import WORKFLOW_ACTIONS, BusinessTarget, Operation, _token
from mobiraeon.registry_schema import fields, integer, invalid, reference, safe_json, string


def artifacts(value):
    if not isinstance(value, list) or not value:
        invalid()
    seen = set()
    for item in value:
        fields(
            item,
            {"identity", "revision", "sha256", "content"},
            {"identity", "revision", "sha256", "content"},
        )
        _token(item["identity"])
        _token(item["revision"])
        string(item["content"])
        if item["sha256"] != hashlib.sha256(item["content"].encode()).hexdigest():
            invalid()
        if item["identity"] in seen:
            invalid()
        seen.add(item["identity"])


def work_contract(work):
    keys = {
        "project",
        "request",
        "initiative",
        "project_context",
        "request_outcome",
        "initiative_outcome",
        "objective",
        "scope",
        "exclusions",
        "inputs",
        "deliverables",
        "criteria",
        "role",
    }
    fields(work, keys, keys)
    for key in ("project", "request", "initiative"):
        _token(work[key])
    for key in (
        "objective",
        "scope",
        "exclusions",
        "project_context",
        "request_outcome",
        "initiative_outcome",
    ):
        string(work[key])
    artifacts(work["inputs"])
    reference(work["role"], "role")
    if not isinstance(work["deliverables"], list) or not work["deliverables"]:
        invalid()
    for item in work["deliverables"]:
        _token(item)
    if len(set(work["deliverables"])) != len(work["deliverables"]):
        invalid()
    if not isinstance(work["criteria"], dict) or not work["criteria"]:
        invalid()
    for key, item in work["criteria"].items():
        _token(key)
        fields(item, {"requirement", "evidence"}, {"requirement", "evidence"})
        string(item["requirement"])
        _token(item["evidence"])


def validate(operation, target, inputs):
    if operation not in WORKFLOW_ACTIONS or not isinstance(target, BusinessTarget):
        invalid()
    if (target.kind, target.entity_kind, target.revision) != ("entity", "task", None):
        invalid()
    safe_json(inputs)
    additions = {
        Operation.SUPPLY: {"work"},
        Operation.ALLOCATE: {"assignment_id", "attempt_id", "configuration"},
        Operation.DISPATCH: {"attempt_id"},
        Operation.OBSERVE: {"attempt_id", "observation", "detail"},
        Operation.SUBMIT: {"attempt_id", "submission_id", "artifacts"},
        Operation.ASSESS: {
            "submission_id",
            "submission_digest",
            "evidence",
            "decision",
            "rationale",
        },
        Operation.ACCEPT: {"submission_id", "submission_digest", "assessment_id"},
        Operation.STATUS: set(),
    }[operation]
    required = additions | ({"operation_id"} if operation != Operation.STATUS else set())
    if operation not in {Operation.SUPPLY, Operation.STATUS}:
        required |= {"expected_version"}
    fields(inputs, required, required)
    for key in {
        "operation_id",
        "assignment_id",
        "attempt_id",
        "submission_id",
        "assessment_id",
    } & inputs.keys():
        _token(inputs[key])
    if "expected_version" in inputs:
        integer(inputs["expected_version"])
    if "work" in inputs:
        work_contract(inputs["work"])
    if "configuration" in inputs:
        refs = inputs["configuration"]
        fields(
            refs,
            {"agent", "profile", "role", "context"},
            {"agent", "profile", "role", "context"},
        )
        for kind, value in refs.items():
            reference(value, kind)
    for key in {"artifacts", "evidence"} & inputs.keys():
        artifacts(inputs[key])
    if "observation" in inputs and inputs["observation"] not in {
        "succeeded",
        "failed",
        "unknown",
    }:
        invalid()
    if "decision" in inputs and inputs["decision"] not in {"approve", "reject"}:
        invalid()
    for key in {"detail", "rationale", "submission_digest"} & inputs.keys():
        string(inputs[key])
