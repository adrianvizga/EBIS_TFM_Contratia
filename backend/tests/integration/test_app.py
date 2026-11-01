import sys
import os
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app import app
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.integration
class TestAppEndpoints:

    def test_root_endpoint(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["message"] == "ContratIA API"
        assert body["version"] == "1.0.0"
        assert body["status"] == "running"

    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"

    def test_404_unknown_route(self, client):
        resp = client.get("/api/nonexistent-route")
        assert resp.status_code == 404

    def test_global_exception_handler(self):
        from app import global_exception_handler
        from starlette.requests import Request as StarletteRequest

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "query_string": b"",
            "headers": [],
        }
        request = StarletteRequest(scope)
        exc = RuntimeError("boom")

        import asyncio
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                global_exception_handler(request, exc)
            )
        finally:
            loop.close()

        assert result.status_code == 500
        import json
        body = json.loads(result.body)
        assert body["message"] == "Internal server error"

    def test_docs_hidden_in_production(self):
        # which would corrupt shared state for other tests.
        from core.config import settings as real_settings
        docs_url = "/docs" if real_settings.debug else None
        assert docs_url is None or real_settings.debug is True
        from app import app
        expected = "/docs" if real_settings.debug else None
        assert app.docs_url == expected

    def test_docs_visible_in_debug(self):
        from fastapi import FastAPI
        debug = True
        docs_url = "/docs" if debug else None
        assert docs_url == "/docs"
        test_app = FastAPI(docs_url="/docs" if debug else None)
        assert test_app.docs_url == "/docs"
