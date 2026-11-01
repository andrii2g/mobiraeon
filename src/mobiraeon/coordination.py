"""Coordination-owned bounded workflow, using the shared transaction boundary."""

import json
import time
from dataclasses import asdict, replace
from functools import partial
from uuid import uuid4

from mobiraeon.access import Access, CurrentAccessPolicy, execute, one
from mobiraeon.contracts import (
    WORKFLOW_ACTIONS,
    BusinessData,
    BusinessTarget,
    Operation,
    OperationResult,
    Outcome,
    Owner,
)
from mobiraeon.coordination_schema import validate
from mobiraeon.errors import Reason, SafeError
from mobiraeon.operations import Binding, OperationBoundary
from mobiraeon.registry_schema import canonical, digest


def bindings():
    return {Operation.COORDINATION_WORK: Binding(Owner.COORDINATION, requires_target=True)}


def require(condition, reason=Reason.CONFLICT):
    if condition is not True:
        raise SafeError(reason)


def operation_fingerprint(operation, target, actor, inputs):
    return digest(
        {
            "action": operation.value,
            "target": asdict(target),
            "actor": asdict(actor),
            "inputs": inputs,
        }
    )


class Coordinator:
    def __init__(self, store, private, *, access=None, configuration_source=None):
        self.store = store
        self.access = access if access is not None else Access(store, private)
        # Trusted in-process composition only. Ordinary CLI has no simulation switch.
        self.configuration_source = configuration_source

    def invoke(self, code, target=None, inputs=None, *, proof=None):
        operation, caller = None, None
        invocation = uuid4()
        try:
            operation = Operation(code)
            if isinstance(target, dict):
                target = BusinessTarget(**target)
            validate(operation, target, inputs)
            self.store.check()
            caller = self.access.caller(proof)
            policy = CurrentAccessPolicy(self.access, proof)
            bound = {
                action: Binding(
                    Owner.COORDINATION,
                    partial(self._handle, action, caller, proof),
                    True,
                    True,
                    partial(validate, action),
                    True,
                )
                for action in WORKFLOW_ACTIONS
            }
            result = OperationBoundary(bound, policy, caller, self.store).invoke(
                operation, target=target, inputs=inputs
            )
        except ValueError, TypeError, KeyError:
            result = OperationResult(
                invocation, operation, Outcome.INVALID, Reason.INVALID_INPUT
            )
        except SafeError as error:
            outcome = (
                Outcome.INVALID
                if error.reason == Reason.INVALID_INPUT
                else Outcome.REFUSED
                if error.reason in {Reason.AUTHENTICATION, Reason.PROTECTION, Reason.REFUSED}
                else Outcome.UNAVAILABLE
            )
            result = OperationResult(
                invocation,
                operation,
                outcome,
                error.reason,
                caller.actor if caller else None,
            )
        except Exception:
            result = OperationResult(
                invocation,
                operation,
                Outcome.UNAVAILABLE,
                Reason.STORAGE_FAILURE,
                caller.actor if caller else None,
            )
        if result.outcome != Outcome.SUCCESS and caller is not None:
            try:
                with self.store.transaction() as tx:
                    self._history(
                        tx,
                        target.identity,
                        result.invocation_id,
                        caller.actor.value,
                        operation,
                        result.outcome,
                        {
                            "reason": result.reason.value,
                            "operation_id": inputs.get("operation_id"),
                            "fingerprint": operation_fingerprint(
                                operation, target, caller.actor, inputs
                            ),
                            "requires_inspection": result.outcome == Outcome.UNCERTAIN
                            and operation != Operation.STATUS,
                        },
                    )
            except Exception:
                result = replace(result, data=BusinessData(audit_status="unavailable"))
        return result

    def _history(self, tx, task, invocation, actor, operation, outcome, record):
        execute(
            tx,
            "INSERT INTO coordination_history(task,invocation,actor,operation,"
            "outcome,record) VALUES(:task,:invocation,:actor,:operation,:outcome,:record)",
            {
                "task": task,
                "invocation": str(invocation),
                "actor": actor,
                "operation": operation.value,
                "outcome": outcome.value,
                "record": canonical(record | {"at": int(time.time())}),
            },
        )

    def _fact(self, tx, task, stage):
        row = one(
            tx,
            "SELECT record FROM coordination_facts WHERE task=:task AND stage=:stage",
            {"task": task, "stage": stage},
        )
        require(row is not None, Reason.NOT_FOUND)
        return json.loads(row["record"])

    def _status(self, tx, task):
        row = one(tx, "SELECT * FROM coordination_tasks WHERE id=:task", {"task": task})
        facts = {
            r["stage"]: json.loads(r["record"])
            for r in execute(
                tx, "SELECT * FROM coordination_facts WHERE task=:task", {"task": task}
            ).mappings()
        }
        history = [
            dict(r) | {"record": json.loads(r["record"])}
            for r in execute(
                tx,
                "SELECT * FROM coordination_history WHERE task=:task ORDER BY sequence",
                {"task": task},
            ).mappings()
        ]
        unresolved_operations = self._unresolved(tx, task, history)
        require(row is not None or bool(unresolved_operations), Reason.NOT_FOUND)
        return (dict(row) if row else {"id": task, "version": None, "state": "unresolved"}) | {
            "facts": facts,
            "history": history,
            "request_state": "open",
            "initiative_acceptance": "unaccepted",
            "unresolved_operations": unresolved_operations,
            "unresolved": row is None
            or row["state"] == "unresolved"
            or bool(unresolved_operations),
        }

    def _unresolved(self, tx, task, history=None):
        if history is None:
            history = [
                dict(r) | {"record": json.loads(r["record"])}
                for r in execute(
                    tx, "SELECT * FROM coordination_history WHERE task=:task", {"task": task}
                ).mappings()
            ]
        return [
            r["record"]
            for r in history
            if r["record"].get("requires_inspection")
            and not self._matching_receipt(tx, task, r)
        ]

    def _matching_receipt(self, tx, task, uncertainty):
        receipt = one(
            tx,
            "SELECT * FROM coordination_receipts WHERE id=:id AND task=:task",
            {"id": uncertainty["record"].get("operation_id", ""), "task": task},
        )
        if receipt is None:
            return False
        fingerprint = uncertainty["record"].get("fingerprint")
        if fingerprint is not None:
            return receipt["fingerprint"] == fingerprint
        # Pre-repair history has no fingerprint. The original invocation's atomic
        # success record must bind this exact receipt, including its full inputs.
        success = one(
            tx,
            "SELECT record FROM coordination_history WHERE task=:task "
            "AND invocation=:invocation AND operation=:operation AND actor=:actor "
            "AND outcome='success'",
            {
                "task": task,
                "invocation": uncertainty["invocation"],
                "operation": uncertainty["operation"],
                "actor": uncertainty["actor"],
            },
        )
        if success is None:
            return False
        recorded = json.loads(success["record"])
        recorded.pop("at", None)
        return recorded == json.loads(receipt["record"])

    def _authority(self, tx, proof):
        row = self.access.authenticate(tx, proof)
        require(row is not None, Reason.REFUSED)
        return {"credential_id": row["id"], "credential_version": row["version"]}

    def _current(self, tx, authority, operation, target):
        row = one(
            tx,
            "SELECT * FROM access_credentials WHERE id=:id",
            {"id": authority["credential_id"]},
        )
        scopes = {"*", "task:*", "task:" + target.identity}
        require(
            row is not None
            and row["revoked"] is None
            and row["expires"] > int(self.access.clock())
            and any(
                g["action"] == operation.value and g["scope"] in scopes
                for g in json.loads(row["grants"])
            ),
            Reason.REFUSED,
        )

    def _resolve(self, tx, proof, configuration, work):
        for ref in configuration.values():
            target = BusinessTarget(
                "publication", ref["kind"], ref["identity"], ref["revision"]
            )
            require(
                self.access.permits(proof, Operation.REGISTRY_READ, target, tx), Reason.REFUSED
            )
        require(configuration["role"] == work["role"])
        if self.configuration_source is not None:
            return self.configuration_source.resolve(configuration)
        # Exact Registry reads retain scoped access even though execution is unavailable.
        documents = {}
        for name, ref in configuration.items():
            row = one(
                tx,
                "SELECT document FROM registry_publications WHERE id=:revision "
                "AND kind=:kind AND identity=:identity",
                ref,
            )
            require(row is not None, Reason.NOT_FOUND)
            documents[name] = json.loads(row["document"])
        require(documents["agent"]["profileRef"] == configuration["profile"])
        require(documents["profile"]["roleRef"] == configuration["role"])
        raise SafeError(Reason.UNAVAILABLE)

    def _handle(self, operation, caller, proof, tx, target, inputs, invocation):
        task, actor = target.identity, caller.actor.value
        if operation == Operation.STATUS:
            record = self._status(tx, task)
            record["current_authority"] = {
                "actor": asdict(caller.actor),
                "allowed_actions": sorted(
                    action.value
                    for action in WORKFLOW_ACTIONS
                    if self.access.permits(proof, action, target, tx) is True
                ),
            }
            return BusinessData((record,), reference=task, state="inspected")
        authority = self._authority(tx, proof)
        fingerprint = operation_fingerprint(operation, target, caller.actor, inputs)
        previous = one(
            tx,
            "SELECT * FROM coordination_receipts WHERE id=:id",
            {"id": inputs["operation_id"]},
        )
        if previous is not None:
            require(previous["fingerprint"] == fingerprint)
            record = json.loads(previous["record"])
            return BusinessData(
                (record | {"replayed": True},),
                reference=task,
                version=record["version"],
                state=record["state"],
            )
        require(not self._unresolved(tx, task), Reason.UNCERTAIN)
        stage = operation.value.split(".")[1]
        state = {
            "supply": "supplied",
            "allocate": "allocated",
            "dispatch": "unresolved",
            "observe": "observed",
            "submit": "submitted",
            "assess": "assessed",
            "accept": "accepted",
        }[stage]
        record = {
            "actor": actor,
            "actor_kind": caller.actor.kind,
            "authority": authority,
            "inputs": inputs,
            "task": task,
            "operation_id": inputs["operation_id"],
        }
        if operation == Operation.SUPPLY:
            require(
                one(tx, "SELECT id FROM coordination_tasks WHERE id=:task", {"task": task})
                is None
            )
            require(caller.actor.kind == "human", Reason.REFUSED)
            execute(
                tx, "INSERT INTO coordination_tasks VALUES(:task,1,'supplied')", {"task": task}
            )
            version = 1
        else:
            status = self._status(tx, task)
            require(status["version"] == inputs["expected_version"])
            require(stage not in status["facts"])
            work_fact = status["facts"]["supply"]
            work = work_fact["inputs"]["work"]
            author = work_fact["actor"]
            version = status["version"] + 1
            if operation in {
                Operation.ALLOCATE,
                Operation.DISPATCH,
                Operation.OBSERVE,
                Operation.SUBMIT,
            }:
                require(actor == author, Reason.REFUSED)
            if operation == Operation.ALLOCATE:
                require(status["state"] == "supplied")
                require(
                    one(
                        tx,
                        "SELECT id FROM coordination_tasks WHERE state IN "
                        "('allocated','unresolved')",
                    )
                    is None
                )
                snapshot = self._resolve(tx, proof, inputs["configuration"], work)
                record["snapshot"] = snapshot
                record["owner"] = actor
            elif operation in {Operation.DISPATCH, Operation.OBSERVE, Operation.SUBMIT}:
                assignment = self._fact(tx, task, "allocate")
                require(inputs["attempt_id"] == assignment["inputs"]["attempt_id"])
                require(actor == assignment["owner"], Reason.REFUSED)
                self._current(tx, assignment["authority"], Operation.ALLOCATE, target)
                if operation == Operation.DISPATCH:
                    require(status["state"] == "allocated")
                    require(
                        one(tx, "SELECT id FROM coordination_tasks WHERE state ='unresolved'")
                        is None
                    )
                    snapshot = self._resolve(
                        tx, proof, assignment["inputs"]["configuration"], work
                    )
                    require(snapshot == assignment["snapshot"])
                    record["effect"] = "reserved_outcome_unresolved"
                elif operation == Operation.OBSERVE:
                    require(status["state"] == "unresolved")
                    self._fact(tx, task, "dispatch")
                    if inputs["observation"] == "unknown":
                        state = "unresolved"
                else:
                    require(status["state"] == "observed")
                    observed = self._fact(tx, task, "observe")
                    require(observed["inputs"]["observation"] == "succeeded")
                    present = {a["identity"] for a in inputs["artifacts"]}
                    require(set(work["deliverables"]) <= present, Reason.INCOMPLETE)
                    require(
                        {c["evidence"] for c in work["criteria"].values()} <= present,
                        Reason.INCOMPLETE,
                    )
                    for artifact in inputs["artifacts"]:
                        for original in work["inputs"]:
                            if (original["identity"], original["revision"]) == (
                                artifact["identity"],
                                artifact["revision"],
                            ):
                                require(original == artifact)
                    record["contract_digest"] = digest(work_fact)
                    record["submission_digest"] = digest(record)
            else:
                submission = self._fact(tx, task, "submit")
                require(inputs["submission_id"] == submission["inputs"]["submission_id"])
                require(
                    inputs["submission_digest"] == submission["submission_digest"],
                    Reason.REVIEW,
                )
                require(submission["contract_digest"] == digest(work_fact), Reason.REVIEW)
                require(caller.actor.kind == "human" and actor != author, Reason.REVIEW)
                if operation == Operation.ASSESS:
                    require(status["state"] == "submitted")
                    require(
                        inputs["evidence"] == submission["inputs"]["artifacts"], Reason.REVIEW
                    )
                else:
                    require(status["state"] == "assessed")
                    assessment = self._fact(tx, task, "assess")
                    require(
                        inputs["assessment_id"] == assessment["operation_id"], Reason.REVIEW
                    )
                    require(
                        assessment["actor"] != author and assessment["actor_kind"] == "human",
                        Reason.REVIEW,
                    )
                    require(assessment["inputs"]["decision"] == "approve", Reason.REVIEW)
                    require(
                        assessment["inputs"]["submission_digest"]
                        == submission["submission_digest"],
                        Reason.REVIEW,
                    )
                    require(
                        assessment["inputs"]["evidence"] == submission["inputs"]["artifacts"],
                        Reason.REVIEW,
                    )
                    self._current(tx, assessment["authority"], Operation.ASSESS, target)
            execute(
                tx,
                "UPDATE coordination_tasks SET version=:version,state=:state WHERE id=:task",
                {"version": version, "state": state, "task": task},
            )
        identity = inputs.get("attempt_id") if operation == Operation.ALLOCATE else None
        # Globally unique attempt IDs; all other stage IDs are operation identities.
        identity = "attempt:" + identity if identity else "operation:" + inputs["operation_id"]
        execute(
            tx,
            "INSERT INTO coordination_facts VALUES(:task,:stage,:identity,:record)",
            {"task": task, "stage": stage, "identity": identity, "record": canonical(record)},
        )
        receipt = {
            "task": task,
            "version": version,
            "state": state,
            "fact": record,
            "replayed": False,
        }
        execute(
            tx,
            "INSERT INTO coordination_receipts VALUES(:id,:task,:fingerprint,:record)",
            {
                "id": inputs["operation_id"],
                "task": task,
                "fingerprint": fingerprint,
                "record": canonical(receipt),
            },
        )
        self._history(tx, task, invocation, actor, operation, Outcome.SUCCESS, receipt)
        return BusinessData((receipt,), reference=task, version=version, state=state)
