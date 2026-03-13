# VPN Admin Panel V2

Панель управления VPN на одном VPS с поддержкой providers: **Xray**, **WireGuard (WG)**, **AVG (scaffold v1)**.

## Что реализовано

- Backend: FastAPI + SQLAlchemy + Alembic (migration-first).
- Frontend: React + TypeScript + Vite.
- Provider abstraction + registry (`xray`, `wg`, `avg`, `mock`).
- Auth v1: login/logout + cookie session, API token режим сохранён для ops.
- Runtime: docker-compose safe baseline (без обязательного 443), overrides для TLS/Xray-public.

## Providers

`APP_PROVIDER`:
- `xray` — основной working baseline.
- `wg` — WireGuard provider scaffold с базовой server/sessions telemetry.
- `avg` — AVG provider scaffold (ограниченные capabilities).
- `mock` — локальная mock-отладка.

API:
- `GET /api/providers` — активный provider и capability flags.

## Auth

Публично остаётся только `/health`.
Остальные API требуют либо:
- cookie session после `POST /api/auth/login`, либо
- `x-api-token` (ops/debug compatible).

Новые endpoints:
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`

### Env для auth

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=
ADMIN_PASSWORD=admin123
AUTH_SESSION_TTL_HOURS=24
```

Рекомендуется использовать `ADMIN_PASSWORD_HASH` (bcrypt), а `ADMIN_PASSWORD` оставлять только как fallback для bootstrap/dev.

## Deploy (safe baseline)

```bash
cp .env.example .env
./scripts/verify-release-readiness.sh
./deploy.sh prod-like
```

Для VPS с host Xray на 443:

```env
ENABLE_TLS_PROXY=false
ENABLE_XRAY_PUBLIC=false
DOMAIN=
```

## Проверки

```bash
# static
./scripts/verify-release-readiness.sh

# backend
cd apps/api
pip install -r requirements.txt
PYTHONPATH=. pytest -q

# frontend
cd ../web
npm install
npm run build
```

## Rollout docs

- `docs/release-note-rc-144.31.99.55.md`
- `docs/vps-rollout-144.31.99.55.md`
- `docs/operator-cheatsheet-144.31.99.55.md`

## Ограничения текущего этапа

- WG/AVG реализованы как provider v1 (capability-aware scaffold), без полного feature parity с Xray.
- TLS для панели остаётся optional и не должен включаться на host, где 443 уже занят production Xray.


Compatibility note: docker compose v2 and docker-compose v1.29.2 are both supported.

Safety note: host Xray on 443 must remain untouched; panel safe baseline does not claim 443.
