# VPS rollout runbook (144.31.99.55)

## 1) Update code

```bash
cd /opt/vpn-admin-panel_V2
git fetch --all --tags --prune
git checkout codex/server-baseline-20260313
git pull --ff-only
```

## 2) Safe install/deploy (host Xray on 443 must stay untouched)

```bash
./install.sh safe xray
```

## 3) Explicit env baseline (optional hard pin)

```bash
grep -E '^(DEPLOY_MODE|APP_PROVIDER|ENABLE_TLS_PROXY|ENABLE_XRAY_PUBLIC|DOMAIN|AUTH_ENABLED)=' .env
# expected:
# DEPLOY_MODE=safe
# APP_PROVIDER=xray
# ENABLE_TLS_PROXY=false
# ENABLE_XRAY_PUBLIC=false
# DOMAIN=
# AUTH_ENABLED=true
```

## 4) Post-deploy checks

```bash
./scripts/post-deploy-check.sh
./scripts/health-check.sh
curl -s http://127.0.0.1/health
curl -s -H 'x-api-token: admin-token' http://127.0.0.1/api/auth/me
curl -s -H 'x-api-token: admin-token' http://127.0.0.1/api/providers
ss -ltnp | grep ':443'
```

## 5) UI checks

1. Open `http://144.31.99.55`
2. Login with admin credentials from `.env`
3. Open `VLESS ссылки` -> `Profiles`
4. Validate copy/download

## 6) Rollback

```bash
./scripts/backup.sh
./scripts/restore.sh backups/<file>.tar.gz
./scripts/post-deploy-check.sh
```
