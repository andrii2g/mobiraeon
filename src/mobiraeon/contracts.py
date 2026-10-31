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
    REGISTRY = "registry"
    COORDINATION = "coordination"


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


class Outcome(StrEnum):
    SUCCESS = "success"
    INVALID = "invalid_input"
    REFUSED = "refused"
    UNAVAILABLE = "unavailable"
    FAILURE = "known_failure"
    UNCERTAIN = "uncertain_effects"


class PermissionPolicy(Protocol):
    def permits(
        self, caller: CallerContext, operation: Operation, target: RevisionRef | None
    ) -> bool: ...


@dataclass(frozen=True)
class OperationResult:
    invocation_id: UUID
    operation: Operation | None
    outcome: Outcome
    reason: Reason
    actor: EntityId | None = None
    target: RevisionRef | None = None
    evidence: tuple[ArtifactRef, ...] = ()

    # No Run completion or acceptance field: neither follows from operation success.
