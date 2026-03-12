# VPN Admin Panel V2

Лёгкая, аккуратная и «премиальная» админ-панель для управления **одним Xray/VLESS сервером** на одном VPS.

> Текущий релиз ориентирован на demo/internal use: mock-режим работает из коробки, а real Xray интеграция подготовлена в виде безопасного scaffold.

## Скриншоты
- `docs/screenshots/` — место для скриншотов демо-сборки (добавьте при публикации).

## Архитектура (кратко)
- **Frontend**: React + TypeScript + Vite + Tailwind + shadcn/ui-style components + Recharts
- **Backend**: FastAPI + SQLAlchemy + Pydantic + SQLite
- **Realtime**: SSE (`/api/events/stream`)
- **Providers**:
  - `MockProvider` (default)
  - `XrayProvider` (integration scaffold)
- **Repo layout**:
  - `apps/api`
  - `apps/web`
  - `packages/shared`
  - `docker`

## Что включает MVP
- Страницы: **Дашборд**, **VLESS ссылки**, **Клиенты**, **Настройки сервера**
- Seed сценарий:
  - 6 VLESS ссылок
  - 2 активных подключения
  - реалистичные IP/трафик/временные метки
  - минимум одна disabled и одна idle ссылка
- Базовые действия: create/edit/delete/regenerate/toggle/copy/QR + server restart/reload placeholders

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

## Environment variables
- `APP_PROVIDER=mock|xray` (default: `mock`)
- `DATABASE_URL=sqlite:///./data.db`
- `API_TOKEN=admin-token`
- `VITE_API_URL=http://localhost:8000`
- `VITE_API_TOKEN=admin-token`

## API surface
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
- `GET /api/server/status`
- `GET /api/server/logs`
- `POST /api/server/restart`
- `POST /api/server/reload`
- `GET /api/events`
- `GET /api/activity-log`

## Mock provider (default)
- Автосидит демо-данные на первом старте.
- Подходит для UI demo, разработки и smoke-проверок.
- Не требует реального Xray окружения.

## Real Xray integration notes
`XrayProvider` сейчас scaffold и должен быть доработан для production:
1. Подключение Xray Stats API.
2. Парсинг access/error логов.
3. Безопасный execution path для restart/reload.
4. Стандартизованная обработка ошибок/таймаутов.

## Known limitations
- `XrayProvider` не подключён к реальному daemon в этом MVP.
- QR endpoint отдаёт payload строку (рендер QR-изображения не выполняется на backend).
- Docker проверка зависит от наличия Docker CLI в окружении запуска.
