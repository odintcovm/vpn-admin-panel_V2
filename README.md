# VPN Admin Panel V2

Лёгкая, премиальная админ-панель для управления **одним Xray/VLESS сервером** на одном VPS.

## Что реализовано сейчас

- Migration-first backend baseline (Alembic-first).
- RBAC + token-only security context (`x-api-token`) с безопасной dev-role emulation.
- Notification Center с per-principal read-state.
- Sessions list + Session Drilldown + Timeline (v1).
- Global Health/Freshness Bar.
- Action Center для критичных действий с confirm-паттерном.
- Saved Views (local) для Links / Clients / Sessions.

## Архитектура

- **Frontend**: React + TypeScript + Vite + Tailwind + Recharts
- **Backend**: FastAPI + SQLAlchemy + Pydantic + SQLite
- **Realtime**: SSE (`/api/events/stream`, mock-driven)
- **Providers**:
  - `MockProvider` (default)
  - `XrayProvider` (integration scaffold)

## Быстрый старт

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

### 3) Frontend: install → run
```bash
cd apps/web
npm install
npm run dev
```

## Migration-first режим

Штатный режим: только Alembic.

```bash
cd apps/api
PYTHONPATH=. alembic upgrade head
PYTHONPATH=. alembic downgrade -1
```

`SCHEMA_MANAGEMENT_MODE`:
- `alembic` (default): schema mutations на startup не выполняются.
- `bootstrap`: dev-only fallback для локального bootstrap.

> В staging/production использовать только migration-first workflow.

## Security / RBAC

- `x-api-token` сохранён и совместим.
- `x-role` работает только при `APP_ENV in {development, dev, local, test}` + `DEV_ROLE_EMULATION=true`.
- `/api/auth/me` возвращает `subject_id`, `role`, `permissions`, `auth_mode`, `user_id`, `dev_role_emulation_enabled`.

## UX-модули этого спринта

### Action Center
Критичные действия через единый confirm-паттерн:
- restart
- reload
- regenerate UUID
- enable/disable link
- mark suspicious

API: `POST /api/actions/execute`.

### Session Drilldown
- Открытие детализации сессии из таблицы.
- Показ ключевых полей + reconnect summary + related events.
- Timeline v1 в боковой карточке.

API:
- `GET /api/sessions/{id}/drilldown`
- `GET /api/timeline/sessions/{id}`

### Health / Freshness Bar
Глобальная панель состояния:
- provider/backend status
- SSE status (client-side)
- last refresh
- freshness/degraded indications

API: `GET /api/system/health`.

### Saved Views (local)
- Links / Clients / Sessions.
- Сохраняются в localStorage (без backend persistence на текущем этапе).

## Notifications

- Источник истины read-state: `notification_reads`.
- Legacy `notifications.is_read` оставлен как compatibility слой и не участвует в business truth.

## API surface (добавлено/обновлено)

- `GET /api/system/health`
- `POST /api/actions/execute`
- `GET /api/sessions/{id}/drilldown`
- `GET /api/timeline/sessions/{id}`

Также сохранены существующие `/api/auth/me`, `/api/links*`, `/api/clients*`, `/api/sessions*`, `/api/notifications*`, `/api/server/*` и т.д.

## Обязательные проверки после pull

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

## Ручная проверка новых UX-сценариев

1. Открыть панель и проверить Health/Freshness Bar (backend/provider/SSE/freshness).
2. В Links/Clients/Settings запустить критичные действия через Action Center.
3. На странице Sessions открыть drilldown по строке, проверить timeline.
4. Создать и применить Saved View на Links/Clients/Sessions.
5. Проверить Notification Center (read / read-all).

## Что вне scope

- Полный auth lifecycle (`/auth/login`, refresh, logout, session UI)
- Real Xray integration
- Замена mock SSE на real event source
- Advanced alerts engine
- Full export center
- Production infra hardening
