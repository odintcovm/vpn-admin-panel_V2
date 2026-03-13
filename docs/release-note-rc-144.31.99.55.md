# Release note RC (server-baseline-20260313)

## Included
- VM/VPS appliance baseline via `install.sh`.
- Doctor/preflight (`scripts/doctor.sh`).
- Post-deploy validation (`scripts/post-deploy-check.sh`).
- Deploy modes: `safe`, `full`, `behind-ingress`.
- Provider-aware API/runtime: `xray`, `wg`, `avg`, `mock`.
- Auth baseline: login/logout + cookie session + token fallback.

## Staged support
- `xray`: baseline.
- `wg`: staged v1 provider/runtime path.
- `avg`: staged v1 provider/runtime path.

## Safety
- Safe mode does not require host `443`.
- Coexistence with host Xray on `443` preserved.
