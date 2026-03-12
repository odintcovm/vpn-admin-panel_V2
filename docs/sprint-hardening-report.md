# Sprint Hardening Report — vpn-admin-panel_V2

## Sprint Goal Review

| Цель спринта | Статус | Доказательство | Комментарий / Отклонение |
|---|---|---|---|
| Ужесточить RBAC и dev-role emulation | Выполнено | Добавлены env-флаги `app_env`, `dev_role_emulation`, `schema_management_mode`; `x-role` ограничен dev/test режимом; реализованы `SecurityPrincipal` и `require_permission`; ошибки `DEV_ROLE_EMULATION_DISABLED` и `PERMISSION_DENIED`; расширен `/api/auth/me`. | Полный auth lifecycle по-прежнему вне scope; текущая схема остаётся token-based, что является переходным вариантом до user/session модели. |
| Перевести notifications на per-principal read-state | Выполнено | Добавлена модель `NotificationRead` с уникальностью `(notification_id, principal_id)`; реализованы сервисы list/read/read-all на основе `principal_id`; API `/api/notifications*` работает в principal-контексте. | Сохранён legacy-флаг `Notification.is_read` для совместимости; это осознанный переходный слой до полного удаления legacy-поля. |
| Усилить migration discipline | Частично | Добавлена миграция `0002_notification_reads_and_rbac_hardening`; в `main.py` `create_all()` работает только в `bootstrap`, основной режим — migration-first через Alembic; README дополнен командами миграций. | Исторические legacy-сущности ещё не полностью переведены в единый migration-first контур; это отдельная задача следующего спринта. |
| Расширить hardening test coverage | Выполнено | В `test_api_smoke.py` добавлены negative-тесты RBAC, сценарии `x-role` enable/disable, контракт `/api/auth/me`, per-principal notifications и фильтр sessions. | Покрытие по-прежнему в основном smoke+contract; нет полного e2e и нагрузочных сценариев. |
| Обновить frontend-совместимость и документацию | Выполнено | Обновлены frontend-типы (`AuthMe`, `NotificationItem.read_at`), нормализация ошибок (`detail.error`), README дополнен безопасным запуском, миграциями, role emulation и ограничениями. | SSE остаётся mock-driven; документация фиксирует это ограничение, но не заменяет отсутствие real telemetry. |

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
  - безусловный `create_all()` убран из стандартного старта, оставлен только для `bootstrap`-режима.
- Расширено покрытие hardening-тестами:
  - negative RBAC;
  - проверка поведения `x-role` при disabled/enabled emulation;
  - изоляция read-state уведомлений по principal;
  - фильтрация sessions;
  - проверка контракта `/api/auth/me`.
- Поддержана frontend-совместимость:
  - обновлены типы API;
  - доработан parser ошибок под nested `detail.error`.
- Документация (README) обновлена для безопасного онбординга и запуска.

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

## 3) Какие API добавлены/изменены

| Endpoint | Method | Назначение |
|---|---|---|
| `/api/auth/me` | GET | Возврат текущего security context: `subject_id`, `role`, `permissions`, `dev_role_emulation_enabled`. |
| `/api/notifications` | GET | Получение уведомлений с per-principal read-state (`is_read`, `read_at`). |
| `/api/notifications/{notification_id}/read` | POST | Пометка уведомления прочитанным для текущего principal. |
| `/api/notifications/read-all` | POST | Пометка всех уведомлений прочитанными для текущего principal. |

## 4) Какие модели данных добавлены/изменены

- `NotificationRead` (новая сущность):
  - `notification_id`;
  - `principal_id`;
  - `read_at`;
  - unique constraint `(notification_id, principal_id)`.
- `Notification`:
  - сохранён legacy `is_read` как переходная совместимость;
  - фактический read-state перенесён на per-principal модель через `notification_reads`.

## 5) Какие проверки выполнены

- `cd apps/api && python -m pip install -r requirements.txt`
- `cd apps/api && python -m alembic upgrade head`
- `cd apps/api && pytest -q`
- `cd apps/web && npm install`
- `cd apps/web && npm run build`

## 6) Что осталось за пределами этого спринта

- Полный auth lifecycle (`/auth/login`, refresh, logout, session store).
- Real Xray integration (реальные источники telemetry/stats/server control semantics).
- Advanced alerts engine.
- Full export center.
- Production hardening infra (reverse proxy/TLS, backup automation, observability stack и т.д.).

## 7) Какие есть риски/компромиссы

| Риск / компромисс | Текущее состояние | Влияние на следующий спринт |
|---|---|---|
| Неполный перевод legacy-сущностей на migration-first | Часть исторической схемы всё ещё живёт в смешанном режиме bootstrap/migration | Может замедлить релизные миграции и усложнить предсказуемые обновления схемы на средах staging/prod. |
| Переходная зависимость от `Notification.is_read` | Поле сохранено ради совместимости, при этом read-state уже per-principal | Может создавать неоднозначность в бизнес-логике и тестах до полного удаления legacy-флага. |
| SSE остаётся mock-driven | Поток событий не связан с реальным backend telemetry/Xray | Ограничивает ценность real-time UX и мешает закрыть production-ready критерии мониторинга. |
| Token-based security context без полного auth lifecycle | RBAC guards есть, но нет полноценного user/session lifecycle | Ограничивает управляемость доступа, аудит и развитие multi-operator сценариев в следующих релизах. |

---

## Next Sprint Actions

| Задача | Приоритет | Основание | Ожидаемый результат | Рекомендуемый owner | Статус на входе в следующий спринт |
|---|---|---|---|---|---|
| Полный перевод legacy-сущностей на migration-first подход | P0 | В текущем отчёте зафиксирован смешанный режим bootstrap/migration и риск для стабильных релизных миграций | Все рабочие таблицы и изменения схемы ведутся через Alembic, startup не зависит от `create_all()` в штатном режиме | Backend | Требует декомпозиции |
| Устранение переходной зависимости от legacy `Notification.is_read` | P0 | Отмечен переходный компромисс для совместимости уведомлений | Read-state полностью хранится per-principal, legacy-поле удалено/выведено из контракта без регрессий | Backend | Требует декомпозиции |
| Полный auth lifecycle | P0 | Явно вынесено за границы текущего спринта; сохраняется token-only модель | Реализованы login/refresh/logout/session store и совместимая интеграция с RBAC guards | Backend | Требует декомпозиции |
| Замена mock-driven SSE на реальный источник событий | P1 | Ограничение текущего real-time слоя зафиксировано в отчёте/README | SSE/streaming отражает реальные события backend/Xray и корректно пополняет Notification Center | Fullstack | Требует декомпозиции |
| Real Xray integration | P1 | В отчёте отмечено, что Xray остаётся scaffold | Провайдер получает реальные метрики/сессии/сервисные статусы с fallback-логикой | Backend | Требует декомпозиции |
| Production hardening infra | P1 | Вынесено за рамки спринта и влияет на readiness | Минимальный production baseline: безопасный reverse proxy/TLS, backup policy, observability baseline | DevOps | Требует декомпозиции |
| Advanced alerts engine | P2 | Явно указан как post-sprint scope | Базовые alert rules/instances с привязкой к notifications и audit trail | Fullstack | Готово к планированию |
| Full export center | P2 | Зафиксирован как вне текущего scope | Экспорт ключевых сущностей (audit, links, sessions) в управляемом формате и с RBAC-ограничениями | Fullstack | Готово к планированию |

## Recommended Sprint Focus

1. **Сфокусировать следующий спринт на P0-треке безопасности и устойчивости**: migration-first завершение + закрытие legacy `Notification.is_read` + декомпозиция полного auth lifecycle. Это снижает архитектурный риск и повышает предсказуемость релизов.
2. **Не смешивать в одном спринте глубокий auth lifecycle и full Real Xray integration**, если команда ограничена по ресурсу: обе задачи сложные, с высоким интеграционным риском и требуют отдельного QA-контура.
3. **SSE real-source брать после стабилизации auth/migrations**, чтобы не строить realtime-поток поверх переходных security/data контрактов.
4. **Production hardening infra планировать как отдельный поток с DevOps-участием**, но синхронизировать с backend-изменениями по миграциям и auth для единого release gate.
5. **P2-фичи (alerts/export) не ставить в критический путь релиза**, пока не сняты P0-риски по данным и доступу.
