# VPS Rollout Runbook — 144.31.99.55

Цель: безопасно обновить панель, **не затрагивая host systemd Xray на 443**.

## 0) Preconditions

```bash
cd /opt/vpn-admin-panel_V2
```

Проверь compose binary:

```bash
docker compose version || docker-compose version
```

Проверь, что host Xray жив:

```bash
systemctl status xray --no-pager
ss -ltnp | grep ':443'
```

## 1) Backup before update

```bash
./scripts/backup.sh
ls -lah backups/
```

## 2) Update source

```bash
git fetch --all
git checkout codex/build-mvp-for-xray/vless-admin-panel-aj6luj
git pull --ff-only
```

## 3) Safe prod-like env for this VPS

```bash
cp -n .env.example .env
sed -i 's/^APP_ENV=.*/APP_ENV=production/' .env
sed -i 's/^DEV_ROLE_EMULATION=.*/DEV_ROLE_EMULATION=false/' .env
sed -i 's/^SCHEMA_MANAGEMENT_MODE=.*/SCHEMA_MANAGEMENT_MODE=alembic/' .env

# keep host dataplane untouched
sed -i 's/^ENABLE_TLS_PROXY=.*/ENABLE_TLS_PROXY=false/' .env
sed -i 's/^ENABLE_XRAY_PUBLIC=.*/ENABLE_XRAY_PUBLIC=false/' .env
sed -i 's/^DOMAIN=.*/DOMAIN=/' .env
```

## 4) Deploy

```bash
./deploy.sh prod-like
```

## 5) Post-deploy smoke

```bash
./scripts/health-check.sh
curl -s http://127.0.0.1/health
curl -s -H 'x-api-token: admin-token' http://127.0.0.1/api/auth/me
curl -s -H 'x-api-token: admin-token' http://127.0.0.1/api/links | head -c 300
```

UI checks:
- открыть `http://144.31.99.55`
- открыть `VLESS ссылки` -> `Profiles`
- проверить copy/download payload

## 6) Verify host Xray still owns 443

```bash
ss -ltnp | grep ':443'
systemctl status xray --no-pager
```

Ожидание: 443 остаётся за host Xray/service unit, не за proxy контейнером панели.

## 7) Fast rollback

Вариант A — rollback DB/config/env из backup:

```bash
./scripts/restore.sh backups/<backup_file>.tar.gz
./scripts/health-check.sh
```

Вариант B — откат к предыдущему git-коммиту + redeploy:

```bash
git log --oneline -n 5
git checkout <previous_commit>
./deploy.sh prod-like
./scripts/health-check.sh
```

## 8) Optional TLS mode (only if 443 is intentionally free)

```bash
sed -i 's/^DOMAIN=.*/DOMAIN=panel.example.com/' .env
sed -i 's/^ENABLE_TLS_PROXY=.*/ENABLE_TLS_PROXY=true/' .env
./deploy.sh prod-like
```

> Не включать на данном VPS, если host Xray уже использует 443.
