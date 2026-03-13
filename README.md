# VPN Admin Panel V2

Лёгкая админ-панель для одиночного VPS с provider-aware runtime (`xray`, `wg`, `avg`, `mock`) и базовой авторизацией.

## Что включено

- Backend: FastAPI + SQLAlchemy + Alembic + SQLite.
- Frontend: React + TypeScript + Vite + Tailwind.
- Ingress: Caddy.
- Runtime deploy modes: `safe`, `full`, `behind-ingress`.
- Provider registry + capability flags.
- Auth baseline: login/logout + cookie session + token fallback.

## Быстрый старт на новой VM/VPS

```bash
git clone <repo>
cd vpn-admin-panel_V2
./install.sh safe xray
```

`install.sh` делает:
1. preflight (`scripts/doctor.sh`)
2. env bootstrap
3. deploy (`deploy.sh`)
4. post-deploy validation (`scripts/post-deploy-check.sh`)

## Deploy modes

### `safe` (по умолчанию)
- панель только на `80`
- не требует `443`
- безопасен для VPS, где `443` уже занят host Xray

### `full`
- для чистой VM
- включает TLS publish и публичный provider runtime
- требует свободный `443` и валидный `DOMAIN`

### `behind-ingress`
- для запуска за внешним ingress/reverse proxy
- локальный proxy без внешней публикации портов

## Provider support (v1)

- `xray`: baseline, полный текущий MVP-путь.
- `wg`: staged runtime path + capability-aware ограничения.
- `avg`: staged runtime path + ограниченные возможности.
- `mock`: локальный fallback.

API каталог providers:
- `GET /api/providers`

## Auth baseline

### API
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`

### Как включается
- `AUTH_ENABLED=true`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD_HASH` (рекомендуется) или `ADMIN_PASSWORD` (bootstrap/dev fallback)

Хеш пароля:
```bash
./scripts/hash-password.sh 'your-strong-password'
```

`/health` остаётся публичным для ops checks.

## Runtime stack и overrides

Base compose (`docker-compose.yml`) + overlays:
- `docker-compose.tls.yml`
- `docker-compose.xray-public.yml`
- `docker-compose.wg.yml`
- `docker-compose.avg.yml`
- `docker-compose.behind-ingress.yml`

Ручная правка compose-файлов на целевой машине **не требуется**.

## Основные scripts

```bash
./install.sh [safe|full|behind-ingress] [xray|wg|avg|mock]
./scripts/doctor.sh [mode]
./deploy.sh [safe|full|behind-ingress|dev|stage|prod-like]
./scripts/post-deploy-check.sh
./scripts/health-check.sh
./scripts/backup.sh
./scripts/restore.sh <backup.tar.gz>
./scripts/update.sh
./scripts/restart.sh
./scripts/logs.sh [service]
```

## Проверка после deploy

```bash
./scripts/post-deploy-check.sh
curl -s http://127.0.0.1/health
curl -s -H 'x-api-token: admin-token' http://127.0.0.1/api/auth/me
curl -s -H 'x-api-token: admin-token' http://127.0.0.1/api/providers
```

UI:
- открыть панель
- выполнить login
- проверить Dashboard / Links / Profiles modal

## Совместимость Docker Compose

Поддерживается:
- `docker compose` (v2)
- `docker-compose` (v1.29.2)

## Ограничения v1

- `wg` и `avg` реализованы staged/capability-aware (без полного parity с xray).
- Без Docker runtime e2e проверки недоступны, используйте `doctor` + `verify-release-readiness` + `post-deploy-check`.

## Документация ops

- `docs/vps-rollout-144.31.99.55.md`
- `docs/release-note-rc-144.31.99.55.md`
- `docs/operator-cheatsheet-144.31.99.55.md`
