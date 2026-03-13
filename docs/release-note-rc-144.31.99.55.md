# Release Note (RC) — vpn-admin-panel_V2

## Release status

Ветка готова как release-candidate для rollout на VPS `144.31.99.55` с safe baseline:

- base compose не занимает `443`;
- host Xray на `443` не должен быть затронут;
- deploy/ops слой совместим с `docker compose` и `docker-compose v1.29.2`;
- есть backup/restore/update/health-check и статическая release-проверка.

## Что зафиксировано как готовое

- Deployment normalization (safe base + overrides).
- Verification/release-readiness checks.
- Final stabilization (улучшенный preflight deploy + handoff docs + operator cheatsheet).

## Что остаётся ограничением

- Runtime e2e-подтверждение зависит от Docker на целевой машине.
- TLS для панели — только optional сценарий при свободном `443` и валидном домене.
- Mock-driven telemetry/SSE остаётся допустимым ограничением текущего этапа.

## Рекомендуемый rollout режим для 144.31.99.55

- `./deploy.sh prod-like`
- `ENABLE_TLS_PROXY=false`
- `ENABLE_XRAY_PUBLIC=false`
- `DOMAIN=`

## Артефакты handoff

- Runbook: `docs/vps-rollout-144.31.99.55.md`
- Cheatsheet: `docs/operator-cheatsheet-144.31.99.55.md`
- Static verification: `./scripts/verify-release-readiness.sh`
