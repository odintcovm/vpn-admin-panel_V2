# Release Note (RC) — vpn-admin-panel_V2

## Release status

Ветка готова как release-candidate для rollout на VPS `144.31.99.55` с safe baseline:

- base compose не занимает `443`;
- host Xray на `443` не должен быть затронут;
- deploy/ops слой совместим с `docker compose` и `docker-compose v1.29.2`;
- providers: `xray`, `wg`, `avg`, `mock`;
- auth v1: login/logout cookie session + token fallback for ops.

## Что зафиксировано как готовое

- Deployment normalization (safe base + overrides).
- Verification/release-readiness checks.
- Multi-provider architecture v1.
- Dashboard/API/Web authorization baseline.

## Что остаётся ограничением

- WG/AVG — provider scaffold v1, без полного parity с Xray.
- Runtime e2e-подтверждение зависит от Docker на целевой машине.
- TLS для панели — только optional сценарий при свободном `443` и валидном домене.

## Рекомендуемый rollout режим для 144.31.99.55

- `APP_PROVIDER=xray`
- `./deploy.sh prod-like`
- `ENABLE_TLS_PROXY=false`
- `ENABLE_XRAY_PUBLIC=false`
- `DOMAIN=`

## Артефакты handoff

- Runbook: `docs/vps-rollout-144.31.99.55.md`
- Cheatsheet: `docs/operator-cheatsheet-144.31.99.55.md`
- Static verification: `./scripts/verify-release-readiness.sh`
