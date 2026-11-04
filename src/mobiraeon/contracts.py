"""Domain-only contracts. References and Role text convey no authority."""

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from mobiraeon.errors import Reason


def _token(value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value
    ):
        raise ValueError("invalid identifier")


class Owner(StrEnum):
    FOUNDATION = "foundation"
    ACCESS = "access"
    REGISTRY = "registry"
    COORDINATION = "coordination"
    FORGE = "forge"


@dataclass(frozen=True)
class EntityId:
    kind: str
    value: str

    def __post_init__(self):
        _token(self.kind)
        _token(self.value)


@dataclass(frozen=True)
class RevisionRef:
    entity: EntityId
    revision: str

    def __post_init__(self):
        if not isinstance(self.entity, EntityId):
            raise ValueError("invalid entity reference")
        _token(self.revision)


@dataclass(frozen=True)
class ArtifactRef:
    artifact: EntityId
    revision: str

    def __post_init__(self):
        if not isinstance(self.artifact, EntityId) or self.artifact.kind != "artifact":
            raise ValueError("invalid artifact reference")
        _token(self.revision)


@dataclass(frozen=True)
class ExternalIdentity:
    forge: str
    account: str

    def __post_init__(self):
        _token(self.forge)
        _token(self.account)


@dataclass(frozen=True)
class ConfigurationRefs:
    agent: RevisionRef
    profile: RevisionRef
    instructions: tuple[RevisionRef, ...]
    policies: tuple[RevisionRef, ...]

    def __post_init__(self):
        if not isinstance(self.instructions, tuple) or not isinstance(self.policies, tuple):
            raise ValueError("immutable references required")
        groups = ((self.agent, "agent"), (self.profile, "profile"))
        groups += tuple((ref, "instruction") for ref in self.instructions)
        groups += tuple((ref, "policy") for ref in self.policies)
        seen = {}
        for ref, kind in groups:
            if not isinstance(ref, RevisionRef) or ref.entity.kind != kind:
                raise ValueError("reference kind mismatch")
            if ref.entity in seen and seen[ref.entity] != ref.revision:
                raise ValueError("conflicting exact references")
            seen[ref.entity] = ref.revision


class ExactConfigurationSource(Protocol):
    def resolve(self, reference: RevisionRef) -> ConfigurationRefs: ...


@dataclass(frozen=True)
class CallerContext:
    """Created by trusted composition/adapters, never deserialized from a request."""

    actor: EntityId
    authentication: str

    def __post_init__(self):
        if not isinstance(self.actor, EntityId):
            raise ValueError("invalid actor")
        _token(self.authentication)


class Operation(StrEnum):
    INITIALIZE = "initialize"
    UPGRADE = "upgrade"
    CHECK = "check"
    START = "start"
    REGISTRY_READ = "registry.read"
    REGISTRY_USE = "registry.use"
    COORDINATION_WORK = "coordination.work"
    SUPPLY = "coordination.supply"
    ALLOCATE = "coordination.allocate"
    DISPATCH = "coordination.dispatch"
    OBSERVE = "coordination.observe"
    SUBMIT = "coordination.submit"
    ASSESS = "coordination.assess"
    ACCEPT = "coordination.accept"
    STATUS = "coordination.status"
    EXECUTION_RUN = "execution.run"
    EXECUTION_STATUS = "execution.status"
    EXECUTION_STOP = "execution.stop"
    FORGE_CONFIGURE = "forge.connection.configure"
    FORGE_READ = "forge.connection.read"
    FORGE_LINK = "forge.link"
    FORGE_STATUS = "forge.status"
    FORGE_SYNC = "forge.sync"
    FORGE_RESOLVE = "forge.resolve"
    CREATE = "registry.create"
    EDIT = "registry.edit"
    DISCARD = "registry.discard"
    VALIDATE = "registry.validate"
    REVIEW = "registry.review"
    PUBLISH = "registry.publish"
    HISTORY = "registry.history"
    SELECT = "registry.select"
    ENABLE = "registry.enable"
    DISABLE = "registry.disable"
    RECONCILE = "registry.reconcile"
    SETUP = "access.setup"
    RECOVER = "access.recover"
    ISSUE = "access.issue"
    ROTATE = "access.rotate"
    GRANTS = "access.grants"
    REVOKE = "access.revoke"
    ACCESS_RECONCILE = "access.reconcile"


@dataclass(frozen=True)
class BusinessTarget:
    kind: str
    entity_kind: str
    identity: str
    revision: str | None = None

    def __post_init__(self):
        if self.kind not in {"entity", "draft", "publication", "control", "access", "audit"}:
            raise ValueError("invalid target kind")
        _token(self.entity_kind)
        _token(self.identity)
        if self.revision is not None:
            _token(self.revision)


WORKFLOW_ACTIONS = {
    Operation.SUPPLY,
    Operation.ALLOCATE,
    Operation.DISPATCH,
    Operation.OBSERVE,
    Operation.SUBMIT,
    Operation.ASSESS,
    Operation.ACCEPT,
    Operation.STATUS,
}

EXECUTION_ACTIONS = {
    Operation.EXECUTION_RUN,
    Operation.EXECUTION_STATUS,
    Operation.EXECUTION_STOP,
}

FORGE_ACTIONS = {
    Operation.FORGE_CONFIGURE,
    Operation.FORGE_READ,
    Operation.FORGE_LINK,
    Operation.FORGE_STATUS,
    Operation.FORGE_SYNC,
    Operation.FORGE_RESOLVE,
}


@dataclass(frozen=True)
class BusinessData:
    records: tuple[dict, ...] = ()
    reference: str | None = None
    version: int | None = None
    state: str | None = None
    audit_status: str = "recorded"


class Outcome(StrEnum):
    SUCCESS = "success"
    INVALID = "invalid_input"
    REFUSED = "refused"
    UNAVAILABLE = "unavailable"
    FAILURE = "known_failure"
    UNCERTAIN = "uncertain_effects"


class PermissionPolicy(Protocol):
    def permits(
        self,
        caller: CallerContext,
        operation: Operation,
        target: RevisionRef | BusinessTarget | None,
    ) -> bool: ...


@dataclass(frozen=True)
class OperationResult:
    invocation_id: UUID
    operation: Operation | None
    outcome: Outcome
    reason: Reason
    actor: EntityId | None = None
    target: RevisionRef | BusinessTarget | None = None
    evidence: tuple[ArtifactRef, ...] = ()
    data: BusinessData | None = None

    # No Run completion or acceptance field: neither follows from operation success.
