from dataclasses import FrozenInstanceError

import pytest

from mobiraeon.contracts import (
    ArtifactRef,
    ConfigurationRefs,
    EntityId,
    ExternalIdentity,
    RevisionRef,
)


def ref(kind, revision="r1"):
    return RevisionRef(EntityId(kind, "fixture"), revision)


def test_exact_references_are_immutable_and_separate():
    snapshot = ConfigurationRefs(ref("agent"), ref("profile"), (ref("instruction"),), ())
    assert snapshot.agent != snapshot.profile
    assert ref("profile", "r2") != snapshot.profile
    with pytest.raises(FrozenInstanceError):
        snapshot.agent = ref("agent", "r2")
    assert ArtifactRef(EntityId("artifact", "report"), "sha256-abcd")
    assert ExternalIdentity("gitea-local", "developer-01")


@pytest.mark.parametrize("value", ["", "latest?", "bad/value", " secret ", None, 12])
def test_invalid_identities_and_revisions(value):
    with pytest.raises(ValueError):
        EntityId("agent", value)
    with pytest.raises(ValueError):
        RevisionRef(EntityId("agent", "a"), value)


def test_conflicting_and_wrong_kind_references():
    with pytest.raises(ValueError, match="conflicting"):
        ConfigurationRefs(
            ref("agent"), ref("profile"), (ref("instruction"), ref("instruction", "r2")), ()
        )
    with pytest.raises(ValueError):
        ConfigurationRefs(ref("profile"), ref("agent"), (), ())
    with pytest.raises(ValueError):
        ArtifactRef(EntityId("agent", "a"), "r1")
