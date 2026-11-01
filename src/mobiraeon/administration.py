"""CLI adapters: secrets are read from protected files, never arguments/results."""

import json
import os
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from uuid import UUID, uuid4

from mobiraeon.access import audit, credential_proof
from mobiraeon.bootstrap import PreparationStopped, prepare, read_package
from mobiraeon.catalog import RegistryService
from mobiraeon.contracts import (
    BusinessData,
    BusinessTarget,
    EntityId,
    Operation,
    OperationResult,
    Outcome,
)
from mobiraeon.errors import Reason, SafeError
from mobiraeon.private_state import PrivateState
from mobiraeon.registry_schema import fields, load_json, validate_request


def service_for(application):
    config = application.configuration
    return RegistryService(
        application.store, PrivateState(config.private_dir, config.database_path)
    )


def administer(application, options):
    command = options["command"]
    service = service_for(application)
    config = application.configuration
    if command == "provision":
        installation = service.private.provision()
        return OperationResult(
            uuid4(),
            None,
            Outcome.SUCCESS,
            Reason.OK,
            data=BusinessData(
                reference=installation,
                state="private_state_provisioned",
                audit_status="not_applicable",
            ),
        )
    if command == "prepare":
        proof = credential_proof(service.private.read_credential(config.credential_file))
        try:
            input_path = Path(options["input_file"])
        except KeyError, TypeError, ValueError:
            raise SafeError(Reason.INVALID_INPUT) from None
        package = read_package(input_path)
        try:
            record = prepare(service, package, proof)
            return OperationResult(
                uuid4(),
                None,
                Outcome.SUCCESS,
                Reason.OK,
                data=BusinessData(
                    (record,),
                    state="prepared_disabled_unqualified",
                    audit_status="operations_recorded",
                ),
            )
        except PreparationStopped as stopped:
            return stopped.result
    try:
        request = load_json(Path(options["request_file"]).read_bytes())
    except OSError, KeyError, ValueError, TypeError:
        raise SafeError(Reason.INVALID_INPUT) from None
    fields(request, {"operation", "target", "inputs"}, {"operation", "target", "inputs"})
    if command == "cleanup":
        if request["operation"] != "access.reconcile":
            raise SafeError(Reason.INVALID_INPUT)
        proof = service.access.owner_proof()
        try:
            target = BusinessTarget(**request["target"])
        except KeyError, ValueError, TypeError:
            raise SafeError(Reason.INVALID_INPUT) from None
        validate_request(Operation.ACCESS_RECONCILE, target, request["inputs"])
        try:
            with service.private.credential_lifecycle():
                return _cleanup_locked(service, request, options, proof)
        except SafeError as error:
            if error.reason not in {Reason.UNAVAILABLE, Reason.CLEANUP_FAILED}:
                raise
            return service._attempt_audit(
                OperationResult(
                    uuid4(),
                    Operation.ACCESS_RECONCILE,
                    Outcome.UNAVAILABLE
                    if error.reason == Reason.UNAVAILABLE
                    else Outcome.UNCERTAIN,
                    error.reason,
                    actor=EntityId("installation-owner", proof.principal),
                    target=target,
                )
            )
    if command in {"setup", "recover"}:
        if request["operation"] != "access." + command:
            raise SafeError(Reason.INVALID_INPUT)
        proof = service.access.owner_proof()
    else:
        raw = service.private.read_credential(config.credential_file)
        proof = credential_proof(raw)
    if command == "coordination":
        from mobiraeon.coordination import Coordinator

        return Coordinator(application.store, service.private).invoke(
            request["operation"], request["target"], request["inputs"], proof=proof
        )
    if command == "remote":
        try:
            settings = config.api
            context = ssl.create_default_context(cafile=str(settings["client_ca"]))
            request_object = urllib.request.Request(
                settings["client_url"].rstrip("/") + "/v1/operations",
                data=json.dumps(request).encode(),
                headers={"Authorization": "Bearer " + raw, "Content-Type": "application/json"},
            )

            # No redirects: never forward the credential to another origin.
            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, req, fp, code, msg, headers, newurl):
                    return None

            opener = urllib.request.build_opener(
                NoRedirect(), urllib.request.HTTPSHandler(context=context)
            )
            try:
                response = opener.open(request_object, timeout=60)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                result = json.loads(response.read(1048576))
            return OperationResult(
                UUID(result["invocation_id"]),
                Operation(result["operation"]) if result["operation"] else None,
                Outcome(result["outcome"]),
                Reason(result["reason"]),
                actor=EntityId(**result["actor"]) if result.get("actor") else None,
                target=BusinessTarget(**result["target"]) if result.get("target") else None,
                data=BusinessData(**result["data"]) if result.get("data") else None,
            )
        except Exception:
            # Request may have reached the server. Reconcile before replay.
            return OperationResult(uuid4(), None, Outcome.UNCERTAIN, Reason.TLS)
    return service.invoke(
        request["operation"], request["target"], request["inputs"], proof=proof
    )


def _cleanup_locked(service, request, options, proof):
    result = service.invoke(
        request["operation"], request["target"], request["inputs"], proof=proof
    )
    if result.outcome != Outcome.SUCCESS:
        return result
    record = result.data.records[0]
    if record.get("state") != "not_registered" and record.get("revoked") is None:
        raise SafeError(Reason.REFUSED)
    path = service.private.credential_path(options["credential_name"])
    delivered = credential_proof(service.private.read_credential(path))
    if delivered.identifier != request["target"]["identity"]:
        raise SafeError(Reason.INVALID_INPUT)
    try:
        path.unlink()
        if os.name != "nt":
            descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        with service.store.transaction() as tx:
            audit(
                tx,
                result.invocation_id,
                Operation.ACCESS_RECONCILE,
                proof.principal,
                request["target"],
                Outcome.SUCCESS,
                Reason.OK,
                {"event": "credential_file_removed", "credential_id": delivered.identifier},
            )
    except Exception:
        return OperationResult(
            result.invocation_id, None, Outcome.UNCERTAIN, Reason.CLEANUP_FAILED
        )
    return OperationResult(
        result.invocation_id,
        None,
        Outcome.SUCCESS,
        Reason.OK,
        data=BusinessData(reference=delivered.identifier, state="credential_file_removed"),
    )
