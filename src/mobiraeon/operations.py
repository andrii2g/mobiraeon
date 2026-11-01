"""One internal controlled path. Binding and trusted context come from composition."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from uuid import uuid4

from mobiraeon.contracts import (
    CallerContext,
    Operation,
    OperationResult,
    Outcome,
    Owner,
    PermissionPolicy,
    RevisionRef,
)
from mobiraeon.errors import Reason, SafeError
from mobiraeon.persistence import Store, TransactionAcquisitionFailure, TransactionFailure


@dataclass(frozen=True)
class Binding:
    owner: Owner
    handler: Callable | None = None
    transactional: bool = False
    requires_target: bool = False
    validator: Callable | None = None
    business: bool = False


class OperationBoundary:
    def __init__(
        self,
        bindings: Mapping[Operation, Binding],
        policy: PermissionPolicy,
        caller: CallerContext | None,
        store: Store,
    ):
        if any(not isinstance(code, Operation) for code in bindings):
            raise ValueError("recognized operation bindings required")
        self._bindings = MappingProxyType(dict(bindings))
        self._policy = policy
        self._caller = caller
        self._store = store

    def invoke(self, code, *, target=None, inputs=None):
        invocation = uuid4()
        operation = None
        validated_target = None
        data = None

        def result(outcome, reason):
            return OperationResult(
                invocation,
                operation,
                outcome,
                reason,
                self._caller.actor if self._caller else None,
                validated_target,
                data=data if outcome == Outcome.SUCCESS else None,
            )

        try:
            operation = Operation(code)
        except ValueError, TypeError:
            return result(Outcome.INVALID, Reason.INVALID_INPUT)
        binding = self._bindings.get(operation)
        if binding and binding.business:
            try:
                binding.validator(target, inputs)
            except Exception:
                return result(Outcome.INVALID, Reason.INVALID_INPUT)
        elif inputs not in (None, {}) or (
            target is not None and not isinstance(target, RevisionRef)
        ):
            return result(Outcome.INVALID, Reason.INVALID_INPUT)
        if binding and binding.requires_target and target is None:
            return result(Outcome.INVALID, Reason.INVALID_INPUT)
        if binding and not binding.requires_target and target is not None:
            return result(Outcome.INVALID, Reason.INVALID_INPUT)
        validated_target = target
        if self._caller is None or self._policy is None:
            return result(Outcome.REFUSED, Reason.REFUSED)
        try:
            # Current policy is consulted on every call, including historical refs.
            permitted = self._policy.permits(self._caller, operation, validated_target)
        except Exception:
            # The protected handler has not run. A failed policy dependency must
            # never grant permission or escape the attributable result boundary.
            return result(Outcome.UNAVAILABLE, Reason.UNAVAILABLE)
        if permitted is not True:
            return result(Outcome.REFUSED, Reason.REFUSED)
        try:
            if binding is None or binding.handler is None:
                return result(Outcome.UNAVAILABLE, Reason.UNAVAILABLE)
            if binding.transactional:
                with self._store.transaction() as transaction:
                    # Restrictions may have changed while waiting for the writer lock.
                    check = getattr(self._policy, "permits_in_transaction", None)
                    allowed = (
                        check(self._caller, operation, validated_target, transaction)
                        if check
                        else self._policy.permits(self._caller, operation, validated_target)
                    )
                    if allowed is not True:
                        return result(Outcome.REFUSED, Reason.REFUSED)
                    if binding.business:
                        data = binding.handler(
                            transaction, validated_target, inputs, invocation
                        )
                    else:
                        binding.handler(transaction, validated_target)
            else:
                binding.handler(None, validated_target)
            return result(Outcome.SUCCESS, Reason.OK)
        except TransactionAcquisitionFailure:
            return result(Outcome.UNAVAILABLE, Reason.STORAGE_FAILURE)
        except TransactionFailure as error:
            if error.rolled_back and error.reason is not None:
                outcome = {
                    Reason.REFUSED: Outcome.REFUSED,
                    Reason.AUTHENTICATION: Outcome.REFUSED,
                    Reason.INVALID_INPUT: Outcome.INVALID,
                    Reason.UNAVAILABLE: Outcome.UNAVAILABLE,
                }.get(error.reason, Outcome.FAILURE)
                return result(outcome, error.reason)
            return result(
                Outcome.FAILURE if error.rolled_back else Outcome.UNCERTAIN,
                Reason.ROLLED_BACK if error.rolled_back else Reason.UNCERTAIN,
            )
        except SafeError as error:
            # Only foundation lifecycle handlers raise this controlled error type.
            # Migration failures still have their own per-migration effect boundary.
            if (
                binding is None
                or binding.owner != Owner.FOUNDATION
                or error.reason == Reason.UNCERTAIN
            ):
                return result(Outcome.UNCERTAIN, Reason.UNCERTAIN)
            return result(Outcome.FAILURE, error.reason)
        except Exception:
            return result(Outcome.UNCERTAIN, Reason.UNCERTAIN)
