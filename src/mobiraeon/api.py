"""Authenticated transport only. No identity or authorization comes from request data."""

import asyncio
import contextlib
import ipaddress
import json
import logging
import os
import signal
import ssl
import threading
import time
from dataclasses import asdict
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from mobiraeon.access import credential_proof
from mobiraeon.contracts import OperationResult, Outcome
from mobiraeon.errors import Reason, SafeError
from mobiraeon.registry_schema import fields, load_json


def status(result):
    if result.reason == Reason.AUTHENTICATION:
        return 401
    if result.reason == Reason.NOT_FOUND:
        return 404
    if result.reason in {Reason.CONFLICT, Reason.INCOMPLETE, Reason.REVIEW}:
        return 409
    return {
        "success": 200,
        "invalid_input": 422,
        "refused": 403,
        "unavailable": 503,
        "known_failure": 500,
        "uncertain_effects": 202,
    }[result.outcome.value]


def create_api(service):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.admitting = True
    app.state.active = 0

    def safe_response(outcome, reason, code):
        result = OperationResult(uuid4(), None, outcome, reason)
        return JSONResponse(json.loads(json.dumps(asdict(result), default=str)), code)

    def authenticate(request):
        if request.url.scheme != "https":
            raise SafeError(Reason.TLS)
        header = request.headers.get("authorization", "")
        if not header.startswith("Bearer "):
            raise SafeError(Reason.AUTHENTICATION)
        return credential_proof(header[7:])

    @app.exception_handler(Exception)
    async def failure(request, error):
        return safe_response(Outcome.UNCERTAIN, Reason.INTERNAL, 500)

    @app.get("/v1/openapi.json", include_in_schema=False)
    async def openapi(request: Request):
        try:
            proof = authenticate(request)
            with service.store.engine.connect() as tx:
                if service.access.authenticate(tx, proof) is None:
                    raise SafeError(Reason.AUTHENTICATION)
            return JSONResponse(app.openapi())
        except SafeError:
            return safe_response(Outcome.REFUSED, Reason.AUTHENTICATION, 401)

    @app.post(
        "/v1/operations",
        openapi_extra={
            "security": [{"personalToken": []}],
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["operation", "target", "inputs"],
                            "properties": {
                                "operation": {
                                    "type": "string",
                                    "description": "Action from registry-contracts.md; "
                                    "protected setup/recovery are local only.",
                                },
                                "target": {
                                    "type": "object",
                                    "required": ["kind", "entity_kind", "identity"],
                                    "additionalProperties": False,
                                    "properties": {
                                        "kind": {"type": "string"},
                                        "entity_kind": {"type": "string"},
                                        "identity": {"type": "string"},
                                        "revision": {"type": ["string", "null"]},
                                    },
                                },
                                "inputs": {
                                    "type": "object",
                                    "description": "Strict action-specific input; "
                                    "see registry-contracts.md.",
                                },
                            },
                        }
                    }
                },
            },
            "responses": {
                str(code): {"description": description}
                for code, description in {
                    200: "Success",
                    202: "Uncertain effects; reconcile before retry",
                    401: "Authentication required",
                    403: "Current grant refused",
                    404: "Missing reference",
                    409: "Conflict/incomplete/review inapplicable",
                    422: "Invalid input",
                    500: "Known failure",
                    503: "Unavailable",
                }.items()
            },
        },
    )
    async def operation(request: Request):
        if not app.state.admitting:
            return safe_response(Outcome.UNAVAILABLE, Reason.DRAIN, 503)
        try:
            proof = authenticate(request)
            content = bytearray()
            async for chunk in request.stream():
                content.extend(chunk)
                if len(content) > 65536:
                    raise SafeError(Reason.INVALID_INPUT)
            document = load_json(content)
            fields(
                document, {"operation", "target", "inputs"}, {"operation", "target", "inputs"}
            )
            # Protected owner bootstrap/recovery are never available over HTTP.
            if document["operation"] in {"access.setup", "access.recover"}:
                raise SafeError(Reason.REFUSED)
        except SafeError as error:
            code = 401 if error.reason == Reason.AUTHENTICATION else 422
            return safe_response(
                Outcome.REFUSED if code == 401 else Outcome.INVALID, error.reason, code
            )
        app.state.active += 1

        def invoke():
            return service.invoke(
                document["operation"], document["target"], document["inputs"], proof=proof
            )

        loop = asyncio.get_running_loop()
        task = loop.create_future()

        def finish(result=None, error=None):
            app.state.active -= 1
            if not task.done():
                if error is None:
                    task.set_result(result)
                else:
                    task.set_exception(error)

        def work():
            try:
                result, error = invoke(), None
            except Exception as caught:
                result, error = None, caught
            try:
                loop.call_soon_threadsafe(finish, result, error)
            except RuntimeError:
                # Deadline has closed the loop. The process reports uncertainty.
                pass

        threading.Thread(target=work, daemon=True).start()

        def finished(completed):
            # Consume failures even if client disconnected. Never infer rollback.
            if not completed.cancelled():
                completed.exception()

        task.add_done_callback(finished)
        result = await asyncio.shield(task)
        return JSONResponse(json.loads(json.dumps(asdict(result), default=str)), status(result))

    schema = app.openapi()
    schema.setdefault("components", {}).setdefault("securitySchemes", {})["personalToken"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "mbr personal token",
    }
    return app


class Server(uvicorn.Server):
    @contextlib.contextmanager
    def capture_signals(self):
        yield


def host(service, configuration, ready):
    settings = configuration.api
    try:
        if (
            not settings["allow_remote"]
            and not ipaddress.ip_address(settings["host"]).is_loopback
        ):
            raise ValueError()
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(settings["cert_file"], settings["key_file"])
        service.private.verify()
    except Exception:
        raise SafeError(Reason.TLS) from None
    app = create_api(service)
    # Uvicorn must not emit exception text, request headers, URLs or tracebacks.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers = [logging.NullHandler()]
        logger.propagate = False
    config = uvicorn.Config(
        app,
        host=settings["host"],
        port=settings["port"],
        ssl_certfile=str(settings["cert_file"]),
        ssl_keyfile=str(settings["key_file"]),
        access_log=False,
        log_config=None,
        proxy_headers=False,
        server_header=False,
        timeout_graceful_shutdown=settings["drain_timeout_seconds"],
    )
    server = Server(config)
    previous = {}

    def stop(signum, frame):
        app.state.admitting = False
        server.should_exit = True

    async def run():
        task = asyncio.create_task(server.serve())
        deadline = time.monotonic() + settings["startup_timeout_seconds"]
        while not server.started:
            if task.done():
                await task
                raise SafeError(Reason.TLS)
            if time.monotonic() >= deadline:
                server.should_exit = True
                await task
                raise SafeError(Reason.UNAVAILABLE)
            await asyncio.sleep(0.02)
        ready()
        await task
        if app.state.active:
            raise SafeError(Reason.DRAIN)

    try:
        for sig in (
            signal.SIGINT,
            signal.SIGTERM,
            *((signal.SIGBREAK,) if os.name == "nt" else ()),
        ):
            previous[sig] = signal.signal(sig, stop)
        asyncio.run(run())
    except SystemExit:
        raise SafeError(Reason.TLS) from None
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
