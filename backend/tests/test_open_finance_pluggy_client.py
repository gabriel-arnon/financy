from types import SimpleNamespace

import pytest

from app.services.pluggy_client import PluggyClient, PluggyClientError


def settings(**overrides):
    values = {
        "pluggy_base_url": "https://api.pluggy.ai",
        "pluggy_client_id": "client",
        "pluggy_client_secret": "secret",
        "pluggy_api_timeout_seconds": 1,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_authenticate_caches_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    client = PluggyClient(settings())
    calls = []

    def fake_request(method, path, **kwargs):
        calls.append((method, path, kwargs))
        return {"apiKey": "pluggy-key", "expiresIn": 7200}

    monkeypatch.setattr(client, "_request", fake_request)

    assert client.authenticate() == "pluggy-key"
    assert client.authenticate() == "pluggy-key"
    assert len(calls) == 1
    assert calls[0][0] == "POST"
    assert calls[0][1] == "/auth"


def test_authenticate_requires_credentials() -> None:
    client = PluggyClient(settings(pluggy_client_id=None))

    with pytest.raises(PluggyClientError):
        client.authenticate()


def test_paginated_get_collects_results(monkeypatch: pytest.MonkeyPatch) -> None:
    client = PluggyClient(settings())
    monkeypatch.setattr(client, "authenticate", lambda: "pluggy-key")

    def fake_request(method, path, **kwargs):
        page = kwargs["params"]["page"]
        if page == 1:
            return {"results": [{"id": "a"}], "totalPages": 2}
        return {"results": [{"id": "b"}], "totalPages": 2}

    monkeypatch.setattr(client, "_request", fake_request)

    assert client.list_accounts("item-1") == [{"id": "a"}, {"id": "b"}]
