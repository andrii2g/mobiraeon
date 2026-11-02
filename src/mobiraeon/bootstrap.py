"""Explicit input preparation via ordinary operations; stop on any uncertain result."""

import copy
import json
from dataclasses import asdict, replace
from uuid import uuid4

from mobiraeon.contracts import BusinessData, OperationResult, Outcome, _token
from mobiraeon.errors import Reason, SafeError
from mobiraeon.registry_schema import KINDS, SCHEMAS, fields


def prepare(service, package, proof):
    validate_package_structure(package)
    references, receipts = {}, []
    steps, publications = [], []
    definition = None
    action = "resolve"
    mutated = False
    uncertain = False

    def stopped(result):
        outcome = result.outcome
        if uncertain:
            outcome = Outcome.UNCERTAIN
        elif mutated:
            outcome = Outcome.FAILURE
        progress = {
            "stage": "initial_test",
            "execution_eligible": False,
            "publications": publications,
            "steps": steps,
            "failed": {
                "definition": definition,
                "action": action,
                "reason": result.reason.value,
            },
            "reconciliation_required": uncertain,
        }
        raise PreparationStopped(
            replace(
                result,
                outcome=outcome,
                data=BusinessData(
                    (progress,),
                    state="preparation_stopped",
                    audit_status="unavailable"
                    if any(step["audit_status"] == "unavailable" for step in steps)
                    else "operations_recorded",
                ),
            ),
            receipts,
        )

    def invoke(operation, kind, identity, inputs=None, target_kind="entity"):
        nonlocal action, mutated, uncertain
        action = operation
        mutation = operation not in {"registry.history", "registry.read", "registry.validate"}
        try:
            result = service.invoke(
                operation,
                {"kind": target_kind, "entity_kind": kind, "identity": identity},
                inputs or {},
                proof=proof,
            )
        except Exception:
            uncertain = uncertain or mutation
            raise
        mutated = mutated or (mutation and result.outcome == Outcome.SUCCESS)
        uncertain = uncertain or (mutation and result.outcome == Outcome.UNCERTAIN)
        steps.append(
            {
                "definition": definition,
                "action": operation,
                "operation": result.operation.value if result.operation else None,
                "invocation_id": str(result.invocation_id),
                "outcome": result.outcome.value,
                "reason": result.reason.value,
                "actor": asdict(result.actor) if result.actor else None,
                "target": asdict(result.target) if result.target else None,
                "reference": result.data.reference if result.data else None,
                "version": result.data.version if result.data else None,
                # Failed operations can have no business data after their
                # separate attempt audit committed. Only explicit metadata
                # establishes an actual audit outage.
                "audit_status": (result.data or BusinessData()).audit_status,
            }
        )
        return result

    def call(operation, kind, identity, inputs=None, target_kind="entity"):
        result = invoke(operation, kind, identity, inputs, target_kind)
        if result.outcome != Outcome.SUCCESS:
            stopped(result)
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

    try:
        for item in package["definitions"]:
            definition = {"kind": item["kind"], "identity": item["identity"]}
            action = "resolve"
            fields(item, {"kind", "identity", "document"}, {"kind", "identity", "document"})
            kind, identity = item["kind"], item["identity"]
            document = resolve(copy.deepcopy(item["document"]))
            result = invoke("registry.history", kind, identity)
            if result.reason == Reason.NOT_FOUND:
                version = call(
                    "registry.create", kind, identity, {"document": document}
                ).version
                records = []
            elif result.outcome == Outcome.SUCCESS:
                records = result.data.records
                latest = max(
                    (x for x in records if x["record_type"] == "draft"),
                    key=lambda x: x["version"],
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
                    uncertain = True
                    raise SafeError(Reason.UNAVAILABLE)
            else:
                stopped(result)
            published = [
                x
                for x in records
                if x["record_type"] == "publication" and x["version"] == version
            ]
            if published:
                revision = published[0]["id"]
            else:
                call(
                    "registry.validate", kind, identity, {"expected_version": version}, "draft"
                )
                existing = [
                    x
                    for x in records
                    if x["record_type"] == "review" and x["version"] == version
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
                            "rationale": "Owner approved initial test configuration; "
                            "unprovisioned and unqualified; no execution authority.",
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
            receipt = {"kind": kind, "identity": identity, "revision": revision}
            receipts.append(receipt)
            publications.append(
                receipt | {"disposition": "reused" if published else "published"}
            )
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
    except PreparationStopped:
        raise
    except SafeError as error:
        stopped(OperationResult(uuid4(), None, Outcome.FAILURE, error.reason))
    except Exception:
        stopped(
            OperationResult(
                uuid4(),
                None,
                Outcome.UNCERTAIN if uncertain else Outcome.FAILURE,
                Reason.INTERNAL,
            )
        )

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
    available = set()
    for definition in package["definitions"]:
        fields(definition, {"kind", "identity", "document"}, {"kind", "identity", "document"})
        if not isinstance(definition["kind"], str) or definition["kind"] not in KINDS:
            raise SafeError(Reason.INVALID_INPUT)
        try:
            _token(definition["identity"])
        except ValueError:
            raise SafeError(Reason.INVALID_INPUT) from None
        fields(definition["document"], SCHEMAS[definition["kind"]])
        identity = f"{definition['kind']}:{definition['identity']}"
        if identity in available:
            raise SafeError(Reason.CONFLICT)

        def references(value):
            if isinstance(value, dict):
                if "published" in value:
                    if set(value) != {"published"} or not isinstance(value["published"], str):
                        raise SafeError(Reason.INVALID_INPUT)
                    if value["published"] not in available:
                        raise SafeError(Reason.NOT_FOUND)
                else:
                    for item in value.values():
                        references(item)
            elif isinstance(value, list):
                for item in value:
                    references(item)

        references(definition["document"])
        available.add(identity)


class PreparationStopped(SafeError):
    def __init__(self, result, receipts):
        self.result, self.receipts = result, receipts
        super().__init__(result.reason)


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
