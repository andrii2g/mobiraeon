"""Fixture route metadata controls, not a substitute for actual provider evidence."""

from types import SimpleNamespace

import pytest

from mobiraeon.forge_gitea_verification import PUBLISHED_LOOPBACK, published_route


@pytest.mark.parametrize("change", ["none", "private", "unready", "binding", "mixed"])
def test_affirmative_publication_requires_the_actual_published_upstream(change):
    origin = f"http://{PUBLISHED_LOOPBACK}:31001"
    publication = dict(
        ownership_verified=True,
        running=True,
        ready_on_published_endpoint=True,
        origin=origin,
        port=31001,
        inspected_bindings=[{"HostIp": PUBLISHED_LOOPBACK, "HostPort": "31001"}],
    )
    proxy = SimpleNamespace(
        upstream=origin,
        routes=[{"upstream": origin, "method": "POST", "path": "/api/v1/example"}],
    )
    if change == "private":
        proxy.upstream = "http://172.30.0.2:3000"
    if change == "unready":
        publication["ready_on_published_endpoint"] = False
    if change == "binding":
        publication["inspected_bindings"] = [{"HostIp": "0.0.0.0", "HostPort": "31001"}]
    if change == "mixed":
        proxy.routes.append({"upstream": "http://172.30.0.2:3000"})
    assert published_route(publication, proxy) == (change == "none")


@pytest.mark.parametrize(
    "case", ["transient", "sustained", "unavailable", "wrong_version", "non_200"]
)
def test_startup_budget_prefers_published_without_hiding_sustained_failure(case, monkeypatch):
    import httpx2

    import mobiraeon.forge_gitea_verification as verification

    clock = SimpleNamespace(now=0.0)
    monkeypatch.setattr(verification.time, "monotonic", lambda: clock.now)
    monkeypatch.setattr(
        verification.time, "sleep", lambda n: setattr(clock, "now", clock.now + n)
    )
    calls = []
    published = "http://127.0.0.2:31001"
    private = "http://172.30.0.2:3000"

    class Client:
        published_calls = 0

        def get(self, url, *, timeout):
            assert 0 < timeout <= 1
            calls.append((url, clock.now, timeout))
            clock.now += min(0.05, timeout)
            if url.startswith(published):
                self.published_calls += 1
                if case in {"sustained", "unavailable"} or (
                    case == "transient" and self.published_calls <= 2
                ):
                    raise httpx2.ConnectError("controlled startup refusal")
                return httpx2.Response(
                    503 if case == "non_200" else 200,
                    json={"version": "29.0.0" if case == "wrong_version" else "28.2.0"},
                )
            if case == "unavailable":
                raise httpx2.ConnectError("controlled private refusal")
            return httpx2.Response(200, json={"version": "28.2.0"})

    observations = []
    if case == "wrong_version":
        with pytest.raises(AssertionError):
            verification.await_fixture_api(Client(), published, private, observations)
        return
    response, selected = verification.await_fixture_api(
        Client(), published, private, observations
    )
    assert clock.now <= 25.000001 and calls and observations
    if case == "transient":
        assert selected == published and response.json() == {"version": "28.2.0"}
        assert len([u for u, _, _ in calls if u.startswith(published)]) == 3
        assert any(o["origin"] == private for o in observations)
    elif case == "sustained":
        assert selected == private and response.status_code == 200 and clock.now >= 25
        assert len([u for u, _, _ in calls if u.startswith(private)]) == 1
    elif case == "unavailable":
        assert response is None and selected == published and clock.now >= 25
    else:
        assert response.status_code == 503 and selected == published and clock.now >= 25
        assert all(u.startswith(published) for u, _, _ in calls)


@pytest.mark.parametrize(
    "case",
    [
        "non_200",
        "positive",
        "transient",
        "private",
        "unavailable",
        "malformed",
        "wrong_version",
    ],
)
def test_connected_exercise_startup_requires_http_200_and_exact_version(case):
    from mobiraeon.verification_repair_controls import readiness_case

    result = readiness_case(case)
    assert result["required_behavior"], result
    assert not result["later_provider_assertions_executed"]
