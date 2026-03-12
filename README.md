# VPN Admin Panel V2

Лёгкая, аккуратная админ-панель для управления **одним Xray/VLESS сервером** на одном VPS.

## Что реализовано в Foundation + Stabilization
- RBAC scaffolding (roles/permissions + backend guards)
- Hardening для `x-role` dev-эмуляции (явный флаг + запрет вне dev/test)
- Migration-first база на Alembic (штатный запуск без неявных schema mutations)
- Persistent Notification Center с per-principal read-state
- Sessions API + отдельная страница Sessions
- Auth foundation (`users`, `auth_sessions`) без поломки token-only режима
- CI baseline (GitHub Actions)

## Архитектура (кратко)
- **Frontend**: React + TypeScript + Vite + Tailwind + shadcn/ui-style components + Recharts
- **Backend**: FastAPI + SQLAlchemy + Pydantic + SQLite
- **Realtime**: SSE (`/api/events/stream`, mock-driven)
- **Providers**:
  - `MockProvider` (default)
  - `XrayProvider` (integration scaffold)

## Быстрый старт (локально)

### 1) Подготовить env
```bash
cp .env.example .env
cp apps/api/.env.example apps/api/.env
```

### 2) Backend: install → migrate → run
```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API: http://localhost:8000

### 3) Frontend: install → run
```bash
cd apps/web
npm install
npm run dev
```
Web: http://localhost:5173

## Migration-first режим

Основной режим управления схемой: **только Alembic**.

```bash
cd apps/api
PYTHONPATH=. alembic upgrade head
PYTHONPATH=. alembic downgrade -1
```

### SCHEMA_MANAGEMENT_MODE
- `alembic` (по умолчанию): безопасный штатный режим. Приложение **не** выполняет `create_all()`.
- `bootstrap`: dev-only fallback для одноразового локального старта. Разрешён только в dev-like окружении.

> Для staging/production использовать только migration-first workflow.

## RBAC и token совместимость

### Совместимость с `x-api-token`
- Текущий `x-api-token` сценарий сохранён.
- По умолчанию токен маппится на privileged context (`owner`).

### `x-role` (только для dev/test)
Role emulation включается только при:
- `APP_ENV in {development, dev, local, test}`
- `DEV_ROLE_EMULATION=true`

Иначе `x-role` возвращает:
- `403`
- `error.code = DEV_ROLE_EMULATION_DISABLED`

Проверка контекста:
- `GET /api/auth/me`
- возвращает `subject_id`, `role`, `permissions`, `auth_mode`, `user_id`, `dev_role_emulation_enabled`

## Auth foundation (текущий статус)

Подготовлены базовые сущности для следующего auth-спринта:
- `users`
- `auth_sessions`

Текущий режим остаётся token-only. Полный lifecycle (`login/refresh/logout/session UI`) пока не реализован.

## Notifications

- Статус прочтения хранится в `notification_reads` (per-principal).
- Legacy `notifications.is_read` оставлен как временный compatibility слой, но **не используется как источник истины**.
- Endpoints:
  - `GET /api/notifications`
  - `POST /api/notifications/{id}/read`
  - `POST /api/notifications/read-all`

## API surface (актуально)
- `GET /api/auth/me`
- `GET /api/dashboard/overview`
- `GET /api/links`
- `POST /api/links`
- `PATCH /api/links/{id}`
- `DELETE /api/links/{id}`
- `POST /api/links/{id}/regenerate`
- `GET /api/links/{id}/qr`
- `GET /api/clients`
- `GET /api/clients/active`
- `GET /api/clients/{id}`
- `GET /api/sessions`
- `GET /api/sessions/active`
- `GET /api/sessions/{id}`
- `GET /api/server/status`
- `GET /api/server/logs`
- `POST /api/server/restart`
- `POST /api/server/reload`
- `GET /api/events`
- `GET /api/activity-log`
- `GET /api/notifications`
- `POST /api/notifications/{id}/read`
- `POST /api/notifications/read-all`
- `GET /api/events/stream`

## CI
GitHub Actions `.github/workflows/ci.yml`:
- frontend install + build/typecheck
- backend install
- backend tests (`pytest`)

## Обязательные команды после pull
```bash
# backend
cd apps/api
pip install -r requirements.txt
PYTHONPATH=. alembic upgrade head
pytest -q

# frontend
cd ../web
npm install
npm run build
```

## Что вне scope текущего этапа
- Полный auth lifecycle (`/auth/login`, refresh, logout, session store + UI)
- Real Xray integration
- Замена mock SSE на real event source
- Advanced alerts engine
- Full export center
- Production infra hardening
