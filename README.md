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

The service listens on `http://127.0.0.1:8000`. Open that address in your Mac browser for the interactive demonstration. Set `ZTNA_ADMIN_PASSWORD` before starting the service; it fails closed if the secret is absent. The username defaults to `admin`.

```sh
curl -s http://localhost:8000/health
curl -s -X POST http://localhost:8000/login -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"use-a-long-random-local-secret"}'
```

The homepage provides a browser-based login and application request flow. Enter the configured password, select the simulated managed/compliant posture checks, and request the portal or admin console. To exercise the API directly, use the returned `access_token` in `Authorization: Bearer <token>`, send `X-Device-Managed: true` and `X-Device-Compliant: true`, and request `/apps/portal` or `/apps/admin`.

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

The project is deployed on Render at <https://ztna-demo-gateway.onrender.com>. The Blueprint uses the Docker web service and stores `ZTNA_ADMIN_PASSWORD` as a Render secret; the secret is not in this repository. The free Render instance can spin down when idle, so its first request may take longer. The live health check and browser login/deny/permit flow were verified on Nov. 3, 2026. This is a public demo; caller-supplied posture claims are not suitable for protecting real applications. Never commit `.env` or secret values.

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

## Wazuh monitoring (local demonstration)

The gateway emits structured JSON audit events that a Wazuh agent can collect. Example agent configuration and Wazuh manager alert rules are in [`wazuh/`](wazuh/). This adds monitoring for denied access and repeated failed sign-ins; Wazuh does not make or enforce gateway access decisions. Run the gateway on the same Mac/Linux host as the Wazuh agent and configure the agent to monitor `/tmp/ztna-audit.jsonl`. The manager and agent must already be installed and enrolled; their installation is separate from this app. Check [`wazuh/README.md`](wazuh/README.md) for setup and verification steps.

This integration is for the local demonstration. Render's filesystem is ephemeral and its internal audit file is not reachable by an agent on your Mac, so the committed sample config does not claim to collect Render events. Forwarding hosted events to a secured central collector is a separate deployment task.
