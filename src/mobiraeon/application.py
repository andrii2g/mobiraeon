from dataclasses import dataclass

from mobiraeon import coordination, registry
from mobiraeon.configuration import Configuration
from mobiraeon.contracts import CallerContext, EntityId, Operation, Owner
from mobiraeon.operations import Binding, OperationBoundary
from mobiraeon.persistence import Store

CAPABILITIES = {
    "fixture_execution": "supervised_fixture_only",
    "registry_business_operations": "authenticated_administration",
    "coordination_workflows": "local_simulated_task_acceptance",
    "agent_execution": "unavailable",
    "forge_integration": "gitea_manual_task_comment",
}


class LocalOperatorPolicy:
    """OS access to this process/store grants only local foundation operations."""

    def permits(self, caller, operation, target):
        return (
            caller == LOCAL_OPERATOR
            and target is None
            and operation
            in {Operation.INITIALIZE, Operation.UPGRADE, Operation.CHECK, Operation.START}
        )


LOCAL_OPERATOR = CallerContext(EntityId("operator", "local-os-operator"), "local-os")


@dataclass
class Application:
    configuration: Configuration

    def __post_init__(self):
        self.store = Store(self.configuration.database_path, self.configuration.timeout_seconds)
        bindings = {
            Operation.INITIALIZE: Binding(
                Owner.FOUNDATION, lambda tx, ref: self.store.initialize()
            ),
            Operation.UPGRADE: Binding(Owner.FOUNDATION, lambda tx, ref: self.store.upgrade()),
            Operation.CHECK: Binding(Owner.FOUNDATION, lambda tx, ref: self.store.check()),
            Operation.START: Binding(Owner.FOUNDATION, lambda tx, ref: self.store.check()),
        }
        self.operations = OperationBoundary(
            bindings | registry.bindings() | coordination.bindings(),
            LocalOperatorPolicy(),
            LOCAL_OPERATOR,
            self.store,
        )

    def close(self):
        self.store.close()
