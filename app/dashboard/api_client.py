"""
Cliente HTTP interno para o dashboard consumir a própria API REST.

Delega todas as chamadas para a mesma instância FastAPI via ASGI
(TestClient) quando rodando em modo single-process (recomendado para o
streamlit local), ou via HTTP quando ``API_BASE_URL`` está configurado.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_API_BASE: str | None = None


def configure(*, api_base_url: str | None = None) -> None:
    global _API_BASE
    _API_BASE = api_base_url


def _url(path: str) -> str:
    if _API_BASE is None:
        raise RuntimeError("API client not configured. Call configure() first.")
    return f"{_API_BASE.rstrip('/')}/{path.lstrip('/')}"


# In-process shortcut (fastest option for local dashboards)
_client = None

def _get_client():
    global _client
    if _client is None:
        # Lazy import so the dashboard can start without
        # instantiating the full app if we only hit HTTP.
        from fastapi.testclient import TestClient

        from app.main import create_app

        _client = TestClient(create_app())
    return _client


def get(path: str, *, params: dict | None = None) -> dict:
    """GET a JSON endpoint."""
    if _API_BASE is not None:
        import requests

        r = requests.get(_url(path), params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    # In-process
    params = params or {}
    r = _get_client().request("GET", path, params=params)
    r.raise_for_status()
    return r.json()


def post(path: str, *, json: dict | None = None) -> dict:
    """POST a JSON endpoint."""
    if _API_BASE is not None:
        import requests

        r = requests.post(_url(path), json=json, timeout=30)
        r.raise_for_status()
        return r.json()
    r = _get_client().request("POST", path, json=json)
    r.raise_for_status()
    return r.json()


def patch(path: str, *, json: dict | None = None) -> dict:
    """PATCH a JSON endpoint."""
    if _API_BASE is not None:
        import requests

        r = requests.patch(_url(path), json=json, timeout=30)
        r.raise_for_status()
        return r.json()
    r = _get_client().request("PATCH", path, json=json)
    r.raise_for_status()
    return r.json()


def delete(path: str) -> None:
    """DELETE a JSON endpoint."""
    if _API_BASE is not None:
        import requests

        r = requests.delete(_url(path), timeout=30)
        r.raise_for_status()
        return
    r = _get_client().request("DELETE", path)
    r.raise_for_status()
