# VPN Admin Panel V2

Панель управления **одним Xray/VLESS сервером**: FastAPI API, React web, Xray runtime, Caddy reverse proxy, Alembic migration-first.

## Что включено

- Backend: FastAPI + SQLAlchemy + Pydantic + SQLite.
- Frontend: React + TypeScript + Vite + Tailwind.
- VPN backend: Xray only (single server).
- UX: Health/Freshness, Action Center, Session Drilldown, Saved Views, Timeline.
- Client profiles: `vless_uri`, `qr_payload`, `v2rayn_json`, `singbox_json`, `hiddify_guide`.
- Ops scripts: deploy, health-check, logs, restart, backup, restore, update.

## Docker Compose compatibility

Сценарии поддерживают оба варианта:

- `docker compose` (v2)
- `docker-compose` (v1.29.2)

Проектное имя задаётся через `COMPOSE_PROJECT_NAME` (по умолчанию `vpn_admin_panel`), поэтому **top-level `name:` в compose не используется**.

## Runtime layout (server-friendly)

Base stack (`docker-compose.yml`) безопасен для VPS, где:

- порт `443` уже занят host Xray;
- нельзя ломать боевой dataplane.

По умолчанию:

- proxy публикует только `80:80`;
- контейнерный Xray не публикуется наружу.

Опциональные override-файлы:

- `docker-compose.tls.yml` — включает публикацию `443:443` для proxy;
- `docker-compose.xray-public.yml` — включает публикацию `${XRAY_PUBLIC_PORT}:8443` для контейнерного Xray.

## One-command deploy

```bash
git clone <repo>
cd vpn-admin-panel_V2
cp .env.example .env
./deploy.sh prod-like
```

Поддерживаемые профили:

```bash
./deploy.sh dev
./deploy.sh stage
./deploy.sh prod-like
```

### Что делает `deploy.sh`

1. Проверяет Docker.
2. Подготавливает/обновляет `.env` под выбранный профиль.
3. Генерирует `docker/caddy/Caddyfile`.
4. Поднимает compose stack с autodetect `docker compose` / `docker-compose`.
5. Ждёт API health.
6. Применяет `alembic upgrade head`.
7. Выполняет idempotent seed.

## Профили запуска

- `dev`: `APP_ENV=development`, `DEV_ROLE_EMULATION=true`, `SCHEMA_MANAGEMENT_MODE=bootstrap`.
- `stage`: `APP_ENV=staging`, `DEV_ROLE_EMULATION=false`, `SCHEMA_MANAGEMENT_MODE=alembic`.
- `prod-like`: `APP_ENV=production`, `DEV_ROLE_EMULATION=false`, `SCHEMA_MANAGEMENT_MODE=alembic`.

## TLS и coexistence с host Xray

### Без домена / безопасный базовый сценарий (рекомендуется для VPS с занятым 443)

```env
DOMAIN=
ENABLE_TLS_PROXY=false
ENABLE_XRAY_PUBLIC=false
```

Запуск:

```bash
./deploy.sh prod-like
```

### С доменом и TLS для панели

```env
DOMAIN=panel.example.com
ENABLE_TLS_PROXY=true
```

> Включайте только если 443 свободен для proxy/Caddy.

### Публикация контейнерного Xray

```env
ENABLE_XRAY_PUBLIC=true
XRAY_PUBLIC_PORT=8443
```

> Если на хосте уже есть боевой Xray, оставляйте `ENABLE_XRAY_PUBLIC=false`.

## Caddy routing

Настроено так:

- `/api/events/stream*` -> API (с `flush_interval -1` для SSE);
- `/api/*` и `/health` -> API;
- всё остальное -> Web.

Это гарантирует, что `/health` через proxy не попадает во frontend HTML.

## Client Profiles API

- `GET /api/links/{link_id}/profiles`
- `GET /api/links/{link_id}/profiles/{profile_key}`

Provider-aware форматы:
- `xray`: `vless_uri`, `qr_payload`, `v2rayn_json`, `singbox_json`, `hiddify_guide`
- `avg`: `awg_conf`
- `wg`: `wg_conf`

В UI: `VLESS ссылки` -> `Создать пользователя` (с выбором протокола) -> `Profiles` для мгновенного открытия конфигураций.

## Release-readiness static validation (без Docker)

```bash
./scripts/verify-release-readiness.sh
```

Скрипт проверяет:
- shell syntax;
- compose compatibility constraints (без `name:`, без `443` в base);
- override-файлы;
- Caddy routing правила (`/health`, `/api/*`, SSE);
- синхронность `Caddyfile.template` и дефолтного `Caddyfile`.

## Production handoff package

- Release note: `docs/release-note-rc-144.31.99.55.md`
- Runbook: `docs/vps-rollout-144.31.99.55.md`
- Operator cheatsheet: `docs/operator-cheatsheet-144.31.99.55.md`

## Ops scripts

```bash
./scripts/health-check.sh
./scripts/logs.sh [service]
./scripts/restart.sh
./scripts/backup.sh
./scripts/restore.sh <backup.tar.gz>
./scripts/update.sh
```

## Smoke checks после deploy

```bash
curl -s http://127.0.0.1/health
curl -s -H 'x-api-token: admin-token' http://127.0.0.1/api/auth/me
curl -s -H 'x-api-token: admin-token' http://127.0.0.1/api/links | head -c 300
```

Если panel доступна по IP:

```bash
curl -s http://144.31.99.55/health
curl -s -H 'x-api-token: admin-token' http://144.31.99.55/api/auth/me
```

## Post-deploy verification checklist

- [ ] `docker compose ps` или `docker-compose ps`: `vpn_xray`, `vpn_api`, `vpn_web`, `vpn_proxy` в состоянии up/healthy.
- [ ] `curl http://127.0.0.1/health` возвращает API JSON, а не frontend HTML.
- [ ] `curl -H 'x-api-token: admin-token' http://127.0.0.1/api/auth/me` возвращает валидный principal.
- [ ] `curl -H 'x-api-token: admin-token' http://127.0.0.1/api/links` отдаёт список ссылок.
- [ ] UI доступен по `http://<server-ip>`.
- [ ] В `VLESS ссылки` -> `Profiles` открывается modal, работают copy/download.
- [ ] `./scripts/health-check.sh` проходит без ошибок.
- [ ] `ss -ltnp | grep ':443'` подтверждает, что 443 остаётся за host Xray (в safe baseline режиме).

## Локальная разработка

```bash
cd apps/api
pip install -r requirements.txt
PYTHONPATH=. alembic upgrade head
pytest -q

cd ../web
npm install
npm run build
```

## Вне scope

- Multi-backend VPN (WireGuard/OpenVPN)
- Full auth lifecycle UI
- Distributed/multi-node orchestration
- Advanced alerts/export center
