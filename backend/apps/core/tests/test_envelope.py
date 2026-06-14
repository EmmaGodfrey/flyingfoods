"""Tests for the global response envelope and error shape."""

import pytest

pytestmark = pytest.mark.django_db


def test_success_envelope(auth_client):
    """A successful response renders as {success: true, data: ...}.

    The envelope is applied by the renderer, so it appears in the rendered
    JSON body rather than the pre-render `response.data`.
    """
    client = auth_client("ADMIN")
    resp = client.get("/api/locations/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "data" in body


def test_auth_required_envelope(api_client):
    """An unauthenticated request returns the error envelope with a code."""
    resp = api_client.get("/api/users/")
    assert resp.status_code == 401
    assert resp.data["success"] is False
    assert resp.data["error"]["code"] == "AUTH_REQUIRED"


def test_forbidden_role_envelope(auth_client):
    """A non-admin hitting an admin endpoint gets FORBIDDEN_ROLE."""
    client = auth_client("WAITER")
    resp = client.get("/api/users/")
    assert resp.status_code == 403
    assert resp.data["error"]["code"] == "FORBIDDEN_ROLE"
