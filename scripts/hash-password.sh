#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: ./scripts/hash-password.sh <password>"
  exit 1
fi

python - <<'PY' "$1"
import sys
from passlib.context import CryptContext
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
print(pwd.hash(sys.argv[1]))
PY
