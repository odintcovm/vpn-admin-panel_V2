import os
import sys

from fastapi.testclient import TestClient

os.environ.setdefault("SCHEMA_MANAGEMENT_MODE", "bootstrap")
os.environ.setdefault("APP_ENV", "development")

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.core.config import get_settings
from app.main import app


BASE_HEADERS = {"x-api-token": "admin-token"}


def _headers(role: str | None = None) -> dict[str, str]:
    headers = dict(BASE_HEADERS)
    if role:
        headers["x-role"] = role
    return headers


def _reset_settings_cache():
    get_settings.cache_clear()


def test_dashboard_overview():
    with TestClient(app) as client:
        response = client.get("/api/dashboard/overview", headers=BASE_HEADERS)
        assert response.status_code == 200
        assert "total_links" in response.json()


def test_links_crud_minimal():
    with TestClient(app) as client:
        create = client.post("/api/links", headers=BASE_HEADERS, json={"name": "Smoke Link", "tag": "Test device", "enabled": True})
        assert create.status_code == 200
        link_id = create.json()["id"]

        patch = client.patch(f"/api/links/{link_id}", headers=BASE_HEADERS, json={"name": "Smoke Link Updated"})
        assert patch.status_code == 200

        delete = client.delete(f"/api/links/{link_id}", headers=BASE_HEADERS)
        assert delete.status_code == 200


def test_auth_me_blocks_x_role_when_emulation_disabled(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEV_ROLE_EMULATION", "false")
    _reset_settings_cache()

    with TestClient(app) as client:
        response = client.get("/api/auth/me", headers=_headers("readonly"))

    assert response.status_code == 403
    assert response.json()["detail"]["error"]["code"] == "DEV_ROLE_EMULATION_DISABLED"


def test_auth_me_allows_x_role_in_dev_when_enabled(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DEV_ROLE_EMULATION", "true")
    _reset_settings_cache()

    with TestClient(app) as client:
        response = client.get("/api/auth/me", headers=_headers("readonly"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["role"] == "readonly"
    assert payload["dev_role_emulation_enabled"] is True
    assert payload["subject_id"].startswith("token:")
    assert "notifications.read" in payload["permissions"]


def test_readonly_cannot_restart_server(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DEV_ROLE_EMULATION", "true")
    _reset_settings_cache()

    with TestClient(app) as client:
        response = client.post("/api/server/restart", headers=_headers("readonly"))

    assert response.status_code == 403
    assert response.json()["detail"]["error"]["code"] == "PERMISSION_DENIED"


def test_notifications_read_state_is_per_principal(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DEV_ROLE_EMULATION", "true")
    _reset_settings_cache()

    with TestClient(app) as client:
        list_owner = client.get("/api/notifications", headers=_headers("owner"))
        assert list_owner.status_code == 200
        first_id = list_owner.json()[0]["id"]

        mark_read = client.post(f"/api/notifications/{first_id}/read", headers=_headers("readonly"))
        assert mark_read.status_code == 200

        readonly_list = client.get("/api/notifications", headers=_headers("readonly"))
        owner_list = client.get("/api/notifications", headers=_headers("owner"))

    readonly_item = next(item for item in readonly_list.json() if item["id"] == first_id)
    owner_item = next(item for item in owner_list.json() if item["id"] == first_id)

    assert readonly_item["is_read"] is True
    assert owner_item["is_read"] is False


def test_sessions_active_filter(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DEV_ROLE_EMULATION", "true")
    _reset_settings_cache()

    with TestClient(app) as client:
        response = client.get("/api/sessions?status=active&limit=50&offset=0", headers=_headers("operator"))

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert all(item["status"] == "active" for item in data)


def test_server_status():
    with TestClient(app) as client:
        response = client.get("/api/server/status", headers=BASE_HEADERS)
    assert response.status_code == 200
