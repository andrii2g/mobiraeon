from mobiraeon.contracts import Operation, Owner
from mobiraeon.operations import Binding


def bindings():
    return {Operation.COORDINATION_WORK: Binding(Owner.COORDINATION, requires_target=True)}
