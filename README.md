# VPN Admin Panel V2

Панель управления **одним Xray/VLESS сервером**: FastAPI API, React web, Xray runtime, reverse proxy (Caddy), миграции Alembic и one-command deploy.

## Что входит в продукт

- Backend: FastAPI + SQLAlchemy + Pydantic + SQLite.
- Frontend: React + TypeScript + Vite + Tailwind.
- VPN backend: **только Xray** (single-node).
- Ingress: Caddy (web + api + SSE).
- DB discipline: migration-first (Alembic), bootstrap только dev fallback.
- Ops baseline: deploy/update/backup/restore/restart/logs/health-check scripts.
- Client profiles: VLESS URI, QR payload, v2rayN/v2rayNG JSON, sing-box JSON, Hiddify guide.

---

## One-command deploy (чистая VM)

```bash
git clone <repo>
cd vpn-admin-panel_V2
cp .env.example .env
./deploy.sh prod-like
```

Поддерживаемые профили деплоя:

```bash
./deploy.sh dev
./deploy.sh stage
./deploy.sh prod-like
```

### Что делает `deploy.sh`

1. Проверяет Docker/Compose.
2. Подготавливает `.env` и профильные флаги.
3. Генерирует Caddy config (домен/TLS или IP/self-host fallback).
4. Поднимает runtime stack (`xray`, `api`, `web`, `proxy`).
5. Ждёт health API.
6. Применяет `alembic upgrade head`.
7. Выполняет idempotent seed.
8. Показывает URL, статус и операционные команды.

---

## TLS и сценарии с доменом/без домена

### 1) С доменом (TLS)

В `.env`:

```env
DOMAIN=vpn.example.com
```

Запуск:

```bash
./deploy.sh prod-like
```

Caddy поднимет HTTPS и получит сертификат автоматически.

### 2) Без домена (self-host / IP)

Оставьте `DOMAIN=` пустым.

Запуск:

```bash
./deploy.sh prod-like
```

Панель будет доступна по `http://<server-ip>` без ложного обещания TLS.

---

## Runtime stack

`docker-compose.yml` поднимает:

- `xray` — VLESS inbound (baseline config `docker/xray/config.json`)
- `api` — FastAPI
- `web` — Vite preview build
- `proxy` — Caddy reverse proxy

### Основные команды runtime

```bash
docker compose up -d --build
docker compose ps
docker compose down
```

---

## Migration-first и bootstrap

Штатный режим: только миграции.

```bash
cd apps/api
pip install -r requirements.txt
PYTHONPATH=. alembic upgrade head
```

`SCHEMA_MANAGEMENT_MODE`:

- `alembic` — production/stage default, startup не делает schema mutations.
- `bootstrap` — только dev fallback для локальной разработки.

---

## Client Profiles (панель и API)

В разделе `VLESS ссылки` есть кнопка **Profiles** для каждой ссылки.

Поддерживаемые форматы:

- `vless_uri`
- `qr_payload`
- `v2rayn_json`
- `singbox_json`
- `hiddify_guide`

Действия в UI:

- открыть формат;
- скопировать payload;
- скачать файл профиля.

### API

- `GET /api/links/{link_id}/profiles`
- `GET /api/links/{link_id}/profiles/{profile_key}`

---

## Operations scripts

```bash
./scripts/health-check.sh
./scripts/logs.sh [service]
./scripts/restart.sh
./scripts/backup.sh
./scripts/restore.sh <backup.tar.gz>
./scripts/update.sh
```

### Что покрыто

- backup: SQLite + `.env` + `docker/xray/config.json`
- restore: восстановление env/config/db + restart сервисов
- update: `git pull` (если git repo), rebuild, migration, restart
- health-check: быстрый статус compose + API probe

---

## Локальная разработка (без deploy.sh)

### Backend

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd apps/web
npm install
npm run dev
```

---

## Manual checks

1. `./deploy.sh prod-like` (или `dev/stage`) завершается без ошибок.
2. `./scripts/health-check.sh` возвращает OK.
3. Панель открывается через proxy URL.
4. SSE обновления и Health/Freshness bar видны.
5. Session drilldown открывается из таблицы сессий.
6. Action Center выполняет действия с confirm.
7. В Links → Profiles можно получить минимум 2–3 формата профилей.

---

## Ограничения этапа (вне scope)

- Multi-backend VPN (WireGuard/OpenVPN) — не реализуется.
- Full auth lifecycle UI (`login/refresh/logout`) — не реализован.
- Distributed/multi-node deployment — не реализован.
- Advanced alerts/export center — не в этом этапе.
