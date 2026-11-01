"""Access-owned credentials, current grants and protected installation-owner actions."""

import hashlib
import hmac
import json
import re
import secrets
import time
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import text

from mobiraeon.contracts import CallerContext, EntityId, Operation
from mobiraeon.errors import Reason, SafeError
from mobiraeon.private_state import durable_new
from mobiraeon.registry_schema import canonical, validate_grants


def one(tx, sql, values=None):
    return tx.execute(text(sql), values or {}).mappings().first()


def execute(tx, sql, values=None):
    return tx.execute(text(sql), values or {})


@dataclass(frozen=True, repr=False)
class CredentialProof:
    identifier: str
    verifier: str


@dataclass(frozen=True)
class OwnerProof:
    installation: str
    principal: str


def credential_proof(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"mbr_[0-9a-f]{32}_[A-Za-z0-9_-]{43}", value
    ):
        raise SafeError(Reason.AUTHENTICATION)
    return CredentialProof(value[4:36], hashlib.sha256(value.encode()).hexdigest())


def audit(tx, invocation, operation, actor, target, outcome, reason, record=None, now=None):
    execute(
        tx,
        "INSERT INTO registry_audit(invocation,operation,actor,target"
        ",outcome,reason,record,at) "
        "VALUES (:invocation,:operation,:actor,:target,:outcome,:reason,:record,:at)",
        {
            "invocation": str(invocation),
            "operation": operation.value if operation else None,
            "actor": actor,
            "target": canonical(target) if target else None,
            "outcome": outcome.value,
            "reason": reason.value,
            "record": canonical(record or {}),
            "at": int(time.time()) if now is None else now,
        },
    )


def usable_admin(grants):
    return all(
        {"action": action.value, "scope": "*"} in grants
        for action in (Operation.ISSUE, Operation.GRANTS, Operation.REVOKE)
    )


class Access:
    def __init__(self, store, private, *, clock=time.time):
        self.store, self.private, self.clock = store, private, clock

    def owner_proof(self):
        marker = self.private.verify()
        return OwnerProof(marker["installation"], marker["principal"])

    def owner_valid(self, proof, tx):
        marker = self.private.verify()
        if not isinstance(proof, OwnerProof) or proof != OwnerProof(
            marker["installation"], marker["principal"]
        ):
            return False
        installation = one(tx, "SELECT * FROM access_installation WHERE id=1")
        return installation is None or (
            installation["installation"] == proof.installation
            and installation["principal"] == proof.principal
        )

    def authenticate(self, tx, proof):
        if not isinstance(proof, CredentialProof):
            return None
        row = one(
            tx,
            "SELECT c.*, i.actor FROM access_credentials c "
            "JOIN access_installation i ON c.installation_id=i.id WHERE c.id=:id",
            {"id": proof.identifier},
        )
        if row is None or row["revoked"] is not None or row["expires"] <= int(self.clock()):
            return None
        if not hmac.compare_digest(row["verifier"], proof.verifier):
            return None
        return row

    def caller(self, proof):
        with self.store.engine.connect() as connection:
            if isinstance(proof, OwnerProof):
                if not self.owner_valid(proof, connection):
                    return None
                return CallerContext(
                    EntityId("installation-owner", proof.principal), "protected-os-owner"
                )
            row = self.authenticate(connection, proof)
            return (
                CallerContext(EntityId("human", row["actor"]), "personal-token")
                if row
                else None
            )

    def permits(self, proof, operation, target, tx):
        if isinstance(proof, OwnerProof):
            return operation in {
                Operation.SETUP,
                Operation.RECOVER,
                Operation.ACCESS_RECONCILE,
            } and self.owner_valid(proof, tx)
        row = self.authenticate(tx, proof)
        if row is None:
            return False
        scopes = {"*", f"{target.entity_kind}:*", f"{target.entity_kind}:{target.identity}"}
        return any(
            grant["action"] == operation.value and grant["scope"] in scopes
            for grant in json.loads(row["grants"])
        )

    def deliver(self, inputs):
        self.private.verify()
        identifier = uuid4().hex
        raw = "mbr_" + identifier + "_" + secrets.token_urlsafe(32)
        destination = self.private.credential_path(inputs["destination"])
        durable_new(destination, raw.encode("ascii") + b"\n")
        return credential_proof(raw)

    def last_admin(self, tx):
        rows = execute(
            tx,
            "SELECT grants FROM access_credentials WHERE revoked IS NULL AND expires>:at",
            {"at": int(self.clock())},
        ).mappings()
        if not any(usable_admin(json.loads(row["grants"])) for row in rows):
            raise SafeError(Reason.LAST_ADMIN)

    def mutate(self, tx, operation, target, inputs, proof, delivered):
        now = int(self.clock())
        if operation in {Operation.SETUP, Operation.RECOVER, Operation.ISSUE, Operation.ROTATE}:
            if delivered is None:
                raise SafeError(Reason.DELIVERY)
            validate_grants(inputs["grants"])
            if operation == Operation.SETUP:
                if one(tx, "SELECT id FROM access_installation") is not None:
                    raise SafeError(Reason.CONFLICT)
                if not usable_admin(inputs["grants"]):
                    raise SafeError(Reason.LAST_ADMIN)
                if not self.owner_valid(proof, tx):
                    raise SafeError(Reason.REFUSED)
                execute(
                    tx,
                    "INSERT INTO access_installation VALUES(1,:installation,:prin"
                    "cipal,:actor,:review)",
                    {
                        "installation": proof.installation,
                        "principal": proof.principal,
                        "actor": uuid4().hex,
                        "review": inputs["allow_self_review"],
                    },
                )
            elif one(tx, "SELECT id FROM access_installation") is None:
                raise SafeError(Reason.REFUSED)
            if operation == Operation.RECOVER:
                if not self.owner_valid(proof, tx):
                    raise SafeError(Reason.REFUSED)
                execute(
                    tx,
                    "UPDATE access_credentials SET revoked=:now,version=version+1"
                    " WHERE revoked IS NULL",
                    {"now": now},
                )
            execute(
                tx,
                "INSERT INTO access_credentials VALUES(:id,1,:verifier,:creat"
                "ed,:expires,NULL,1,:grants)",
                {
                    "id": delivered.identifier,
                    "verifier": delivered.verifier,
                    "created": now,
                    "expires": now + inputs["lifetime_seconds"],
                    "grants": canonical(inputs["grants"]),
                },
            )
            if operation == Operation.ROTATE:
                self.update(tx, target.identity, inputs["expected_version"], revoked=now)
            self.last_admin(tx)
            return {
                "credential_id": delivered.identifier,
                "version": 1,
                "state": "registered",
                "grants": inputs["grants"],
                "expires": now + inputs["lifetime_seconds"],
            }
        if operation == Operation.REVOKE:
            self.update(tx, target.identity, inputs["expected_version"], revoked=now)
        elif operation == Operation.GRANTS:
            self.update(
                tx,
                target.identity,
                inputs["expected_version"],
                grants=canonical(inputs["grants"]),
            )
        self.last_admin(tx)
        return {
            "credential_id": target.identity,
            "version": inputs["expected_version"] + 1,
            "grants": inputs.get("grants"),
            "revoked": now if operation == Operation.REVOKE else None,
        }

    def update(self, tx, identifier, version, **changes):
        row = one(tx, "SELECT * FROM access_credentials WHERE id=:id", {"id": identifier})
        if row is None:
            raise SafeError(Reason.NOT_FOUND)
        if row["version"] != version:
            raise SafeError(Reason.CONFLICT)
        # Keys are internal constants, never request-controlled SQL identifiers.
        assignments = ",".join(f"{key}=:{key}" for key in changes)
        execute(
            tx,
            f"UPDATE access_credentials SET {assignments},version=version+1 WHERE id=:id",
            changes | {"id": identifier},
        )

    def reconcile(self, tx, identifier):
        row = one(
            tx,
            "SELECT id,created,expires,revoked,version FROM access_credentials WHERE id=:id",
            {"id": identifier},
        )
        return dict(row) if row else {"credential_id": identifier, "state": "not_registered"}


class CurrentAccessPolicy:
    """Invocation-local proof; no service retains one request's authentication."""

    def __init__(self, access, proof):
        self.access, self.proof = access, proof

    def permits(self, caller, operation, target):
        with self.access.store.engine.connect() as connection:
            return self.access.permits(self.proof, operation, target, connection)

    def permits_in_transaction(self, caller, operation, target, tx):
        return self.access.permits(self.proof, operation, target, tx)
