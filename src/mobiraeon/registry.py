from mobiraeon.contracts import Operation, Owner
from mobiraeon.operations import Binding


def bindings():
    return {
        Operation.REGISTRY_READ: Binding(Owner.REGISTRY, requires_target=True),
        Operation.REGISTRY_USE: Binding(Owner.REGISTRY, requires_target=True),
    }
