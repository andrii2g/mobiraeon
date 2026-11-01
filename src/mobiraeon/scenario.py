"""Isolated trusted synthetic identities and simulator; never ordinary execution.

Run creates a NEW disposable private root. Status only inspects an existing root.
No actor, grant, qualification or configuration bypass is accepted from the CLI.
"""

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from mobiraeon.access import Access, credential_proof
from mobiraeon.bootstrap import prepare, read_package
from mobiraeon.catalog import RegistryService
from mobiraeon.contracts import CallerContext, EntityId, Operation, Outcome
from mobiraeon.coordination import Coordinator, require
from mobiraeon.errors import Reason
from mobiraeon.persistence import Store
from mobiraeon.private_state import PrivateState, durable_new, harden
from mobiraeon.registry_schema import ACCESS_ACTIONS, CATALOG_ACTIONS, load_json

TARGET = {"kind": "entity", "entity_kind": "task", "identity": "task-1"}
AUTHOR_ACTIONS = {
    Operation.SUPPLY,
    Operation.ALLOCATE,
    Operation.DISPATCH,
    Operation.OBSERVE,
    Operation.SUBMIT,
    Operation.STATUS,
}
ASSESSOR_ACTIONS = {Operation.ASSESS, Operation.ACCEPT, Operation.STATUS}


def fixture_ref(kind):
    return {"kind": kind, "identity": "fixture-" + kind, "revision": "fixture-v1"}


class FixtureConfiguration:
    """Immutable exact fixture source, independent of the retained real catalog."""

    def resolve(self, references):
        require(
            references
            == {kind: fixture_ref(kind) for kind in ("agent", "profile", "role", "context")},
            Reason.NOT_FOUND,
        )
        return {
            "references": references,
            "mode": "isolated-simulation",
            "agent": {"profileRef": fixture_ref("profile")},
            "profile": {"roleRef": fixture_ref("role"), "runtime": "simulated"},
            "context": "Trusted bounded text-only scenario v1; no external execution",
            "requested": {"mode": "isolated-simulation", "configuration": references},
            "effective": {
                "runtime": {"name": "local-marker-simulator", "version": "fixture-v1"},
                "transport": "in-process-fixture",
                "provider": "unavailable",
                "account": "unavailable",
                "model": "unavailable",
                "tools": [],
                "instructions": {
                    "revision": "fixture-v1",
                    "text": "Create one local simulated marker",
                },
                "limits": {"active_attempts": 1, "provider_calls": 0},
                "qualification": "not-applicable-to-isolated-simulation",
            },
        }


class ScenarioAccess(Access):
    """Fixed trusted fixture composition after real credential authentication."""

    def __init__(self, store, private):
        super().__init__(store, private)
        self.identities = {
            credential_proof(
                private.read_credential(private.credential_path(name + ".token"))
            ).identifier: "scenario-" + name
            for name in ("author", "assessor")
        }

    def caller(self, proof):
        ordinary = super().caller(proof)
        if ordinary is None:
            return None
        identity = self.identities.get(proof.identifier)
        return (
            CallerContext(EntityId("human", identity), "trusted-scenario") if identity else None
        )


def compose(directory):
    private = PrivateState(directory, directory / "scenario.db")
    store = Store(private.database)
    coordinator = Coordinator(
        store,
        private,
        access=ScenarioAccess(store, private),
        configuration_source=FixtureConfiguration(),
    )
    return store, private, coordinator


def proof_for(private, name):
    return credential_proof(private.read_credential(private.credential_path(name + ".token")))


def setup(directory, catalog_input):
    private = PrivateState(directory, directory / "scenario.db")
    private.provision()
    store = Store(private.database)
    try:
        store.initialize()
        harden(private.database)
        registry = RegistryService(store, private)
        administrator = registry.invoke(
            Operation.SETUP,
            {"kind": "access", "entity_kind": "installation", "identity": "owner"},
            {
                "destination": "admin.token",
                "lifetime_seconds": 3600,
                "allow_self_review": True,
                "grants": [
                    {"action": a.value, "scope": "*"}
                    for a in sorted(ACCESS_ACTIONS | CATALOG_ACTIONS)
                ],
            },
            proof=registry.access.owner_proof(),
        )
        require(administrator.outcome == Outcome.SUCCESS)
        admin = proof_for(private, "admin")
        prepared = prepare(registry, read_package(catalog_input), admin)
        for name, actions in (("author", AUTHOR_ACTIONS), ("assessor", ASSESSOR_ACTIONS)):
            result = registry.invoke(
                Operation.ISSUE,
                {"kind": "access", "entity_kind": "credential", "identity": "new-" + name},
                {
                    "destination": name + ".token",
                    "lifetime_seconds": 3600,
                    "grants": [
                        {"action": a.value, "scope": "task:task-1"} for a in sorted(actions)
                    ]
                    + [{"action": Operation.REGISTRY_READ.value, "scope": "*"}],
                },
                proof=admin,
            )
            require(result.outcome == Outcome.SUCCESS)
        return {
            "catalog": prepared,
            "catalog_input_sha256": hashlib.sha256(catalog_input.read_bytes()).hexdigest(),
        }
    finally:
        store.close()


def run_scenario(directory, input_file, catalog_input, *, stop_after=None):
    provenance = setup(directory, catalog_input)
    scenario = load_json(input_file.read_bytes())
    # Only supplied work and versioned outputs; identity/grants/configuration are trusted code.
    from mobiraeon.registry_schema import fields

    fields(scenario, {"work", "artifacts"}, {"work", "artifacts"})
    store, private, coordinator = compose(directory)
    steps = []

    def invoke(action, inputs, actor="author"):
        result = coordinator.invoke(action, TARGET, inputs, proof=proof_for(private, actor))
        steps.append(asdict(result))
        require(result.outcome == Outcome.SUCCESS)
        return result

    try:
        invoke(Operation.SUPPLY, {"operation_id": "supply-1", "work": scenario["work"]})
        allocation = {
            "operation_id": "allocate-1",
            "expected_version": 1,
            "assignment_id": "assignment-1",
            "attempt_id": "attempt-1",
            "configuration": {
                kind: fixture_ref(kind) for kind in ("agent", "profile", "role", "context")
            },
        }
        invoke(Operation.ALLOCATE, allocation)
        if stop_after == "allocation":
            return {"steps": steps}
        dispatch = invoke(
            Operation.DISPATCH,
            {"operation_id": "dispatch-1", "expected_version": 2, "attempt_id": "attempt-1"},
        )
        if stop_after == "reservation":
            return {"steps": steps}
        require(dispatch.data.records[0]["replayed"] is False)
        # Exclusive synthetic effect, with no provider/process/forge invocation.
        durable_new(
            directory / "simulated-effect.json", b'{"attempt":"attempt-1","simulated":true}\n'
        )
        if stop_after == "effect":
            return {"steps": steps}
        invoke(
            Operation.OBSERVE,
            {
                "operation_id": "observe-1",
                "expected_version": 3,
                "attempt_id": "attempt-1",
                "observation": "succeeded",
                "detail": "Exclusive local simulated marker created; no Agent ran",
            },
        )
        submitted = invoke(
            Operation.SUBMIT,
            {
                "operation_id": "submit-1",
                "expected_version": 4,
                "attempt_id": "attempt-1",
                "submission_id": "submission-1",
                "artifacts": scenario["artifacts"],
            },
        )
        submission_digest = submitted.data.records[0]["fact"]["submission_digest"]
        invoke(
            Operation.ASSESS,
            {
                "operation_id": "assess-1",
                "expected_version": 5,
                "submission_id": "submission-1",
                "submission_digest": submission_digest,
                "evidence": scenario["artifacts"],
                "decision": "approve",
                "rationale": "Synthetic human assessment of exact supplied evidence",
            },
            "assessor",
        )
        invoke(
            Operation.ACCEPT,
            {
                "operation_id": "accept-1",
                "expected_version": 6,
                "submission_id": "submission-1",
                "submission_digest": submission_digest,
                "assessment_id": "assess-1",
            },
            "assessor",
        )
        status = invoke(Operation.STATUS, {}, "assessor")
        with store.engine.connect() as tx:
            agents = [
                dict(row)
                for row in tx.exec_driver_sql(
                    "SELECT identity,enabled FROM registry_controls"
                ).mappings()
            ]
        require(len(agents) == 5 and all(row["enabled"] == 0 for row in agents))
        return provenance | {
            "input_sha256": hashlib.sha256(input_file.read_bytes()).hexdigest(),
            "steps": steps,
            "status": status.data.records[0],
            "actual_agents": agents,
            "execution": "unavailable",
        }
    finally:
        store.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["run", "status"])
    parser.add_argument("--directory", required=True, type=Path)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--catalog-input", type=Path)
    options = parser.parse_args()
    if options.command == "run":
        if options.input is None or options.catalog_input is None:
            parser.error("run requires explicit scenario and catalog inputs")
        result = run_scenario(options.directory.resolve(), options.input, options.catalog_input)
    else:
        store, private, coordinator = compose(options.directory.resolve())
        try:
            result = asdict(
                coordinator.invoke(
                    Operation.STATUS, TARGET, {}, proof=proof_for(private, "assessor")
                )
            )
        finally:
            store.close()
    print(json.dumps(result, default=str))


if __name__ == "__main__":
    main()
