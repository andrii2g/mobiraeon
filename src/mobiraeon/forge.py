"""Bounded manual forge bridge. Registry configuration and Coordination evidence.

External work always runs outside SQL transactions. An armed intent is never resent.
The OS guard excludes cooperating processes; immutable intents fence crash recovery.
"""

import asyncio
import hashlib
import json
import time
from dataclasses import asdict, replace
from datetime import UTC, datetime
from functools import partial
from uuid import uuid4

from mobiraeon.access import Access, CurrentAccessPolicy, execute, one
from mobiraeon.contracts import (
    FORGE_ACTIONS,
    BusinessData,
    BusinessTarget,
    Operation,
    OperationResult,
    Outcome,
    Owner,
)
from mobiraeon.coordination import operation_fingerprint, require
from mobiraeon.errors import Reason, RecordedForgeFailure, SafeError
from mobiraeon.forge_adapter import Gitea
from mobiraeon.forge_credentials import read_token
from mobiraeon.forge_lock import guard, signals
from mobiraeon.forge_schema import connection, validate
from mobiraeon.operations import Binding, OperationBoundary
from mobiraeon.registry_schema import canonical, digest


def identity(prefix):
    return prefix + "_" + uuid4().hex


def sha(body):
    return hashlib.sha256(body.encode()).hexdigest()


def row(tx, table, key, value):
    return one(tx, f"SELECT * FROM {table} WHERE {key}=:value", {"value": value})


def insert(tx, table, **values):
    execute(
        tx,
        f"INSERT INTO {table} ({','.join(values)}) VALUES "
        f"({','.join(':' + key for key in values)})",
        values,
    )


class ForgeService:
    def __init__(self, store, private, *, access=None, adapter=Gitea, fault=None):
        self.store, self.private = store, private
        self.access = access or Access(store, private)
        self.adapter = adapter
        # Trusted deterministic test seam, never request/config selectable.
        self.fault = fault or (lambda phase: None)

    def invoke(self, code, target=None, inputs=None, *, proof=None):
        invocation, operation, caller = uuid4(), None, None
        try:
            operation = Operation(code)
            if isinstance(target, dict):
                target = BusinessTarget(**target)
            validate(operation, target, inputs)
            self.store.check()
            caller = self.access.caller(proof)
            bindings = {
                action: Binding(
                    Owner.FORGE,
                    partial(self._handle, action, caller, proof),
                    False,
                    True,
                    partial(validate, action),
                    True,
                )
                for action in FORGE_ACTIONS
            }
            result = OperationBoundary(
                bindings, CurrentAccessPolicy(self.access, proof), caller, self.store
            ).invoke(operation, target=target, inputs=inputs)
        except ValueError, TypeError, KeyError:
            result = OperationResult(
                invocation, operation, Outcome.INVALID, Reason.INVALID_INPUT
            )
        except SafeError as error:
            result = OperationResult(
                invocation,
                operation,
                Outcome.INVALID
                if error.reason == Reason.INVALID_INPUT
                else Outcome.UNAVAILABLE,
                error.reason,
            )
        except Exception:
            result = OperationResult(
                invocation, operation, Outcome.UNAVAILABLE, Reason.UNAVAILABLE
            )
        if result.outcome != Outcome.SUCCESS and caller is not None:
            try:
                with self.store.transaction() as tx:
                    self._history(
                        tx,
                        target.identity,
                        None,
                        result.invocation_id,
                        caller,
                        "attempt",
                        inputs.get("operation_id"),
                        result.outcome,
                        {
                            "reason": result.reason.value,
                            "task": inputs.get("task_id"),
                            "fingerprint": operation_fingerprint(
                                operation, target, caller.actor, inputs
                            ),
                        },
                    )
            except Exception:
                result = replace(result, data=BusinessData(audit_status="unavailable"))
        return result

    def _authorize(self, tx, operation, target, inputs, proof):
        require(self.access.permits(proof, operation, target, tx) is True, Reason.REFUSED)
        task = inputs.get("task_id")
        if task:
            task_target = BusinessTarget("entity", "task", task)
            require(
                self.access.permits(proof, Operation.STATUS, task_target, tx) is True,
                Reason.REFUSED,
            )
            fact = one(
                tx,
                "SELECT record FROM coordination_facts WHERE task=:task AND stage='supply'",
                {"task": task},
            )
            require(fact is not None, Reason.NOT_FOUND)
            require(
                json.loads(fact["record"])["inputs"]["work"]["project"] == target.identity,
                Reason.REFUSED,
            )

    def _history(self, tx, project, link, invocation, caller, kind, reference, outcome, record):
        insert(
            tx,
            "forge_history",
            at=datetime.now(UTC).isoformat(),
            project=project,
            link=link,
            invocation=str(invocation),
            actor=caller.actor.value,
            kind=kind,
            reference=reference,
            outcome=outcome.value,
            record=canonical(record),
        )

    def _complete(
        self,
        tx,
        request,
        state,
        reference,
        version,
        record=None,
        outcome=Outcome.SUCCESS,
        reason=Reason.OK,
    ):
        data = BusinessData((record,) if record is not None else (), reference, version, state)
        encoded = canonical(asdict(data))
        require(len(encoded.encode()) <= 65536, Reason.UNAVAILABLE)
        insert(
            tx,
            "forge_receipts",
            id=request,
            result=canonical(
                {"outcome": outcome.value, "reason": reason.value, "data": asdict(data)}
            ),
        )
        return data

    def _replay(self, tx, operation, target, inputs, caller):
        request = inputs.get("operation_id")
        if not request:
            return None
        existing = row(tx, "forge_requests", "id", request)
        if not existing:
            attempt = one(
                tx,
                "SELECT outcome,record FROM forge_history WHERE kind='attempt' "
                "AND reference=:request ORDER BY sequence LIMIT 1",
                {"request": request},
            )
            if attempt:
                record = json.loads(attempt["record"])
                require(
                    record.get("fingerprint")
                    == operation_fingerprint(operation, target, caller.actor, inputs)
                )
                raise RecordedForgeFailure(Reason(record["reason"]), attempt["outcome"])
        if existing:
            require(
                existing["fingerprint"]
                == operation_fingerprint(operation, target, caller.actor, inputs)
            )
            receipt = row(tx, "forge_receipts", "id", request)
            if not receipt:
                raise SafeError(Reason.UNCERTAIN)
            result = json.loads(receipt["result"])
            if result["outcome"] != Outcome.SUCCESS:
                raise RecordedForgeFailure(Reason(result["reason"]), result["outcome"])
            return BusinessData(
                **(result["data"] | {"records": tuple(result["data"]["records"])})
            )
        return None

    def _reserve(self, tx, operation, target, inputs, caller):
        insert(
            tx,
            "forge_requests",
            id=inputs["operation_id"],
            fingerprint=operation_fingerprint(operation, target, caller.actor, inputs),
            project=target.identity,
            task=inputs.get("task_id"),
            actor=caller.actor.value,
            operation=operation.value,
        )

    def _connection(self, tx, project, revision=None, *, current=True):
        head = row(tx, "forge_connections", "project", project)
        require(head is not None, Reason.NOT_FOUND)
        if revision and current:
            require(head["revision"] == revision)
        retained = row(tx, "forge_revisions", "id", revision or head["revision"])
        require(retained is not None and retained["connection"] == head["id"], Reason.NOT_FOUND)
        return dict(head), json.loads(retained["definition"]), dict(retained)

    def _link(self, tx, task, project):
        link = row(tx, "forge_links", "task", task)
        require(link is not None, Reason.NOT_FOUND)
        require(link["project"] == project, Reason.REFUSED)
        return dict(link)

    def _pending(self, tx, link):
        return one(
            tx,
            "SELECT i.*, s.state, s.generation FROM forge_intents i "
            "JOIN forge_intent_state s ON s.id=i.id WHERE i.link=:link "
            "AND s.state IN ('prepared','armed','uncertain')",
            {"link": link},
        )

    def _handle(self, operation, caller, proof, _, target, inputs, invocation):
        with self.store.engine.connect() as tx:
            self._authorize(tx, operation, target, inputs, proof)
            replay = self._replay(tx, operation, target, inputs, caller)
            if replay:
                return replay
            if operation == Operation.FORGE_READ:
                head, definition, revision = self._connection(
                    tx, target.identity, inputs.get("connection_revision"), current=False
                )
                return BusinessData(
                    (
                        dict(
                            connection_id=head["id"],
                            current_version=head["version"],
                            current_revision=head["revision"],
                            connection_revision=revision["id"],
                            revision_version=revision["version"],
                            definition=definition,
                            currently_verified=False,
                            permitted_actions=self._permitted(tx, target, proof),
                        ),
                    ),
                    reference=revision["id"],
                    version=revision["version"],
                    state="inspected",
                )
            if operation == Operation.FORGE_STATUS:
                return self._status(tx, target, inputs, proof)
        if operation == Operation.FORGE_CONFIGURE:
            return self._configure(operation, caller, proof, target, inputs, invocation)
        with signals() as interruption, guard(self.private, inputs["task_id"]):
            # Recheck after lock acquisition, including exact concurrent receipt.
            with self.store.engine.connect() as tx:
                self._authorize(tx, operation, target, inputs, proof)
                replay = self._replay(tx, operation, target, inputs, caller)
                if replay:
                    return replay
            if operation == Operation.FORGE_RESOLVE:
                return self._resolve(operation, caller, proof, target, inputs, invocation)
            result = asyncio.run(
                self._foreground(
                    self._network(
                        operation, caller, proof, target, inputs, invocation, interruption
                    ),
                    interruption,
                )
            )
            with self.store.engine.connect() as tx:
                self._authorize(tx, operation, target, inputs, proof)
            return result

    async def _foreground(self, cycle, interruption):
        task = asyncio.create_task(cycle)
        cancellation_requested = False
        while not task.done():
            if interruption.pending and not cancellation_requested:
                cancellation_requested = True
                task.cancel()
            await asyncio.wait({task}, timeout=0.05)
        try:
            return await task
        except asyncio.CancelledError:
            raise SafeError(Reason.UNCERTAIN) from None

    def _permitted(self, tx, target, proof):
        return [
            a.value
            for a in sorted(FORGE_ACTIONS)
            if self.access.permits(proof, a, target, tx) is True
        ]

    def _status(self, tx, target, inputs, proof):
        link = self._link(tx, inputs["task_id"], target.identity)
        pending = self._pending(tx, link["id"])
        history = [
            dict(r)
            for r in execute(
                tx,
                "SELECT sequence,at,kind,reference,outcome "
                "FROM forge_history WHERE link=:link OR (link IS NULL AND project=:project "
                "AND json_extract(record,'$.task')=:task) ORDER BY sequence DESC LIMIT 21",
                {"link": link["id"], "project": target.identity, "task": inputs["task_id"]},
            ).mappings()
        ]
        record = {
            key: link[key]
            for key in (
                "id",
                "task",
                "project",
                "connection",
                "revision",
                "version",
                "comment",
                "conflict",
                "approval",
            )
        }
        record |= {
            "last_observed": json.loads(link["observation"]) if link["observation"] else None,
            "last_confirmed_publication": json.loads(link["publication"])
            if link["publication"]
            else None,
            "currently_verified": False,
            "pending_intent": {"id": pending["id"], "state": pending["state"]}
            if pending
            else None,
            "history": history[:20],
            "history_has_more": len(history) > 20,
            "permitted_actions": self._permitted(tx, target, proof),
        }
        require(len(canonical(record).encode()) < 64000, Reason.UNAVAILABLE)
        return BusinessData((record,), link["id"], link["version"], "inspected")

    def _configure(self, operation, caller, proof, target, inputs, invocation):
        definition = connection(inputs["connection"])
        with self.store.transaction() as tx:
            self._authorize(tx, operation, target, inputs, proof)
            replay = self._replay(tx, operation, target, inputs, caller)
            if replay:
                return replay
            head = row(tx, "forge_connections", "project", target.identity)
            require(inputs["expected_version"] == (head["version"] if head else 0))
            if head:
                _, previous, _ = self._connection(tx, target.identity)
                if previous["credential"] != definition["credential"]:
                    require(
                        previous["credential"]["name"] != definition["credential"]["name"]
                        and previous["credential"]["revision"]
                        != definition["credential"]["revision"]
                    )
                if row(tx, "forge_links", "project", target.identity):
                    require(
                        all(previous[key] == definition[key] for key in ("provider", "origin"))
                        and previous["repository"]["id"] == definition["repository"]["id"]
                        and previous["account"]["id"] == definition["account"]["id"]
                    )
            self._reserve(tx, operation, target, inputs, caller)
            cid = head["id"] if head else identity("fc")
            revision, version = identity("fcr"), head["version"] + 1 if head else 1
            if not head:
                insert(
                    tx,
                    "forge_connections",
                    project=target.identity,
                    id=cid,
                    version=version,
                    revision=revision,
                )
            insert(
                tx,
                "forge_revisions",
                id=revision,
                connection=cid,
                version=version,
                definition=canonical(definition),
                sha256=digest(definition),
                actor=caller.actor.value,
                request=inputs["operation_id"],
            )
            execute(
                tx,
                "UPDATE forge_connections SET version=:version,revision=:revision "
                "WHERE project=:project",
                dict(version=version, revision=revision, project=target.identity),
            )
            self._history(
                tx,
                target.identity,
                None,
                invocation,
                caller,
                "configured",
                revision,
                Outcome.SUCCESS,
                {"version": version},
            )
            return self._complete(tx, inputs["operation_id"], "configured", revision, version)

    def _resolve(self, operation, caller, proof, target, inputs, invocation):
        with self.store.transaction() as tx:
            self._authorize(tx, operation, target, inputs, proof)
            link = self._link(tx, inputs["task_id"], target.identity)
            require(link["version"] == inputs["expected_version"])
            require(self._pending(tx, link["id"]) is None, Reason.UNCERTAIN)
            require(link["conflict"] == inputs["conflict_id"])
            conflict = row(tx, "forge_conflicts", "id", link["conflict"])
            observed = json.loads(conflict["record"])
            require(
                inputs["action"] == ("replace" if observed["kind"] == "deleted" else "refresh")
            )
            self._reserve(tx, operation, target, inputs, caller)
            approval, version = identity("approval"), link["version"] + 1
            insert(
                tx,
                "forge_approvals",
                id=approval,
                conflict=conflict["id"],
                link=link["id"],
                version=version,
                record=canonical(
                    {"actor": asdict(caller.actor), "inputs": inputs, "observation": observed}
                ),
            )
            execute(
                tx,
                "UPDATE forge_links SET version=:v,approval=:a WHERE id=:id",
                dict(v=version, a=approval, id=link["id"]),
            )
            self._history(
                tx,
                target.identity,
                link["id"],
                invocation,
                caller,
                "approval_recorded",
                approval,
                Outcome.SUCCESS,
                {"conflict": conflict["id"]},
            )
            return self._complete(
                tx, inputs["operation_id"], "approval_recorded", approval, version
            )

    def _projection(self, tx, task):
        head = row(tx, "coordination_tasks", "id", task)
        facts = {
            r["stage"]: json.loads(r["record"])
            for r in execute(
                tx,
                "SELECT stage,record FROM coordination_facts WHERE task=:task",
                {"task": task},
            ).mappings()
        }
        projection = {
            "task": task,
            "task_version": head["version"],
            "state": head["state"],
            "attempt": None,
            "result": None,
            "evidence": [],
        }
        if "allocate" in facts:
            projection["attempt"] = facts["allocate"]["inputs"]["attempt_id"]
        if "observe" in facts:
            projection["result"] = facts["observe"]["inputs"]["observation"]
        for stage, key in (("supply", "inputs"), ("submit", "artifacts")):
            value = facts.get(stage, {}).get("inputs", {})
            artifacts = (
                value.get("work", {}).get("inputs", [])
                if stage == "supply"
                else value.get(key, [])
            )
            for artifact in artifacts:
                projection["evidence"].append(
                    {k: artifact[k] for k in ("identity", "revision", "sha256")}
                )
        return projection

    def _render(self, installation, link, intent, facts):
        # Only validated ASCII IDs/enums/numbers/hashes enter this projection. No freeform
        # Task text, remote human content, paths or inline artifact bytes are rendered.
        lines = [
            f"<!-- mobiraeon-status installation={installation} "
            f"link={link} intent={intent} -->",
            "## Möbiræon Task status",
            "",
            f"Installation: `{installation}`",
            f"Link: `{link}`",
            f"Task: `{facts['task']}` (version {facts['task_version']})",
            f"State: `{facts['state']}`",
            f"Attempt: `{facts['attempt'] or 'none'}`",
            f"Recorded result: `{facts['result'] or 'none'}`",
            "",
            "Evidence references:",
        ]
        lines += [
            f"- `{a['identity']}@{a['revision']}` SHA-256 `{a['sha256']}`"
            for a in facts["evidence"]
        ]
        lines += [
            "",
            "Run completion does not establish Task acceptance.",
            "Inline fixture evidence has no hosted resolver.",
        ]
        return "\n".join(lines) + "\n"

    async def _network(
        self, operation, caller, proof, target, inputs, invocation, interruption
    ):
        admitted = time.monotonic()
        cycle, link, deadline = None, None, None
        request = inputs["operation_id"]
        try:
            with self.store.engine.connect() as tx:
                self._authorize(tx, operation, target, inputs, proof)
                _, definition, _ = self._connection(
                    tx, target.identity, inputs["connection_revision"]
                )
            deadline = admitted + definition["limits"]["cycle_seconds"]
            with self._tx(deadline) as tx:
                self._authorize(tx, operation, target, inputs, proof)
                head, definition, _ = self._connection(
                    tx, target.identity, inputs["connection_revision"]
                )
                link_row = row(tx, "forge_links", "task", inputs["task_id"])
                link = dict(link_row) if link_row else None
                if operation == Operation.FORGE_SYNC:
                    require(link is not None, Reason.NOT_FOUND)
                    require(link["version"] == inputs["expected_version"])
                elif link:
                    require(inputs["expected_version"] in (0, link["version"]))
                    require(
                        link["issue_number"] == inputs["issue_number"]
                        and link["project"] == target.identity
                    )
                else:
                    require(inputs["expected_version"] == 0)
                self._reserve(tx, operation, target, inputs, caller)
                facts = self._projection(tx, inputs["task_id"])
                if operation == Operation.FORGE_SYNC:
                    cycle = identity("cycle")
                    link["version"] += 1
                    link["generation"] = cycle
                    insert(
                        tx,
                        "forge_cycles",
                        id=cycle,
                        link=link["id"],
                        request=request,
                        version=link["version"],
                        record=canonical(
                            {
                                "task": facts,
                                "connection_revision": head["revision"],
                                "actor": asdict(caller.actor),
                            }
                        ),
                    )
                    execute(
                        tx,
                        "UPDATE forge_links SET version=:v,generation=:g WHERE id=:id",
                        dict(v=link["version"], g=cycle, id=link["id"]),
                    )
                    pending = self._pending(tx, link["id"])
                    if pending:
                        execute(
                            tx,
                            "UPDATE forge_intent_state SET generation=:g WHERE id=:id",
                            dict(g=cycle, id=pending["id"]),
                        )
                    self._history(
                        tx,
                        target.identity,
                        link["id"],
                        invocation,
                        caller,
                        "admitted",
                        cycle,
                        Outcome.SUCCESS,
                        {
                            "version": link["version"],
                            "reconciliation_claim": pending["id"] if pending else None,
                        },
                    )
            deadline = admitted + definition["limits"]["cycle_seconds"]
            self.fault("admission_committed")
            token = read_token(self.private, definition["credential"]["name"], store=self.store)
            async with self.adapter(definition, token, admitted=admitted) as adapter:
                issue = await adapter.preflight(
                    link["issue_number"] if link else inputs["issue_number"]
                )
                self.fault("preflight_observed")
                if operation == Operation.FORGE_LINK:
                    return self._establish_link(
                        operation,
                        caller,
                        proof,
                        target,
                        inputs,
                        invocation,
                        head,
                        definition,
                        issue,
                        link,
                        deadline,
                    )
                require(issue.identity == link["issue"])
                with self.store.engine.connect() as tx:
                    pending = self._pending(tx, link["id"])
                if pending:
                    return await self._reconcile(
                        adapter, pending, link, caller, target, inputs, invocation, deadline
                    )
                observed = await adapter.comment(link["comment"]) if link["comment"] else None
                conflict = None
                publication = json.loads(link["publication"]) if link["publication"] else None
                if link["comment"]:
                    if observed is None:
                        # Reverify access after the 404, then require a complete list.
                        await adapter.preflight(link["issue_number"])
                        comments = await adapter.comments()
                        require(
                            not any(c.identity == link["comment"] for c in comments),
                            Reason.UNAVAILABLE,
                        )
                        conflict = {
                            "kind": "deleted",
                            "comment": link["comment"],
                            "lookup_sha256": digest([asdict(c) for c in comments]),
                        }
                    else:
                        require(observed.author == link["account"])
                        if (
                            link["conflict"]
                            or not publication
                            or sha(observed.body) != publication["body_sha256"]
                        ):
                            conflict = {
                                "kind": "edited",
                                "comment": observed.identity,
                                "body_sha256": sha(observed.body),
                            }
                approval = self._approved(link, conflict)
                if conflict and approval is None:
                    self._record_conflict(
                        link, conflict, caller, target, inputs, invocation, deadline, proof
                    )
                    raise SafeError(Reason.CONFLICT)
                semantic = digest(
                    {
                        "installation": self.private.verify()["installation"],
                        "link": link["id"],
                        "facts": facts,
                    }
                )
                if publication and not conflict and semantic == publication["semantic_sha256"]:
                    with self._tx(deadline) as tx:
                        self._current(
                            tx, operation, caller, proof, target, inputs, link, facts, head
                        )
                        self._observation(tx, link, issue)
                        self._history(
                            tx,
                            target.identity,
                            link["id"],
                            invocation,
                            caller,
                            "unchanged",
                            cycle,
                            Outcome.SUCCESS,
                            {},
                        )
                        return self._complete(
                            tx, request, "unchanged", link["id"], link["version"]
                        )
                intent = identity("intent")
                installation = self.private.verify()["installation"]
                body = self._render(installation, link["id"], intent, facts)
                require(
                    len(body.encode()) <= definition["limits"]["comment_bytes"],
                    Reason.UNAVAILABLE,
                )
                method = "POST" if observed is None else "PATCH"
                adapter.check_write(body)
                record = {
                    "body": body,
                    "body_sha256": sha(body),
                    "semantic_sha256": semantic,
                    "method": method,
                    "comment": observed.identity if observed else None,
                    "expected_observation": {
                        "identity": observed.identity,
                        "issue": observed.issue,
                        "author": observed.author,
                        "body_sha256": sha(observed.body),
                    }
                    if observed
                    else conflict,
                    "source_task": facts,
                    "connection_revision": head["revision"],
                    "definition": definition,
                    "issue": asdict(issue),
                    "installation": installation,
                    "destination": adapter.destination(
                        method, observed.identity if observed else None
                    ),
                    "approval": approval,
                    "cycle": cycle,
                    "request": request,
                }
                with self._tx(deadline) as tx:
                    self._current(
                        tx, operation, caller, proof, target, inputs, link, facts, head
                    )
                    if approval:
                        require(self._approved(link, conflict, tx=tx) == approval)
                    insert(
                        tx,
                        "forge_intents",
                        id=intent,
                        link=link["id"],
                        cycle=cycle,
                        record=canonical(record),
                    )
                    insert(
                        tx,
                        "forge_intent_state",
                        id=intent,
                        link=link["id"],
                        generation=cycle,
                        state="prepared",
                    )
                    if approval:
                        insert(tx, "forge_consumptions", approval=approval, intent=intent)
                    self._observation(tx, link, issue)
                    self._history(
                        tx,
                        target.identity,
                        link["id"],
                        invocation,
                        caller,
                        "prepared",
                        intent,
                        Outcome.SUCCESS,
                        {"body_sha256": sha(body)},
                    )
                    self.fault("before_prepare_commit")
                self.fault("prepared_committed")
                with self._tx(deadline) as tx:
                    self._current(
                        tx, operation, caller, proof, target, inputs, link, facts, head
                    )
                    adapter.check_write(body)
                    changed = execute(
                        tx,
                        "UPDATE forge_intent_state SET state='armed' "
                        "WHERE id=:id AND generation=:g AND state='prepared'",
                        dict(id=intent, g=cycle),
                    )
                    require(changed.rowcount == 1)
                    self._history(
                        tx,
                        target.identity,
                        link["id"],
                        invocation,
                        caller,
                        "armed",
                        intent,
                        Outcome.SUCCESS,
                        {},
                    )
                    self.fault("before_arm_commit")
                self.fault("armed_committed")
                require(not interruption.pending, Reason.UNCERTAIN)
                confirmed = await adapter.publish(
                    method, observed.identity if observed else None, body
                )
                self.fault("write_observed")
                result = self._confirm(
                    intent,
                    record,
                    confirmed,
                    link,
                    caller,
                    target,
                    inputs,
                    invocation,
                    deadline,
                )
            with self.store.engine.connect() as tx:
                self._authorize(tx, operation, target, inputs, proof)
            return result
        except BaseException as error:
            # A fresh writer serializes after any uncertain earlier commit. It may close
            # a positively unarmed intent, but an armed one remains potentially delivered.
            self._record_error(
                operation,
                caller,
                target,
                inputs,
                invocation,
                link,
                cycle,
                deadline,
                error.reason if isinstance(error, SafeError) else Reason.UNAVAILABLE,
            )
            with self.store.engine.connect() as tx:
                pending = self._pending(tx, link["id"]) if link else None
                if pending and pending["state"] in {"armed", "uncertain"}:
                    raise SafeError(Reason.UNCERTAIN) from None
                if isinstance(error, SafeError) and error.reason == Reason.CLEANUP_FAILED:
                    raise error
                self._authorize(tx, operation, target, inputs, proof)
                replay = self._replay(tx, operation, target, inputs, caller)
                if replay:
                    return replay
            if isinstance(error, (KeyboardInterrupt, asyncio.CancelledError)):
                raise SafeError(Reason.UNCERTAIN) from None
            raise

    def _tx(self, deadline):
        remaining = deadline - time.monotonic() if deadline else self.store.timeout
        require(remaining > 0, Reason.UNAVAILABLE)
        return self.store.transaction(timeout=min(self.store.timeout, remaining))

    def _current(self, tx, operation, caller, proof, target, inputs, link, facts, head):
        self._authorize(tx, operation, target, inputs, proof)
        current, _, _ = self._connection(tx, target.identity, head["revision"])
        require(current["version"] == head["version"])
        retained = self._link(tx, inputs["task_id"], target.identity)
        require(
            retained["version"] == link["version"]
            and retained["generation"] == link["generation"]
            and retained["conflict"] == link["conflict"]
            and retained["approval"] == link["approval"]
        )
        require(
            row(tx, "coordination_tasks", "id", inputs["task_id"])["version"]
            == facts["task_version"]
        )

    def _observation(self, tx, link, issue):
        execute(
            tx,
            "UPDATE forge_links SET observation=:o WHERE id=:id AND generation=:g",
            dict(o=canonical(asdict(issue)), id=link["id"], g=link["generation"]),
        )

    def _establish_link(
        self,
        operation,
        caller,
        proof,
        target,
        inputs,
        invocation,
        head,
        definition,
        issue,
        link,
        deadline,
    ):
        with self._tx(deadline) as tx:
            self._authorize(tx, operation, target, inputs, proof)
            self._connection(tx, target.identity, head["revision"])
            previous = row(tx, "forge_links", "task", inputs["task_id"])
            if previous:
                require(
                    previous["issue"] == issue.identity
                    and previous["connection"] == head["id"]
                    and inputs["expected_version"] in (0, previous["version"])
                )
                state, lid, version = "already_linked", previous["id"], previous["version"]
            else:
                require(link is None)
                lid, version, state = identity("link"), 1, "linked"
                insert(
                    tx,
                    "forge_links",
                    id=lid,
                    task=inputs["task_id"],
                    project=target.identity,
                    connection=head["id"],
                    revision=head["revision"],
                    provider=definition["provider"],
                    origin=definition["origin"],
                    repository=definition["repository"]["id"],
                    account=definition["account"]["id"],
                    issue=issue.identity,
                    issue_number=issue.number,
                    version=1,
                    observation=canonical(asdict(issue)),
                )
            self._history(
                tx, target.identity, lid, invocation, caller, state, lid, Outcome.SUCCESS, {}
            )
            return self._complete(tx, inputs["operation_id"], state, lid, version)

    def _approved(self, link, conflict, *, tx=None):
        if not conflict or not link["approval"]:
            return None
        if tx is None:
            with self.store.engine.connect() as connection:
                return self._approved(link, conflict, tx=connection)
        approval = row(tx, "forge_approvals", "id", link["approval"])
        if (
            approval
            and json.loads(approval["record"])["observation"] == conflict
            and row(tx, "forge_consumptions", "approval", approval["id"]) is None
        ):
            return approval["id"]
        return None

    def _record_conflict(
        self, link, observation, caller, target, inputs, invocation, deadline, proof
    ):
        with self._tx(deadline) as tx:
            self._authorize(tx, Operation.FORGE_SYNC, target, inputs, proof)
            previous = (
                row(tx, "forge_conflicts", "id", link["conflict"]) if link["conflict"] else None
            )
            if previous and json.loads(previous["record"]) == observation:
                return
            cid = identity("conflict")
            insert(
                tx,
                "forge_conflicts",
                id=cid,
                link=link["id"],
                version=link["version"],
                record=canonical(observation),
            )
            changed = execute(
                tx,
                "UPDATE forge_links SET conflict=:c,approval=NULL "
                "WHERE id=:id AND generation=:g",
                dict(c=cid, id=link["id"], g=link["generation"]),
            )
            require(changed.rowcount == 1)
            self._history(
                tx,
                target.identity,
                link["id"],
                invocation,
                caller,
                "conflict",
                cid,
                Outcome.FAILURE,
                observation,
            )

    def _confirm(
        self, intent, record, comment, link, caller, target, inputs, invocation, deadline
    ):
        with self._tx(deadline) as tx:
            changed = execute(
                tx,
                "UPDATE forge_intent_state SET state='confirmed' "
                "WHERE id=:id AND generation=:g AND state IN ('armed','uncertain')",
                dict(id=intent, g=link["generation"]),
            )
            require(changed.rowcount == 1)
            current = self._link(tx, inputs["task_id"], target.identity)
            require(current["generation"] == link["generation"])
            publication = {
                "intent": intent,
                "comment": comment.identity,
                "body_sha256": record["body_sha256"],
                "semantic_sha256": record["semantic_sha256"],
                "source_task_version": record["source_task"]["task_version"],
                "connection_revision": record["connection_revision"],
            }
            execute(
                tx,
                "UPDATE forge_links SET comment=:c,publication=:p,conflict=NULL,approval=NULL "
                "WHERE id=:id AND generation=:g",
                dict(
                    c=comment.identity,
                    p=canonical(publication),
                    id=link["id"],
                    g=link["generation"],
                ),
            )
            self._history(
                tx,
                target.identity,
                link["id"],
                invocation,
                caller,
                "published",
                intent,
                Outcome.SUCCESS,
                publication | {"previous_comment": current["comment"]},
            )
            if row(tx, "forge_receipts", "id", record["request"]) is None:
                original_cycle = row(tx, "forge_cycles", "id", record["cycle"])
                self._complete(
                    tx, record["request"], "published", link["id"], original_cycle["version"]
                )
            if inputs["operation_id"] != record["request"]:
                result = self._complete(
                    tx, inputs["operation_id"], "published", link["id"], link["version"]
                )
            else:
                result = BusinessData(
                    reference=link["id"], version=link["version"], state="published"
                )
            self.fault("before_finalize_commit")
        self.fault("finalized_committed")
        return result

    def _close_prepared(
        self,
        tx,
        pending,
        link,
        caller,
        target,
        inputs,
        invocation,
        *,
        outcome=Outcome.UNAVAILABLE,
        reason=Reason.UNAVAILABLE,
    ):
        """Close only a positively unarmed intent and both correlated receipts atomically."""
        record = json.loads(pending["record"])
        original = row(tx, "forge_requests", "id", record["request"])
        original_cycle = row(tx, "forge_cycles", "id", record["cycle"])
        recovery_cycle = row(tx, "forge_cycles", "id", link["generation"])
        retained = row(tx, "forge_links", "id", link["id"])
        require(
            original is not None and original_cycle is not None and recovery_cycle is not None
        )
        original_facts = json.loads(original_cycle["record"])
        require(
            pending["state"] == "prepared"
            and pending["link"]
            == link["id"]
            == original_cycle["link"]
            == recovery_cycle["link"]
            and pending["cycle"] == original_cycle["id"] == record["cycle"]
            and original_cycle["request"] == original["id"] == record["request"]
            and original["project"] == target.identity == retained["project"]
            and original["task"] == retained["task"] == inputs["task_id"]
            and original["operation"] == Operation.FORGE_SYNC.value
            and original["actor"] == original_facts["actor"]["value"]
            and original_facts["task"] == record["source_task"]
            and original_facts["connection_revision"] == record["connection_revision"]
            and recovery_cycle["request"] == inputs["operation_id"]
            and recovery_cycle["version"] == retained["version"] == link["version"]
            and retained["generation"] == pending["generation"] == link["generation"]
        )
        changed = execute(
            tx,
            "UPDATE forge_intent_state SET state='not_attempted' "
            "WHERE id=:id AND link=:link AND generation=:g AND state='prepared'",
            dict(id=pending["id"], link=link["id"], g=link["generation"]),
        )
        require(changed.rowcount == 1)
        self._history(
            tx,
            target.identity,
            link["id"],
            invocation,
            caller,
            "not_attempted",
            pending["id"],
            Outcome.UNAVAILABLE,
            {
                "original_request": original["id"],
                "original_cycle": original_cycle["id"],
                "recovery_request": inputs["operation_id"],
                "recovery_cycle": recovery_cycle["id"],
                "recovery_reason": reason.value,
            },
        )
        receipts = [
            (
                original["id"],
                original_cycle["version"],
                outcome if original["id"] == inputs["operation_id"] else Outcome.UNAVAILABLE,
                reason if original["id"] == inputs["operation_id"] else Reason.UNAVAILABLE,
            )
        ]
        if original["id"] != inputs["operation_id"]:
            receipts.append(
                (inputs["operation_id"], recovery_cycle["version"], outcome, reason)
            )
        for request, version, effect, failure in receipts:
            existing = row(tx, "forge_receipts", "id", request)
            expected = {
                "outcome": effect.value,
                "reason": failure.value,
                "data": asdict(
                    BusinessData(reference=link["id"], version=version, state="not_attempted")
                ),
            }
            if existing:
                require(existing["result"] == canonical(expected))
            else:
                self._complete(
                    tx,
                    request,
                    "not_attempted",
                    link["id"],
                    version,
                    outcome=effect,
                    reason=failure,
                )

    async def _reconcile(
        self, adapter, pending, link, caller, target, inputs, invocation, deadline
    ):
        record = json.loads(pending["record"])
        if pending["state"] == "prepared":
            with self._tx(deadline) as tx:
                self._close_prepared(tx, pending, link, caller, target, inputs, invocation)
            self.fault("not_attempted_committed")
            raise SafeError(Reason.UNAVAILABLE)
        if record["method"] == "POST":
            comments = await adapter.comments()
            marker = record["body"].split("\n", 1)[0]
            candidates = [c for c in comments if pending["id"] in c.body or marker in c.body]
            require(len(candidates) == 1, Reason.UNCERTAIN)
            comment = candidates[0]
        else:
            comment = await adapter.comment(record["comment"])
        require(
            comment is not None
            and comment.body == record["body"]
            and comment.author == link["account"]
            and comment.issue == link["issue"],
            Reason.UNCERTAIN,
        )
        return self._confirm(
            pending["id"], record, comment, link, caller, target, inputs, invocation, deadline
        )

    def _record_error(
        self, operation, caller, target, inputs, invocation, link, cycle, deadline, reason
    ):
        try:
            # This is trusted retained-intent recording, not new Task authority. A fresh
            # writer is mandatory even after a lost local commit acknowledgement.
            with self.store.transaction(timeout=min(self.store.timeout, 0.5)) as tx:
                pending = self._pending(tx, link["id"]) if link else None
                outcome = {
                    Reason.REFUSED: Outcome.REFUSED,
                    Reason.CONFLICT: Outcome.FAILURE,
                }.get(reason, Outcome.UNAVAILABLE)
                if pending and pending["generation"] == cycle:
                    if pending["state"] == "prepared":
                        self._close_prepared(
                            tx,
                            pending,
                            link,
                            caller,
                            target,
                            inputs,
                            invocation,
                            outcome=outcome,
                            reason=reason,
                        )
                        return
                    state = "not_attempted" if pending["state"] == "prepared" else "uncertain"
                    execute(
                        tx,
                        "UPDATE forge_intent_state SET state=:s WHERE id=:id AND generation=:g",
                        dict(s=state, id=pending["id"], g=cycle),
                    )
                    self._history(
                        tx,
                        target.identity,
                        link["id"],
                        invocation,
                        caller,
                        state,
                        pending["id"],
                        Outcome.UNCERTAIN if state == "uncertain" else Outcome.UNAVAILABLE,
                        {},
                    )
                unresolved = pending is not None and pending["state"] != "prepared"
                if (
                    not unresolved
                    and row(tx, "forge_requests", "id", inputs["operation_id"])
                    and row(tx, "forge_receipts", "id", inputs["operation_id"]) is None
                ):
                    outcome = {
                        Reason.REFUSED: Outcome.REFUSED,
                        Reason.CONFLICT: Outcome.FAILURE,
                    }.get(reason, Outcome.UNAVAILABLE)
                    self._history(
                        tx,
                        target.identity,
                        link["id"] if link else None,
                        invocation,
                        caller,
                        "cycle_failed",
                        inputs["operation_id"],
                        outcome,
                        {"reason": reason.value},
                    )
                    self._complete(
                        tx,
                        inputs["operation_id"],
                        "not_attempted",
                        link["id"] if link else None,
                        link["version"] if link else None,
                        outcome=outcome,
                        reason=reason,
                    )
        except Exception:
            pass  # Invoke's separate attempt audit truthfully exposes audit failure.
