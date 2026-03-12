# VPN Admin Panel V2

Лёгкая, аккуратная админ-панель для управления **одним Xray/VLESS сервером** на одном VPS.

## Что реализовано в Foundation Sprint
- RBAC scaffolding (roles/permissions + backend guards)
- Unified UI states framework (loading/empty/error/retry/skeleton/inline notice)
- Persistent Notification Center (read/unread + mark all)
- Sessions API + отдельная страница Sessions
- CI baseline (GitHub Actions)
- DB migration baseline (Alembic)

## Архитектура (кратко)
- **Frontend**: React + TypeScript + Vite + Tailwind + shadcn/ui-style components + Recharts
- **Backend**: FastAPI + SQLAlchemy + Pydantic + SQLite
- **Realtime**: SSE (`/api/events/stream`)
- **Providers**:
  - `MockProvider` (default)
  - `XrayProvider` (integration scaffold)

## Быстрый старт (локально)

### 1) Подготовить env
```bash
cp .env.example .env
cp apps/api/.env.example apps/api/.env
```

### 2) Запустить API
```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API: http://localhost:8000

### 3) Запустить Web
```bash
cd apps/web
npm install
npm run dev
```
Web: http://localhost:5173

## Docker Compose
```bash
cp .env.example .env
docker compose up --build
```
- API: http://localhost:8000
- Web: http://localhost:5173

## Миграции
```bash
cd apps/api
python -m alembic upgrade head
python -m alembic downgrade -1
```

## RBAC совместимость с x-api-token
- Текущий `x-api-token` механизм сохранён.
- По умолчанию токен маппится на privileged context (`owner`) в token-only режиме.
- Для проверки ограничений в development можно передавать `x-role: owner|admin|operator|readonly`.
- Endpoint для проверки контекста: `GET /api/auth/me`.

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

## UI
- Notification Center открывается кнопкой "Уведомления" в header.
- Отдельная вкладка "Сессии" для активных/завершённых сессий.

## CI
GitHub Actions workflow `.github/workflows/ci.yml` проверяет:
- frontend install + build/typecheck
- backend install
- backend smoke tests (pytest)

## Ограничения текущего этапа
- Полный auth lifecycle (`/auth/login`, refresh, logout) ещё не внедрён
- Real Xray integration остаётся scaffold
- Advanced alerts engine и export center — в следующих спринтах
