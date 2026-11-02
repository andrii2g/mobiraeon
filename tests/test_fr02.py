"""FR-02: preserve partial publications and child operation progress."""

import json
from dataclasses import replace

import pytest
from test_increment2_repairs import cli
from test_increment2_repairs import installation as installation
from test_registry import document

from mobiraeon.catalog import RegistryService
from mobiraeon.contracts import BusinessData, Outcome
from mobiraeon.errors import Reason, SafeError


def package():
    return {
        "stage": "initial_test",
        "provenance": {},
        "definitions": [
            {"kind": "instruction", "identity": n, "document": document(n)}
            for n in ("first", "second")
        ],
    }


def count(service, table):
    with service.store.engine.connect() as tx:
        return tx.exec_driver_sql("SELECT count(*) FROM " + table).scalar()


def run(installation, payload):
    _, config = installation
    path = config.parent / "package.json"
    path.write_text(json.dumps(payload))
    return cli(config, "--input-file", path, "prepare")


@pytest.mark.parametrize("bad", ["missing", "malformed"])
def test_fr02_preflight(installation, bad):
    payload = package()
    payload["definitions"][1]["document"] = {
        "text": {"published": "profile:absent"} if bad == "missing" else {"published": 12}
    }
    code, result, _ = run(installation, payload)
    assert code == 2 and result["outcome"] == "invalid_input"
    assert count(installation[0], "registry_entities") == 0


@pytest.mark.parametrize(
    "step", ["registry.validate", "registry.review", "registry.publish", "runtime_conflict"]
)
def test_fr02_partial_progress(installation, monkeypatch, step):
    service, _ = installation
    original = RegistryService.invoke

    def fault(self, operation, target, inputs, **kw):
        if target.get("identity") == "second" and operation == (
            "registry.history" if step == "runtime_conflict" else step
        ):
            if step == "runtime_conflict":
                raise SafeError(Reason.CONFLICT)
            return replace(
                original(self, "registry.history", target | {"kind": "entity"}, {}, **kw),
                outcome=Outcome.INVALID,
                reason=Reason.INVALID_INPUT,
                data=BusinessData(audit_status="unavailable"),
            )
        return original(self, operation, target, inputs, **kw)

    monkeypatch.setattr(RegistryService, "invoke", fault)
    code, result, diagnostic = run(installation, package())
    assert (code, result["outcome"]) == (1, "known_failure"), result
    assert result["data"]["state"] == "preparation_stopped"
    progress = result["data"]["records"][0]
    assert progress["stage"] == "initial_test" and progress["execution_eligible"] is False
    assert (
        progress["publications"][0]["identity"] == "first"
        and not progress["reconciliation_required"]
    )
    assert progress["failed"]["definition"]["identity"] == "second"
    assert count(service, "registry_publications") == 1
    assert count(service, "registry_entities") == (1 if step == "runtime_conflict" else 2)
    completed = [s for s in progress["steps"] if s["outcome"] == "success"]
    assert any(
        s["action"] == "registry.publish"
        and s["reference"] == progress["publications"][0]["revision"]
        for s in completed
    )
    with service.store.engine.connect() as tx:
        audits = {r[0] for r in tx.exec_driver_sql("SELECT invocation FROM registry_audit")}
    assert all(s["invocation_id"] in audits for s in completed)
    if step != "runtime_conflict":
        assert progress["steps"][-1]["audit_status"] == "unavailable"
        assert progress["steps"][-1]["outcome"] == "invalid_input"
        assert progress["steps"][-1]["actor"] and progress["steps"][-1]["target"]
    assert "mbr_" not in json.dumps(result) + diagnostic
    monkeypatch.setattr(RegistryService, "invoke", original)
    code, resumed, _ = run(installation, package())
    assert code == 0, resumed
    code, repeated, _ = run(installation, package())
    assert code == 0 and repeated["data"]["records"] == resumed["data"]["records"]
    assert count(service, "registry_publications") == 2


def test_fr02_lost_ack_progress(installation, monkeypatch):
    from sqlalchemy.engine import Transaction

    original = Transaction.commit

    def fail(tx):
        original(tx)
        raise RuntimeError("synthetic ack loss")

    monkeypatch.setattr(Transaction, "commit", fail)
    code, result, _ = run(installation, package())
    assert code == 1 and result["outcome"] == "uncertain_effects"
    progress = result["data"]["records"][0]
    assert (
        progress["reconciliation_required"]
        and progress["failed"]["action"] == "registry.create"
    )
    assert progress["steps"][-1]["outcome"] == "uncertain_effects"
    monkeypatch.setattr(Transaction, "commit", original)
    assert count(installation[0], "registry_entities") == 1
    code, resumed, _ = run(installation, package())
    # Exact successful atomic audit reconciles this lost acknowledgement.
    assert code == 0, resumed
    assert count(installation[0], "registry_entities") == 2


def test_fr02_partial_review_receipt(installation, monkeypatch):
    service, _ = installation
    original = RegistryService.invoke

    def fault(self, operation, target, inputs, **kw):
        if operation == "registry.publish" and target.get("identity") == "first":
            return replace(
                original(self, "registry.history", target | {"kind": "entity"}, {}, **kw),
                outcome=Outcome.FAILURE,
                reason=Reason.CONFLICT,
            )
        return original(self, operation, target, inputs, **kw)

    monkeypatch.setattr(RegistryService, "invoke", fault)
    code, result, _ = run(installation, package())
    assert code == 1 and result["outcome"] == "known_failure"
    p = result["data"]["records"][0]
    assert not p["publications"] and any(
        s["action"] == "registry.review" and s["reference"] for s in p["steps"]
    )
    assert (
        count(service, "registry_reviews") == 1 and count(service, "registry_publications") == 0
    )


def test_fr02_no_effect_refusal_retains_child_classification(installation, monkeypatch):
    original = RegistryService.invoke

    def refused(self, operation, target, inputs, **kw):
        return replace(
            original(self, operation, target, inputs, **kw),
            outcome=Outcome.REFUSED,
            reason=Reason.REFUSED,
            data=BusinessData(audit_status="unavailable"),
        )

    monkeypatch.setattr(RegistryService, "invoke", refused)
    code, result, _ = run(installation, package())
    assert code == 1 and result["outcome"] == "refused"
    assert result["data"]["audit_status"] == "unavailable"
    progress = result["data"]["records"][0]
    assert not progress["publications"] and not progress["reconciliation_required"]
    assert count(installation[0], "registry_entities") == 0


def test_fr02_publication_retained_before_selection_failure(installation, monkeypatch):
    from pathlib import Path

    payload = json.loads(
        (Path(__file__).parents[1] / "bootstrap/initial-test.json").read_bytes()
    )
    original = RegistryService.invoke
    failed = []

    def fault(self, operation, target, inputs, **kw):
        if operation == "registry.select":
            failed.append(target["identity"])
            return replace(
                original(self, "registry.history", target | {"kind": "entity"}, {}, **kw),
                outcome=Outcome.FAILURE,
                reason=Reason.CONFLICT,
            )
        return original(self, operation, target, inputs, **kw)

    monkeypatch.setattr(RegistryService, "invoke", fault)
    code, result, _ = run(installation, payload)
    assert code == 1 and result["outcome"] == "known_failure"
    progress = result["data"]["records"][0]
    publication = progress["publications"][-1]
    assert publication["kind"] == "agent" and publication["identity"] == failed[0]
    with installation[0].store.engine.connect() as tx:
        assert (
            tx.exec_driver_sql(
                "SELECT count(*) FROM registry_publications WHERE id=?",
                (publication["revision"],),
            ).scalar()
            == 1
        )
        assert not any(
            row[0] for row in tx.exec_driver_sql("SELECT enabled FROM registry_controls")
        )
    monkeypatch.setattr(RegistryService, "invoke", original)
    code, resumed, _ = run(installation, payload)
    assert code == 0, resumed


@pytest.mark.parametrize("outage", [False, True])
def test_fr02_r1_actual_failed_attempt_audit(installation, monkeypatch, outage):
    """A failed child with no BusinessData can have a committed failure audit."""
    import mobiraeon.catalog as catalog

    service, _ = installation
    payload = package()
    payload["definitions"][1]["document"] = {}
    original = catalog.audit
    faulted = []

    def audit(tx, invocation, operation, actor, target, outcome, reason, *args, **kwargs):
        if (
            outage
            and operation.value == "registry.validate"
            and target["identity"] == "second"
            and outcome == Outcome.FAILURE
        ):
            faulted.append(str(invocation))
            raise OSError("trusted targeted failed-attempt audit outage")
        return original(
            tx, invocation, operation, actor, target, outcome, reason, *args, **kwargs
        )

    monkeypatch.setattr(catalog, "audit", audit)
    code, result, diagnostic = run(installation, payload)
    assert (code, result["outcome"], result["reason"]) == (
        1,
        "known_failure",
        "incomplete_definition",
    )
    assert result["phase"] == "terminal" and result["data"]["state"] == "preparation_stopped"
    progress = result["data"]["records"][0]
    failed = progress["steps"][-1]
    assert (
        failed["action"] == "registry.validate" and failed["definition"]["identity"] == "second"
    )
    assert not progress["reconciliation_required"]
    assert len(progress["publications"]) == 1
    assert progress["publications"][0]["identity"] == "first"
    assert count(service, "registry_entities") == count(service, "registry_drafts") == 2
    assert count(service, "registry_publications") == 1
    with service.store.engine.connect() as tx:
        rows = [
            dict(r._mapping)
            for r in tx.exec_driver_sql(
                "SELECT invocation,operation,actor,target,outcome,reason "
                "FROM registry_audit WHERE invocation=?",
                (failed["invocation_id"],),
            )
        ]
        revision = tx.exec_driver_sql("SELECT id FROM registry_publications").scalar()
    assert revision == progress["publications"][0]["revision"]
    if outage:
        assert faulted == [failed["invocation_id"]] and not rows
    else:
        assert len(rows) == 1
        assert (rows[0]["operation"], rows[0]["outcome"], rows[0]["reason"]) == (
            "registry.validate",
            "known_failure",
            "incomplete_definition",
        )
        assert rows[0]["actor"] == failed["actor"]["value"]
        assert json.loads(rows[0]["target"]) == failed["target"]
    assert "mbr_" not in json.dumps(result) + diagnostic and "Traceback" not in diagnostic
    print(
        "FR02_R1_EVIDENCE "
        + json.dumps(
            {
                "outage": outage,
                "exit": code,
                "returned": result,
                "diagnostic": diagnostic,
                "audit_rows": rows,
                "faulted_invocations": faulted,
                "publications": 1,
                "drafts": 2,
            }
        )
    )

    assert failed["audit_status"] == ("unavailable" if outage else "recorded")
    assert result["data"]["audit_status"] == (
        "unavailable" if outage else "operations_recorded"
    )
    if not outage:
        assert all(s["audit_status"] == "recorded" for s in progress["steps"][:-1])
    assert "mbr_" not in json.dumps(result) + diagnostic and "Traceback" not in diagnostic
