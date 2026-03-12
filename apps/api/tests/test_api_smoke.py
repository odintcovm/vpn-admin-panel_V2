import os
import sys

from fastapi.testclient import TestClient

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.main import app

HEADERS = {"x-api-token": "admin-token"}


def call(method: str, path: str, **kwargs):
    with TestClient(app) as client:
        return client.request(method, path, headers=HEADERS, **kwargs)


def test_dashboard_overview():
    response = call("GET", "/api/dashboard/overview")
    assert response.status_code == 200
    assert "total_links" in response.json()


def test_links_crud_minimal():
    create = call("POST", "/api/links", json={"name": "Smoke Link", "tag": "Test device", "enabled": True})
    assert create.status_code == 200
    link_id = create.json()["id"]

    patch = call("PATCH", f"/api/links/{link_id}", json={"name": "Smoke Link Updated"})
    assert patch.status_code == 200

    delete = call("DELETE", f"/api/links/{link_id}")
    assert delete.status_code == 200


def test_notifications_api():
    response = call("GET", "/api/notifications")
    assert response.status_code == 200


def test_sessions_api():
    response = call("GET", "/api/sessions")
    assert response.status_code == 200


def test_server_status():
    response = call("GET", "/api/server/status")
    assert response.status_code == 200
