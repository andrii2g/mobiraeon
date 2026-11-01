"""Explicit input preparation via ordinary operations; stop on any uncertain result."""

import copy
import json

from mobiraeon.contracts import Outcome, _token
from mobiraeon.errors import Reason, SafeError
from mobiraeon.registry_schema import KINDS, SCHEMAS, fields


def prepare(service, package, proof):
    validate_package_structure(package)
    references, receipts = {}, []

    def call(operation, kind, identity, inputs=None, target_kind="entity"):
        result = service.invoke(
            operation,
            {"kind": target_kind, "entity_kind": kind, "identity": identity},
            inputs or {},
            proof=proof,
        )
        if result.outcome != Outcome.SUCCESS:
            # In particular, never retry uncertain mutations automatically.
            raise PreparationStopped(result, receipts)
        return result.data

    def resolve(value):
        if isinstance(value, dict):
            if set(value) == {"published"}:
                if value["published"] not in references:
                    raise SafeError(Reason.NOT_FOUND)
                return references[value["published"]]
            return {k: resolve(v) for k, v in value.items()}
        if isinstance(value, list):
            return [resolve(x) for x in value]
        return value

    for definition in package["definitions"]:
        fields(definition, {"kind", "identity", "document"}, {"kind", "identity", "document"})
        kind, identity = definition["kind"], definition["identity"]
        document = resolve(copy.deepcopy(definition["document"]))
        result = service.invoke(
            "registry.history",
            {"kind": "entity", "entity_kind": kind, "identity": identity},
            {},
            proof=proof,
        )
        if result.reason == Reason.NOT_FOUND:
            version = call("registry.create", kind, identity, {"document": document}).version
            records = []
        elif result.outcome == Outcome.SUCCESS:
            records = result.data.records
            latest = max(
                (x for x in records if x["record_type"] == "draft"), key=lambda x: x["version"]
            )
            if latest["discarded"] or latest["document"] != document:
                raise SafeError(Reason.CONFLICT)
            version = latest["version"]
            events = [x for x in records if x["record_type"] == "audit"]
            successes = {x["invocation"] for x in events if x["outcome"] == "success"}
            if any(
                x["outcome"] == "uncertain_effects" and x["invocation"] not in successes
                for x in events
            ):
                # Current state alone does not establish ambiguous earlier effects.
                raise SafeError(Reason.UNAVAILABLE)
        else:
            raise PreparationStopped(result, receipts)
        published = [
            x for x in records if x["record_type"] == "publication" and x["version"] == version
        ]
        if published:
            revision = published[0]["id"]
        else:
            call("registry.validate", kind, identity, {"expected_version": version}, "draft")
            existing = [
                x for x in records if x["record_type"] == "review" and x["version"] == version
            ]
            review = (
                None
                if existing
                else call(
                    "registry.review",
                    kind,
                    identity,
                    {
                        "expected_version": version,
                        "decision": "approve",
                        "rationale": "Owner approved initial test configuration; unprovisione"
                        "d and unqualified; no execution authority.",
                    },
                    "draft",
                )
            )
            revision = call(
                "registry.publish",
                kind,
                identity,
                {
                    "expected_version": version,
                    "review_id": existing[-1]["id"] if existing else review.reference,
                },
                "draft",
            ).reference
        references[f"{kind}:{identity}"] = {
            "kind": kind,
            "identity": identity,
            "revision": revision,
        }
        if kind == "agent":
            control = call("registry.read", kind, identity, target_kind="control")
            if control.records[0]["enabled"]:
                raise SafeError(Reason.CONFLICT)
            selected = control.records[0]["selected"]
            if selected is None:
                call(
                    "registry.select",
                    kind,
                    identity,
                    {"expected_version": control.version, "revision": revision},
                    "control",
                )
            elif selected != revision:
                raise SafeError(Reason.CONFLICT)
        receipts.append({"kind": kind, "identity": identity, "revision": revision})
    return {"stage": "initial_test", "publications": receipts, "execution_eligible": False}


def validate_package_structure(package):
    """Check the entire package envelope before any per-operation preparation."""
    fields(
        package, {"stage", "provenance", "definitions"}, {"stage", "provenance", "definitions"}
    )
    if (
        package["stage"] != "initial_test"
        or not isinstance(package["definitions"], list)
        or not isinstance(package["provenance"], dict)
    ):
        raise SafeError(Reason.INVALID_INPUT)
    for definition in package["definitions"]:
        fields(definition, {"kind", "identity", "document"}, {"kind", "identity", "document"})
        if not isinstance(definition["kind"], str) or definition["kind"] not in KINDS:
            raise SafeError(Reason.INVALID_INPUT)
        try:
            _token(definition["identity"])
        except ValueError:
            raise SafeError(Reason.INVALID_INPUT) from None
        fields(definition["document"], SCHEMAS[definition["kind"]])


class PreparationStopped(Exception):
    def __init__(self, result, receipts):
        self.result, self.receipts = result, receipts
        super().__init__("preparation_stopped")


def read_package(path):
    # Packages contain captured Role text and can exceed one operation's 64KiB.
    from mobiraeon.registry_schema import safe_json

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise SafeError(Reason.INVALID_INPUT)
            result[key] = value
        return result

    try:
        content = path.read_bytes()
        if len(content) > 1048576:
            raise SafeError(Reason.INVALID_INPUT)
        value = json.loads(content, object_pairs_hook=pairs)
        safe_json(value)
        validate_package_structure(value)
    except OSError, ValueError, TypeError, RecursionError:
        # This boundary runs before prepare or any catalog mutation. Never wrap
        # preparation itself: possible effects must retain their own outcomes.
        raise SafeError(Reason.INVALID_INPUT) from None
    return value
