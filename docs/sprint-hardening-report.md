# Sprint Hardening Report — vpn-admin-panel_V2

## Sprint Goal Review

| Цель спринта | Статус | Доказательство | Комментарий / Отклонение |
|---|---|---|---|
| Ужесточить RBAC и dev-role emulation | Выполнено | Внедрены `APP_ENV`, `DEV_ROLE_EMULATION`, `SCHEMA_MANAGEMENT_MODE`; `x-role` ограничен dev/test; контекст унифицирован через `SecurityPrincipal` и `require_permission`; расширен `/api/auth/me`; используются коды ошибок `DEV_ROLE_EMULATION_DISABLED`, `PERMISSION_DENIED`. | Полный auth lifecycle не реализован; текущий доступ остаётся token-based как переходный этап. |
| Перевести notifications на per-principal read-state | Выполнено | Добавлена модель `notification_reads` (`notification_id`, `principal_id`, `read_at`, unique constraint); обновлены `/api/notifications`, `/api/notifications/{id}/read`, `/api/notifications/read-all`. | Сохранён legacy `Notification.is_read` для обратной совместимости до полного завершения миграции контракта. |
| Усилить migration discipline | Частично | Добавлена миграция `0002_notification_reads_and_rbac_hardening`; стандартный запуск больше не использует безусловный `create_all()`, bootstrap вынесен в отдельный режим; README обновлён командами миграций. | Полный перевод исторических legacy-сущностей в migration-first контур ещё не завершён и перенесён в следующий спринт. |
| Расширить hardening test coverage | Выполнено | В `test_api_smoke.py` добавлены negative-сценарии RBAC, проверки `x-role` enabled/disabled, контракт `/api/auth/me`, per-principal notifications, фильтрация sessions. | Покрытие преимущественно smoke/contract; e2e и нагрузочные сценарии остаются вне текущего scope. |
| Обновить frontend-совместимость и документацию | Выполнено | Обновлены frontend-типы (`AuthMe`, `NotificationItem.read_at`), parser ошибок (`detail.error`), README дополен по безопасному запуску, миграциям и ограничениям. | SSE остаётся mock-driven; ограничение зафиксировано, но не устранено в этом спринте. |

---

## 1) Что реализовано

- Ужесточён RBAC-контур и безопасность dev-role emulation:
  - введены env-флаги `APP_ENV`, `DEV_ROLE_EMULATION`, `SCHEMA_MANAGEMENT_MODE`;
  - `x-role` разрешён только в dev/test при явном флаге;
  - унифицирован security-context через `SecurityPrincipal` и `require_permission`.
- Расширен контракт `GET /api/auth/me`: возвращаются `subject_id`, `role`, `permissions`, `dev_role_emulation_enabled`.
- Уведомления переведены на per-principal read-state:
  - добавлена сущность `notification_reads`;
  - `GET /api/notifications`, `POST /api/notifications/{id}/read`, `POST /api/notifications/read-all` работают по principal-контексту.
- Усилена дисциплина миграций:
  - добавлена Alembic-миграция `0002_notification_reads_and_rbac_hardening`;
  - безусловный `create_all()` убран из стандартного старта, оставлен только для bootstrap-режима.
- Расширено покрытие hardening-тестами:
  - negative RBAC;
  - проверка поведения `x-role` при disabled/enabled emulation;
  - изоляция read-state уведомлений по principal;
  - фильтрация sessions;
  - проверка контракта `/api/auth/me`.
- Поддержана frontend-совместимость:
  - обновлены типы API;
  - доработан parser ошибок под nested `detail.error`.
- Документация (`README`) обновлена для безопасного онбординга и запуска.

---

## 2) Какие файлы созданы/изменены

### Создано

- `apps/api/alembic/versions/0002_notification_reads_and_rbac_hardening.py` — миграция для per-principal read-state уведомлений.

### Изменено

- `apps/api/app/core/config.py` — hardening-флаги окружения.
- `apps/api/app/core/security.py` — RBAC hardening, `SecurityPrincipal`, безопасная обработка `x-role`.
- `apps/api/app/models/entities.py` — `NotificationRead` и связи с `Notification`.
- `apps/api/app/schemas/api.py` — расширен `AuthMeOut`, обновлён `NotificationOut`.
- `apps/api/app/services/services.py` — per-principal notification services, сиды и вспомогательная логика.
- `apps/api/app/api/routes.py` — обновлены `/api/auth/me` и `/api/notifications*`.
- `apps/api/app/main.py` — ограничение schema bootstrap и безопасный startup seed flow.
- `apps/api/tests/test_api_smoke.py` — hardening/negative тесты.
- `apps/web/src/types/api.ts` — типы совместимости контракта.
- `apps/web/src/lib/utils.ts` — parser ошибок с поддержкой `detail.error`.
- `README.md` — разделы по migration discipline, role emulation, безопасному запуску и ограничениям.

---

## 3) Какие API добавлены/изменены

| Endpoint | Method | Назначение |
|---|---|---|
| `/api/auth/me` | GET | Возврат текущего security context: `subject_id`, `role`, `permissions`, `dev_role_emulation_enabled`. |
| `/api/notifications` | GET | Получение уведомлений с per-principal read-state (`is_read`, `read_at`). |
| `/api/notifications/{notification_id}/read` | POST | Пометка уведомления прочитанным для текущего principal. |
| `/api/notifications/read-all` | POST | Пометка всех уведомлений прочитанными для текущего principal. |

---

## 4) Какие модели данных добавлены/изменены

### NotificationRead (новая сущность)

- `notification_id`
- `principal_id`
- `read_at`
- `unique constraint (notification_id, principal_id)`

### Notification

- сохранён legacy `is_read` как переходная совместимость;
- фактический read-state перенесён на per-principal модель через `notification_reads`.

---

## 5) Какие проверки выполнены

```bash
cd apps/api && python -m pip install -r requirements.txt
cd apps/api && python -m alembic upgrade head
cd apps/api && pytest -q
cd apps/web && npm install
cd apps/web && npm run build
```

---

## 6) Что осталось за пределами этого спринта

- Полный auth lifecycle (`/auth/login`, `refresh`, `logout`, `session store`).
- Real Xray integration (реальные источники telemetry/stats/server control semantics).
- Advanced alerts engine.
- Full export center.
- Production hardening infra (`reverse proxy/TLS`, `backup automation`, `observability stack` и т.д.).

---

## 7) Какие есть риски/компромиссы

| Риск / компромисс | Текущее состояние | Влияние на следующий спринт |
|---|---|---|
| Неполный перевод legacy-сущностей на migration-first | Часть исторической схемы всё ещё живёт в смешанном режиме bootstrap/migration | Замедлит переход к полностью предсказуемым релизным миграциям и усложнит планирование rollout на staging/prod. |
| Переходная зависимость от `Notification.is_read` | Поле сохранено ради совместимости, при этом read-state уже per-principal | Повлияет на консистентность бизнес-логики и тестов при расширении Notification Center и auth-модели. |
| SSE остаётся mock-driven | Поток событий не связан с реальным backend telemetry/Xray | Ограничит внедрение production-ready realtime UX и корректную валидацию freshness/alerts в следующем спринте. |
| Token-based security context без полного auth lifecycle | RBAC guards есть, но нет полноценного user/session lifecycle | Ограничит развитие управляемого доступа, аудита и операторских сценариев при расширении функционала. |

---

## Next Sprint Actions

| Задача | Приоритет | Основание | Ожидаемый результат | Рекомендуемый owner | Статус на входе в следующий спринт |
|---|---|---|---|---|---|
| Полный перевод legacy-сущностей на migration-first подход | P0 | Зафиксирован смешанный режим bootstrap/migration и риск для релизных миграций | Все рабочие таблицы и изменения схемы ведутся через Alembic, startup не зависит от `create_all()` в штатном режиме | Backend | Требует декомпозиции |
| Устранение переходной зависимости от legacy `Notification.is_read` | P0 | Отмечен переходный компромисс для совместимости уведомлений | Read-state полностью хранится per-principal, legacy-поле удалено/выведено из контракта без регрессий | Backend | Требует декомпозиции |
| Полный auth lifecycle | P0 | Явно вынесено за границы текущего спринта; сохраняется token-only модель | Реализованы `login/refresh/logout/session store` и совместимая интеграция с RBAC guards | Backend | Требует декомпозиции |
| Замена mock-driven SSE на реальный источник событий | P1 | Ограничение текущего real-time слоя зафиксировано в отчёте и README | SSE/streaming отражает реальные события backend/Xray и корректно пополняет Notification Center | Fullstack | Требует декомпозиции |
| Real Xray integration | P1 | В отчёте отмечено, что Xray остаётся scaffold | Провайдер получает реальные метрики/сессии/сервисные статусы с fallback-логикой | Backend | Требует декомпозиции |
| Production hardening infra | P1 | Вынесено за рамки спринта и влияет на readiness | Минимальный production baseline: безопасный reverse proxy/TLS, backup policy, observability baseline | DevOps | Требует декомпозиции |
| Advanced alerts engine | P2 | Явно указан как post-sprint scope | Базовые alert rules/instances с привязкой к notifications и audit trail | Fullstack | Готово к планированию |
| Full export center | P2 | Зафиксирован как вне текущего scope | Экспорт ключевых сущностей (audit, links, sessions) в управляемом формате и с RBAC-ограничениями | Fullstack | Готово к планированию |

---

## Recommended Sprint Focus

- Взять в первую очередь P0-задачи: migration-first завершение, снятие зависимости от `Notification.is_read`, декомпозиция полного auth lifecycle.
- Не объединять в один спринт полноценный auth lifecycle и full Real Xray integration при ограниченном ресурсе: оба направления высокорисковые и требуют отдельного QA-контура.
- Запускать замену mock-driven SSE только после стабилизации auth/migrations, чтобы избежать переработки realtime-контрактов.
- Планировать production hardening отдельным потоком с участием DevOps, но синхронизировать его с backend-изменениями по security и migrations.
- Не включать P2-функции в критический путь релиза до закрытия P0-рисков.

---

## Проверки

```bash
git status --short
```

---

## Список файлов

Файлов: 49

- `.env.example`
- `.github/workflows/ci.yml`
- `.gitignore`
- `README.md`
- `apps/api/.env.example`
- `apps/api/Dockerfile`
- `apps/api/alembic.ini`
- `apps/api/alembic/env.py`
- `apps/api/alembic/script.py.mako`
- `apps/api/alembic/versions/0001_rbac_notifications_sessions.py`
- `apps/api/alembic/versions/0002_notification_reads_and_rbac_hardening.py`
- `apps/api/app/__init__.py`
- `apps/api/app/api/__init__.py`
- `apps/api/app/api/routes.py`
- `apps/api/app/core/__init__.py`
- `apps/api/app/core/config.py`
- `apps/api/app/core/security.py`
- `apps/api/app/db/__init__.py`
- `apps/api/app/db/database.py`
- `apps/api/app/main.py`
- `apps/api/app/models/__init__.py`
- `apps/api/app/models/entities.py`
- `apps/api/app/providers/__init__.py`
- `apps/api/app/providers/base.py`
- `apps/api/app/schemas/__init__.py`
- `apps/api/app/schemas/api.py`
- `apps/api/app/services/__init__.py`
- `apps/api/app/services/services.py`
- `apps/api/requirements.txt`
- `apps/api/tests/test_api_smoke.py`
- `apps/web/Dockerfile`
- `apps/web/index.html`
- `apps/web/package-lock.json`
- `apps/web/package.json`
- `apps/web/postcss.config.js`
- `apps/web/src/App.tsx`
- `apps/web/src/components/ui.tsx`
- `apps/web/src/lib/utils.ts`
- `apps/web/src/main.tsx`
- `apps/web/src/styles.css`
- `apps/web/src/types/api.ts`
- `apps/web/src/vite-env.d.ts`
- `apps/web/tailwind.config.js`
- `apps/web/tsconfig.json`
- `apps/web/vite.config.ts`
- `docker-compose.yml`
- `docker/README.md`
- `docs/sprint-hardening-report.md`
- `packages/shared/README.md`
