# Operator cheatsheet

## Install/deploy
```bash
./install.sh safe xray
```

## Doctor
```bash
./scripts/doctor.sh safe
```

## Health
```bash
./scripts/post-deploy-check.sh
./scripts/health-check.sh
```

## Login auth
```bash
./scripts/hash-password.sh 'new-password'
# put hash into ADMIN_PASSWORD_HASH in .env
```

## Logs
```bash
./scripts/logs.sh
./scripts/logs.sh api
```

## Backup / restore
```bash
./scripts/backup.sh
./scripts/restore.sh backups/<file>.tar.gz
```

## Update
```bash
./scripts/update.sh
```
