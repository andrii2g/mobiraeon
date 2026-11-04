"""Forge-neutral observations and the bounded, zero-retry Gitea 28.2.0 adapter."""

import asyncio
import ssl
import time
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import quote, urlsplit

import httpx2

from mobiraeon.errors import Reason, SafeError
from mobiraeon.forge_schema import decode, native, strict_int


@dataclass(frozen=True)
class Issue:
    identity: str
    number: int
    state: str


@dataclass(frozen=True)
class Comment:
    identity: str
    issue: str
    author: str
    body: str


class ForgeAdapter(Protocol):
    capabilities: frozenset[str]

    async def preflight(self, number: int) -> Issue: ...
    async def comment(self, identity: str) -> Comment | None: ...
    async def comments(self) -> list[Comment]: ...
    async def publish(self, method: str, identity: str | None, body: str) -> Comment: ...

    def destination(self, method: str, identity: str | None) -> str: ...

    def check_write(self, body: str) -> None: ...


class Gitea:
    capabilities = frozenset(
        {"ordinary_issue", "managed_comment", "complete_lookup", "cooperative_editing"}
    )

    def __init__(self, definition, token, *, admitted=None):
        self.definition = definition
        self.limits = definition["limits"]
        self.deadline = (admitted if admitted is not None else time.monotonic()) + self.limits[
            "cycle_seconds"
        ]
        self.network_deadline = self.deadline - self.limits["finalization_seconds"]
        self.requests = self.pages = self.read_bytes = 0
        self.token = token
        repo = definition["repository"]
        self.repo_path = (
            "/repos/" + quote(repo["owner"], safe="") + "/" + quote(repo["name"], safe="")
        )
        self.origin = definition["origin"]
        self.issue = None
        self.client = None
        self.write_started = False

    async def __aenter__(self):
        ca_file = self.definition["tls_ca_file"]
        context = (
            ssl.create_default_context(cafile=ca_file)
            if ca_file is not None
            else httpx2.create_ssl_context(trust_env=False)
        )
        transport = httpx2.AsyncHTTPTransport(retries=0, trust_env=False, verify=context)
        self.client = httpx2.AsyncClient(
            transport=transport,
            trust_env=False,
            follow_redirects=False,
            timeout=self.limits["request_seconds"],
            headers={"Authorization": "token " + self.token, "Accept-Encoding": "identity"},
        )
        return self

    async def __aexit__(self, *exc):
        try:
            async with asyncio.timeout_at(self.deadline):
                await self.client.aclose()
        except Exception:
            raise SafeError(Reason.CLEANUP_FAILED) from None

    async def request(self, method, path, *, body=None, lookup=False):
        if (
            self.requests >= self.limits["max_requests"]
            or time.monotonic() >= self.network_deadline
            or (lookup and self.pages >= self.limits["max_pages"])
        ):
            raise SafeError(Reason.UNAVAILABLE)
        allowed = {("GET", "/version"), ("GET", "/user"), ("GET", self.repo_path)}
        if self.issue:
            base = self.repo_path + "/issues/" + str(self.issue.number)
            allowed |= {
                ("GET", base),
                ("GET", base + "/comments"),
                ("POST", base + "/comments"),
            }
        if path.startswith(self.repo_path + "/issues/comments/"):
            native(path.rsplit("/", 1)[1])
            allowed |= {("GET", path), ("PATCH", path)}
        if (method, path) not in allowed:
            raise SafeError(Reason.REFUSED)
        if method in {"POST", "PATCH"} and (
            not isinstance(body, str)
            or len(body.encode()) > self.limits["comment_bytes"]
            or self.write_started
        ):
            raise SafeError(Reason.UNAVAILABLE)
        self.requests += 1
        self.pages += int(lookup)
        deadline = min(time.monotonic() + self.limits["request_seconds"], self.network_deadline)
        async with asyncio.timeout_at(deadline):
            if method != "GET":
                self.write_started = True
            async with self.client.stream(
                method,
                self.origin + "/api/v1" + path,
                **({"json": {"body": body}} if body is not None else {}),
            ) as response:
                if response.headers.get("content-encoding", "identity").lower() != "identity":
                    raise SafeError(Reason.UNAVAILABLE)
                data = bytearray()
                async for chunk in response.aiter_raw(chunk_size=4096):
                    self.read_bytes += len(chunk)
                    if (
                        len(data) + len(chunk) > self.limits["response_bytes"]
                        or self.read_bytes > self.limits["total_read_bytes"]
                    ):
                        raise SafeError(Reason.UNAVAILABLE)
                    data.extend(chunk)
                if response.status_code == 404 and method == "GET":
                    return None, response.headers
                if response.status_code not in ({200} if method == "GET" else {200, 201}):
                    # No generic status is treated as proof of a rejected write.
                    raise SafeError(Reason.UNAVAILABLE)
                return decode(bytes(data), self.limits["response_bytes"]), response.headers

    async def preflight(self, number):
        strict_int(number)
        version, _ = await self.request("GET", "/version")
        if not isinstance(version, dict) or version.get("version") != "28.2.0":
            raise SafeError(Reason.UNAVAILABLE)
        user, _ = await self.request("GET", "/user")
        repo, _ = await self.request("GET", self.repo_path)
        if (
            not isinstance(user, dict)
            or not isinstance(repo, dict)
            or str(strict_int(user.get("id"))) != self.definition["account"]["id"]
            or user.get("login") != self.definition["account"]["name"]
            or str(strict_int(repo.get("id"))) != self.definition["repository"]["id"]
            or repo.get("name") != self.definition["repository"]["name"]
            or repo.get("owner", {}).get("login") != self.definition["repository"]["owner"]
        ):
            raise SafeError(Reason.CONFLICT)
        self.issue = Issue("unverified", number, "unknown")
        item, _ = await self.request("GET", self.repo_path + "/issues/" + str(number))
        if (
            not isinstance(item, dict)
            or item.get("pull_request") is not None
            or strict_int(item.get("number")) != number
            or not self.matches_html_url(item.get("html_url"), number)
            or item.get("state") not in {"open", "closed"}
        ):
            raise SafeError(Reason.CONFLICT)
        self.issue = Issue(str(strict_int(item.get("id"))), number, item["state"])
        return self.issue

    def html_url(self, number):
        return self.origin + self.repo_path.removeprefix("/repos") + "/issues/" + str(number)

    def matches_html_url(self, value, number):
        if (
            not isinstance(value, str)
            or "?" in value
            or "#" in value
            or any(ord(c) <= 32 or ord(c) == 127 for c in value)
        ):
            return False
        try:
            observed, expected = urlsplit(value), urlsplit(self.html_url(number))

            def origin(parts):
                port = (
                    parts.port
                    if parts.port is not None
                    else (443 if parts.scheme == "https" else 80)
                )
                return parts.scheme, parts.hostname.lower() if parts.hostname else None, port

            return (
                observed.username is None
                and observed.password is None
                and origin(observed) == origin(expected)
                and observed.path == expected.path
            )
        except ValueError:
            return False

    def normalize(self, item):
        if (
            not isinstance(item, dict)
            or not self.matches_html_url(item.get("issue_url"), self.issue.number)
            or item.get("pull_request_url") not in {None, ""}
            or not isinstance(item.get("body"), str)
        ):
            raise SafeError(Reason.CONFLICT)
        return Comment(
            str(strict_int(item.get("id"))),
            self.issue.identity,
            str(strict_int(item.get("user", {}).get("id"))),
            item["body"],
        )

    async def comment(self, identity):
        native(identity)
        item, _ = await self.request("GET", self.repo_path + "/issues/comments/" + identity)
        if item is None:
            return None
        observed = self.normalize(item)
        if observed.identity != identity:
            raise SafeError(Reason.CONFLICT)
        return observed

    async def comments(self):
        items, headers = await self.request(
            "GET",
            self.repo_path + "/issues/" + str(self.issue.number) + "/comments",
            lookup=True,
        )
        count = headers.get("x-total-count", "")
        if not isinstance(items, list) or not count.isascii() or not count.isdecimal():
            raise SafeError(Reason.UNAVAILABLE)
        comments = [self.normalize(item) for item in items]
        if int(count) != len(comments) or len({c.identity for c in comments}) != len(comments):
            raise SafeError(Reason.UNAVAILABLE)
        return comments

    async def publish(self, method, identity, body):
        path = (
            self.repo_path + "/issues/" + str(self.issue.number) + "/comments"
            if method == "POST"
            else self.repo_path + "/issues/comments/" + native(identity)
        )
        item, _ = await self.request(method, path, body=body)
        comment = self.normalize(item)
        if (
            comment.author != self.definition["account"]["id"]
            or comment.body != body
            or (method == "PATCH" and comment.identity != identity)
        ):
            raise SafeError(Reason.CONFLICT)
        return comment

    def check_write(self, body):
        if (
            self.write_started
            or self.requests >= self.limits["max_requests"]
            or time.monotonic() >= self.network_deadline
            or self.read_bytes >= self.limits["total_read_bytes"]
            or len(body.encode()) > self.limits["comment_bytes"]
        ):
            raise SafeError(Reason.UNAVAILABLE)

    def destination(self, method, identity):
        path = (
            self.repo_path + "/issues/" + str(self.issue.number) + "/comments"
            if method == "POST"
            else self.repo_path + "/issues/comments/" + native(identity)
        )
        return self.origin + "/api/v1" + path
