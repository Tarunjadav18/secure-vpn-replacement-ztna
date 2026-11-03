# Secure VPN Replacement Using Zero Trust Network Access

An executable educational prototype of application-specific remote access. A small Flask gateway checks an identity, short-lived bearer token, role, and device posture before allowing access to protected application routes. It demonstrates a ZTNA control flow without creating a network tunnel.

> **Scope:** This is a learning prototype, not a production security gateway. Device posture headers are self-asserted by the caller, tokens are held in process memory, there is one configured administrator, and there is no TLS termination, MFA, external identity provider, distributed session store, or cryptographic device attestation. Do not use it to protect real systems.

## Run locally

Requires Python 3.9+.

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export ZTNA_ADMIN_PASSWORD='use-a-long-random-local-secret'
python -m src.ztna.app
```

The service listens on `http://localhost:8000`. Login credentials default to `admin` and `change-me-now`; always set `ZTNA_ADMIN_PASSWORD` before use.

```sh
curl -s http://localhost:8000/health
curl -s -X POST http://localhost:8000/login -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"use-a-long-random-local-secret"}'
```

Use the returned `access_token` in `Authorization: Bearer <token>`. For the demo posture check, send `X-Device-Managed: true` and `X-Device-Compliant: true`. Then request `/apps/portal` or `/apps/admin`.

## Test

```sh
python -m unittest discover -s tests -v
```

## Docker

```sh
docker build -t ztna-demo .
docker run --rm -p 8000:8000 -e ZTNA_ADMIN_PASSWORD='use-a-long-random-secret' ztna-demo
```

## Deploy to Render

`render.yaml` describes a Docker web service and prompts for `ZTNA_ADMIN_PASSWORD` as a secret (`sync: false`). Connect this repository in Render, set that environment variable in the service dashboard, deploy, then confirm `/health` returns `{"status":"ok"}`. Never commit `.env` or secret values. This deployment is a public demo; the current self-asserted posture design is not suitable for production.

## Architecture and project report

- [Architecture and threat model](docs/ARCHITECTURE.md)
- [IEEE-style project report source](docs/ieee_report.tex)

## Endpoints

| Route | Requirement | Result |
|---|---|---|
| `GET /health` | None | Health response |
| `POST /login` | Configured username/password | In-memory bearer token with expiry |
| `GET /apps/portal` | Valid token, managed + compliant posture, admin/employee role | Portal response |
| `GET /apps/admin` | Valid token, managed + compliant posture, admin role | Admin response |

Every login and access decision is appended as JSON Lines to `ZTNA_AUDIT_LOG` (default `/tmp/ztna-audit.jsonl`).
