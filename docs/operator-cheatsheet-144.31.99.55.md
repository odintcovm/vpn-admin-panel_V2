# Operator Cheatsheet — 144.31.99.55

## Rollout (safe baseline)

```bash
cd /opt/vpn-admin-panel_V2
git fetch --all
git checkout codex/build-mvp-for-xray/vless-admin-panel-aj6luj
git pull --ff-only
./scripts/verify-release-readiness.sh
./scripts/backup.sh

cp -n .env.example .env
sed -i 's/^APP_PROVIDER=.*/APP_PROVIDER=xray/' .env
sed -i 's/^APP_ENV=.*/APP_ENV=production/' .env
sed -i 's/^DEV_ROLE_EMULATION=.*/DEV_ROLE_EMULATION=false/' .env
sed -i 's/^SCHEMA_MANAGEMENT_MODE=.*/SCHEMA_MANAGEMENT_MODE=alembic/' .env
sed -i 's/^ENABLE_TLS_PROXY=.*/ENABLE_TLS_PROXY=false/' .env
sed -i 's/^ENABLE_XRAY_PUBLIC=.*/ENABLE_XRAY_PUBLIC=false/' .env
sed -i 's/^DOMAIN=.*/DOMAIN=/' .env

./deploy.sh prod-like
```

## Smoke-check

```bash
./scripts/health-check.sh
curl -s http://127.0.0.1/health
curl -s -H 'x-api-token: admin-token' http://127.0.0.1/api/auth/me
curl -s -H 'x-api-token: admin-token' http://127.0.0.1/api/providers
curl -s -H 'x-api-token: admin-token' http://127.0.0.1/api/links | head -c 300
ss -ltnp | grep ':443'
```

## Rollback

```bash
./scripts/restore.sh backups/<backup_file>.tar.gz
./scripts/health-check.sh
```
