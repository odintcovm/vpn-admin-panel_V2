import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

os.environ.setdefault("SCHEMA_MANAGEMENT_MODE", "bootstrap")
os.environ.setdefault("APP_ENV", "development")

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.core.config import get_settings
from app.db.database import SessionLocal
from app.main import app, startup_event
from app.models.entities import Notification


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
        create = client.post("/api/links", headers=BASE_HEADERS, json={"name": "Smoke Link", "tag": "Test device", "provider": "xray", "enabled": True})
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
    assert payload["auth_mode"] == "token"
    assert payload["user_id"] is not None
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


def test_notification_legacy_flag_is_not_source_of_truth(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DEV_ROLE_EMULATION", "true")
    _reset_settings_cache()

    with SessionLocal() as db:
        notification = db.query(Notification).first()
        assert notification is not None
        notification.is_read = True
        db.commit()
        notification_id = notification.id

    with TestClient(app) as client:
        response = client.get("/api/notifications", headers=_headers("owner"))

    item = next(row for row in response.json() if row["id"] == notification_id)
    assert item["is_read"] is False


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


def test_startup_does_not_call_create_all_in_alembic_mode(monkeypatch):
    import app.main as main_module

    called = {"value": False}

    def fake_create_all(*args, **kwargs):
        called["value"] = True

    monkeypatch.setattr(main_module.settings, "schema_management_mode", "alembic")
    monkeypatch.setattr(main_module.Base.metadata, "create_all", fake_create_all)

    startup_event()
    assert called["value"] is False


def test_startup_calls_create_all_only_in_bootstrap_dev(monkeypatch):
    import app.main as main_module

    called = {"value": False}

    def fake_create_all(*args, **kwargs):
        called["value"] = True

    monkeypatch.setattr(main_module.settings, "schema_management_mode", "bootstrap")
    monkeypatch.setattr(main_module.settings, "app_env", "development")
    monkeypatch.setattr(main_module.Base.metadata, "create_all", fake_create_all)

    startup_event()
    assert called["value"] is True


def test_alembic_upgrade_head_creates_core_tables(tmp_path):
    db_file = tmp_path / "migration_test.db"
    db_url = f"sqlite:///{db_file}"
    env = os.environ.copy()
    env["DATABASE_URL"] = db_url

    subprocess.run(["alembic", "upgrade", "head"], cwd=Path(__file__).resolve().parents[1], check=True, env={**env, "PYTHONPATH": "."})

    con = sqlite3.connect(db_file)
    try:
        tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    finally:
        con.close()

    assert "notification_reads" in tables
    assert "user_links" in tables
    assert "users" in tables


def test_system_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/system/health", headers=BASE_HEADERS)
    assert response.status_code == 200
    payload = response.json()
    assert "provider_status" in payload
    assert "last_success_refresh_at" in payload


def test_action_execute_restart_and_mark_suspicious(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DEV_ROLE_EMULATION", "true")
    _reset_settings_cache()

    with TestClient(app) as client:
        restart = client.post("/api/actions/execute", headers=_headers("admin"), json={"action": "reload", "target_type": "server", "reason": "smoke"})
        assert restart.status_code == 200

        clients = client.get("/api/clients", headers=_headers("operator")).json()
        assert clients
        mark = client.post("/api/actions/execute", headers=_headers("operator"), json={"action": "mark_suspicious", "target_type": "client", "target_id": clients[0]["id"], "reason": "smoke"})
        assert mark.status_code == 200


def test_sessions_drilldown_and_timeline():
    with TestClient(app) as client:
        sessions = client.get("/api/sessions", headers=BASE_HEADERS).json()
        assert sessions
        sid = sessions[0]["id"]
        detail = client.get(f"/api/sessions/{sid}/drilldown", headers=BASE_HEADERS)
        timeline = client.get(f"/api/timeline/sessions/{sid}", headers=BASE_HEADERS)

    assert detail.status_code == 200
    assert "reconnect_summary" in detail.json()
    assert timeline.status_code == 200
    assert isinstance(timeline.json(), list)


def test_link_profiles_endpoints():
    with TestClient(app) as client:
        links = client.get('/api/links', headers=BASE_HEADERS).json()
        assert links
        link_id = links[0]['id']

        formats = client.get(f'/api/links/{link_id}/profiles', headers=BASE_HEADERS)
        assert formats.status_code == 200
        payload = formats.json()
        assert len(payload['formats']) >= 3

        vless = client.get(f'/api/links/{link_id}/profiles/vless_uri', headers=BASE_HEADERS)
        assert vless.status_code == 200
        assert 'vless://' in vless.json()['payload']



def test_create_link_with_provider_and_profiles_contract():
    with TestClient(app) as client:
        avg_create = client.post(
            "/api/links",
            headers=BASE_HEADERS,
            json={"name": "AVG Smoke", "tag": "Test device", "provider": "avg", "enabled": True},
        )
        assert avg_create.status_code == 200
        avg_payload = avg_create.json()
        assert avg_payload["provider"] == "avg"
        assert avg_payload["profile_formats"] == ["awg_conf"]

        avg_profiles = client.get(f"/api/links/{avg_payload['id']}/profiles", headers=BASE_HEADERS)
        assert avg_profiles.status_code == 200
        assert [i["key"] for i in avg_profiles.json()["formats"]] == ["awg_conf"]

        avg_conf = client.get(f"/api/links/{avg_payload['id']}/profiles/awg_conf", headers=BASE_HEADERS)
        assert avg_conf.status_code == 200
        assert "[Interface]" in avg_conf.json()["payload"]

        wg_create = client.post(
            "/api/links",
            headers=BASE_HEADERS,
            json={"name": "WG Smoke", "tag": "Test device", "provider": "wg", "enabled": True},
        )
        assert wg_create.status_code == 200
        wg_payload = wg_create.json()
        assert wg_payload["provider"] == "wg"
        assert wg_payload["profile_formats"] == ["wg_conf"]

        wg_conf = client.get(f"/api/links/{wg_payload['id']}/profiles/wg_conf", headers=BASE_HEADERS)
        assert wg_conf.status_code == 200
        assert "[Peer]" in wg_conf.json()["payload"]

        xray_conf_for_wg = client.get(f"/api/links/{wg_payload['id']}/profiles/vless_uri", headers=BASE_HEADERS)
        assert xray_conf_for_wg.status_code == 404
