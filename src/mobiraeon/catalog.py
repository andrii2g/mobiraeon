"""Registry-owned records and exact publication semantics, with no execution path."""

import json
from contextlib import ExitStack
from dataclasses import asdict, replace
from functools import partial
from uuid import uuid4

from mobiraeon.access import Access, CredentialProof, CurrentAccessPolicy, audit, execute, one
from mobiraeon.contracts import (
    BusinessData,
    BusinessTarget,
    Operation,
    OperationResult,
    Outcome,
    Owner,
)
from mobiraeon.errors import Reason, SafeError
from mobiraeon.operations import Binding, OperationBoundary
from mobiraeon.registry_schema import (
    ACCESS_ACTIONS,
    CATALOG_ACTIONS,
    canonical,
    digest,
    validate_document,
    validate_request,
)


def target_record(target):
    return asdict(target) if isinstance(target, BusinessTarget) else None


class RegistryService:
    def __init__(self, store, private, *, clock=None):
        self.store, self.private = store, private
        self.access = Access(store, private, **({"clock": clock} if clock else {}))

    def invoke(self, code, target=None, inputs=None, *, proof=None):
        """No shared caller field: proof/context/bindings live only for this call."""
        invocation = uuid4()
        operation = None
        caller = None
        delivered = None
        lifecycle = ExitStack()
        result = OperationResult(invocation, None, Outcome.UNCERTAIN, Reason.INTERNAL)
        try:
            operation = Operation(code)
            if isinstance(target, dict):
                target = BusinessTarget(**target)
            validate_request(operation, target, inputs)
            self.store.check()
            caller = self.access.caller(proof)
            policy = CurrentAccessPolicy(self.access, proof)
            # Delivery never precedes an initial grant. Current grant is still
            # rechecked inside registration after all filesystem work is finished.
            if caller is not None and operation in {
                Operation.SETUP,
                Operation.RECOVER,
                Operation.ISSUE,
                Operation.ROTATE,
            }:
                if policy.permits(caller, operation, target) is True:
                    lifecycle.enter_context(self.private.credential_lifecycle())
                    if operation == Operation.SETUP:
                        with self.store.engine.connect() as connection:
                            if one(connection, "SELECT id FROM access_installation"):
                                raise SafeError(Reason.CONFLICT)
                    delivered = self.access.deliver(inputs)
            bindings = {
                action: Binding(
                    Owner.ACCESS
                    if action in ACCESS_ACTIONS | {Operation.SETUP, Operation.RECOVER}
                    else Owner.REGISTRY,
                    partial(self._handle, action, proof, caller, delivered),
                    True,
                    True,
                    partial(validate_request, action),
                    True,
                )
                for action in CATALOG_ACTIONS
                | ACCESS_ACTIONS
                | {Operation.SETUP, Operation.RECOVER}
            }
            result = OperationBoundary(bindings, policy, caller, self.store).invoke(
                operation, target=target, inputs=inputs
            )
            if caller is None and result.outcome == Outcome.REFUSED:
                result = replace(result, reason=Reason.AUTHENTICATION)
        except ValueError, TypeError, KeyError:
            result = OperationResult(
                invocation, operation, Outcome.INVALID, Reason.INVALID_INPUT
            )
        except SafeError as error:
            outcome = Outcome.FAILURE
            if error.reason == Reason.INVALID_INPUT:
                outcome = Outcome.INVALID
            elif error.reason in {Reason.AUTHENTICATION, Reason.PROTECTION}:
                outcome = Outcome.REFUSED
            elif error.reason == Reason.UNAVAILABLE:
                outcome = Outcome.UNAVAILABLE
            result = OperationResult(
                invocation,
                operation,
                outcome,
                error.reason,
                caller.actor if caller else None,
            )
        except Exception:
            # No handler has been entered on these construction/authentication paths.
            result = OperationResult(
                invocation, operation, Outcome.UNAVAILABLE, Reason.STORAGE_FAILURE
            )
        finally:
            try:
                lifecycle.close()
            except Exception:
                # Registration may have committed; finalization cannot claim success.
                result = replace(
                    result, outcome=Outcome.UNCERTAIN, reason=Reason.CLEANUP_FAILED
                )
        if result.outcome != Outcome.SUCCESS:
            result = self._attempt_audit(result)
        if delivered is not None and result.outcome != Outcome.SUCCESS:
            data = result.data or BusinessData()
            result = replace(
                result,
                data=replace(
                    data,
                    reference=delivered.identifier,
                    state="delivery_saved_registration_requires_reconciliation",
                ),
            )
        return result

    def _attempt_audit(self, result):
        try:
            with self.store.transaction() as tx:
                audit(
                    tx,
                    result.invocation_id,
                    result.operation,
                    result.actor.value if result.actor else None,
                    target_record(result.target),
                    result.outcome,
                    result.reason,
                )
        except Exception:
            return replace(result, data=BusinessData(audit_status="unavailable"))
        return result

    def _handle(self, operation, proof, caller, delivered, tx, target, inputs, invocation):
        authority = (
            self.access.authenticate(tx, proof) if isinstance(proof, CredentialProof) else None
        )
        if operation in ACCESS_ACTIONS | {Operation.SETUP, Operation.RECOVER}:
            if operation == Operation.ACCESS_RECONCILE:
                record = self.access.reconcile(tx, target.identity)
            else:
                record = self.access.mutate(tx, operation, target, inputs, proof, delivered)
            data = BusinessData(
                (record,),
                reference=record.get("credential_id"),
                version=record.get("version"),
                state=record.get("state"),
            )
        else:
            data = self._catalog(tx, operation, target, inputs, caller.actor.value)
        audit_record = asdict(data)
        if operation in {
            Operation.REGISTRY_READ,
            Operation.HISTORY,
            Operation.RECONCILE,
            Operation.ACCESS_RECONCILE,
        }:
            audit_record.pop("records", None)
        if isinstance(proof, CredentialProof):
            audit_record["authority"] = {
                "credential_id": proof.identifier,
                "credential_version": authority["version"],
            }
        else:
            audit_record["authority"] = {"proof": "protected_os_owner"}
        audit(
            tx,
            invocation,
            operation,
            caller.actor.value,
            target_record(target),
            Outcome.SUCCESS,
            Reason.OK,
            audit_record,
        )
        return data

    def _draft(self, tx, target, expected=None):
        row = one(
            tx,
            "SELECT * FROM registry_drafts WHERE kind=:kind AND identity=:identity "
            "ORDER BY version DESC LIMIT 1",
            {"kind": target.entity_kind, "identity": target.identity},
        )
        if row is None:
            raise SafeError(Reason.NOT_FOUND)
        if expected is not None and row["version"] != expected:
            raise SafeError(Reason.CONFLICT)
        return row

    def _publication(self, tx, reference):
        row = one(
            tx,
            "SELECT * FROM registry_publications WHERE id=:revision "
            "AND kind=:kind AND identity=:identity",
            reference,
        )
        if row is None:
            raise SafeError(Reason.NOT_FOUND)
        return row

    def _validate(self, tx, kind, document):
        dependencies = validate_document(kind, document, complete=True)
        resolved = {
            dep["revision"]: json.loads(self._publication(tx, dep)["document"])
            for dep in dependencies
        }
        if kind == "agent":
            profile = resolved[document["profileRef"]["revision"]]
            for name, value in document["overrides"].items():
                if value > profile["limits"][name]:
                    raise SafeError(Reason.INVALID_INPUT)
        if kind == "profile":
            runtime = document["runtime"]
            for cap_ref in (runtime["capabilityRef"], document["capabilityRequirementsRef"]):
                cap = resolved[cap_ref["revision"]]
                if (
                    cap["runtime"] != runtime["name"] + "@" + runtime["version"]
                    or cap["provider"] != document["provider"]
                    or document["model"] not in cap["models"]
                    or document["reasoning"] not in cap["reasoning"]
                ):
                    raise SafeError(Reason.INVALID_INPUT)
                for setting, declaration in (
                    ("runtimeOptions", "runtime_options"),
                    ("providerOptions", "provider_options"),
                ):
                    for name, value in document[setting].items():
                        if name not in cap[declaration] or not any(
                            type(value) is type(x) and value == x
                            for x in cap[declaration][name]
                        ):
                            raise SafeError(Reason.INVALID_INPUT)
            for setting, policy_type in (
                ("toolPolicyRef", "tool"),
                ("authorityPolicyRef", "authority"),
                ("fallbackPolicyRef", "fallback"),
            ):
                if (
                    setting in document
                    and resolved[document[setting]["revision"]]["policy_type"] != policy_type
                ):
                    raise SafeError(Reason.INVALID_INPUT)
            connection = resolved[document["providerConnectionRef"]["revision"]]
            if connection["credentialRef"] not in document["secretRefs"]:
                raise SafeError(Reason.INVALID_INPUT)
        return dependencies

    def _catalog(self, tx, operation, target, inputs, actor):
        values = {"kind": target.entity_kind, "identity": target.identity}
        expected = inputs.get("expected_version")
        if operation == Operation.CREATE:
            if one(
                tx,
                "SELECT * FROM registry_entities WHERE kind=:kind AND identity=:identity",
                values,
            ):
                raise SafeError(Reason.CONFLICT)
            execute(tx, "INSERT INTO registry_entities VALUES(:kind,:identity)", values)
            if target.entity_kind == "agent":
                execute(
                    tx, "INSERT INTO registry_controls VALUES(:kind,:identity,1,NULL,0)", values
                )
            version = 1
        elif operation in {Operation.EDIT, Operation.DISCARD}:
            previous = self._draft(tx, target, expected)
            version = previous["version"] + 1
        else:
            version = None
        if version is not None:
            document = inputs.get(
                "document",
                json.loads(previous["document"]) if operation == Operation.DISCARD else {},
            )
            execute(
                tx,
                "INSERT INTO registry_drafts VALUES(:kind,:identity,:ver"
                "sion,:document,:digest,:author,:discarded)",
                values
                | {
                    "version": version,
                    "document": canonical(document),
                    "digest": digest(document),
                    "author": actor,
                    "discarded": operation == Operation.DISCARD,
                },
            )
            return BusinessData(
                reference=f"{target.entity_kind}:{target.identity}",
                version=version,
                state="discarded" if operation == Operation.DISCARD else "draft",
            )
        if operation in {Operation.VALIDATE, Operation.REVIEW, Operation.PUBLISH}:
            draft = self._draft(tx, target, expected)
            if draft["discarded"]:
                raise SafeError(Reason.INCOMPLETE)
            document = json.loads(draft["document"])
            dependencies = self._validate(tx, target.entity_kind, document)
            if operation == Operation.VALIDATE:
                return BusinessData(version=draft["version"], state="valid_unqualified")
            if operation == Operation.REVIEW:
                installation = one(tx, "SELECT self_review FROM access_installation WHERE id=1")
                if draft["author"] == actor and not installation["self_review"]:
                    raise SafeError(Reason.REFUSED)
                review = "review_" + uuid4().hex
                execute(
                    tx,
                    "INSERT INTO registry_reviews VALUES(:id,:kind,:identity"
                    ",:version,:digest,:reviewer,:rationale)",
                    values
                    | {
                        "id": review,
                        "version": draft["version"],
                        "digest": draft["digest"],
                        "reviewer": actor,
                        "rationale": inputs["rationale"],
                    },
                )
                return BusinessData(
                    reference=review, version=draft["version"], state="reviewed"
                )
            review = one(
                tx, "SELECT * FROM registry_reviews WHERE id=:id", {"id": inputs["review_id"]}
            )
            if review is None or any(
                review[key] != draft[key] for key in ("kind", "identity", "version", "digest")
            ):
                raise SafeError(Reason.REVIEW)
            if one(
                tx,
                "SELECT id FROM registry_publications WHERE kind=:kind A"
                "ND identity=:identity AND version=:version",
                values | {"version": draft["version"]},
            ):
                raise SafeError(Reason.CONFLICT)
            revision = "r_" + uuid4().hex
            execute(
                tx,
                "INSERT INTO registry_publications VALUES(:id,:kind,:ide"
                "ntity,:version,:review,:document,:digest)",
                values
                | {
                    "id": revision,
                    "version": draft["version"],
                    "review": review["id"],
                    "document": draft["document"],
                    "digest": draft["digest"],
                },
            )
            for dependency in {dep["revision"] for dep in dependencies}:
                execute(
                    tx,
                    "INSERT INTO registry_dependencies VALUES(:publication,:dependency)",
                    {"publication": revision, "dependency": dependency},
                )
            return BusinessData(
                reference=revision, version=draft["version"], state="published_unqualified"
            )
        if (
            operation in {Operation.SELECT, Operation.ENABLE, Operation.DISABLE}
            or target.kind == "control"
        ):
            control = one(
                tx,
                "SELECT * FROM registry_controls WHERE kind=:kind AND identity=:identity",
                values,
            )
            if control is None:
                raise SafeError(Reason.NOT_FOUND)
            if operation != Operation.REGISTRY_READ:
                if control["version"] != expected:
                    raise SafeError(Reason.CONFLICT)
                if operation == Operation.ENABLE:
                    raise SafeError(
                        Reason.UNAVAILABLE
                    )  # No production positive qualification path.
                if operation == Operation.SELECT:
                    self._publication(tx, values | {"revision": inputs["revision"]})
                    execute(
                        tx,
                        "UPDATE registry_controls SET selected=:revision,version"
                        "=version+1 WHERE kind=:kind AND identity=:identity",
                        values | {"revision": inputs["revision"]},
                    )
                else:
                    execute(
                        tx,
                        "UPDATE registry_controls SET enabled=0,version=version+"
                        "1 WHERE kind=:kind AND identity=:identity",
                        values,
                    )
                control = one(
                    tx,
                    "SELECT * FROM registry_controls WHERE kind=:kind AND identity=:identity",
                    values,
                )
            record = dict(control) | {
                "enabled": bool(control["enabled"]),
                "qualification": "unavailable",
                "execution_eligible": False,
            }
            return BusinessData((record,), version=control["version"], state="current_control")
        if operation == Operation.RECONCILE:
            rows = (
                execute(
                    tx,
                    "SELECT invocation,operation,actor,target,outcome,reason"
                    ",record,at FROM registry_audit WHERE invocation=:invoca"
                    "tion ORDER BY id",
                    {"invocation": target.identity},
                )
                .mappings()
                .all()
            )
            return BusinessData(
                tuple(dict(row) for row in rows),
                state="observed" if rows else "uncertain_no_evidence",
            )
        if operation == Operation.REGISTRY_READ and target.kind == "publication":
            row = self._publication(tx, values | {"revision": target.revision})
            return BusinessData(
                (self._public_record(row),), reference=row["id"], version=row["version"]
            )
        if operation == Operation.REGISTRY_READ and target.kind == "draft":
            row = self._draft(tx, target)
            return BusinessData((self._public_record(row),), version=row["version"])
        if operation in {Operation.REGISTRY_READ, Operation.HISTORY}:
            if not one(
                tx,
                "SELECT * FROM registry_entities WHERE kind=:kind AND identity=:identity",
                values,
            ):
                raise SafeError(Reason.NOT_FOUND)
            drafts = execute(
                tx,
                "SELECT * FROM registry_drafts WHERE kind=:kind AND iden"
                "tity=:identity ORDER BY version",
                values,
            ).mappings()
            publications = execute(
                tx,
                "SELECT * FROM registry_publications WHERE kind=:kind AN"
                "D identity=:identity ORDER BY version",
                values,
            ).mappings()
            history = [self._public_record(row) | {"record_type": "draft"} for row in drafts]
            history += [
                self._public_record(row) | {"record_type": "publication"}
                for row in publications
            ]
            if operation == Operation.HISTORY:
                reviews = execute(
                    tx,
                    "SELECT id,version,digest,reviewer,rationale FROM registry_reviews "
                    "WHERE kind=:kind AND identity=:identity",
                    values,
                ).mappings()
                history += [dict(row) | {"record_type": "review"} for row in reviews]
                events = execute(
                    tx,
                    "SELECT invocation,operation,outcome,reason,record FROM registry_audit "
                    "WHERE json_extract(target,'$.entity_kind')=:kind "
                    "AND json_extract(target,'$.identity')=:identity ORDER BY id",
                    values,
                ).mappings()
                history += [dict(row) | {"record_type": "audit"} for row in events]
            return BusinessData(tuple(history))
        raise SafeError(Reason.INVALID_INPUT)

    @staticmethod
    def _public_record(row):
        return {
            key: json.loads(value) if key == "document" else value
            for key, value in row.items()
            if key
            in {
                "id",
                "kind",
                "identity",
                "version",
                "document",
                "author",
                "discarded",
                "review",
                "digest",
            }
        }
