"""Educational ZTNA access gateway prototype; not production identity software."""
from __future__ import annotations

import hmac
import json
import os
import time
from functools import wraps
from pathlib import Path
from secrets import token_urlsafe

from flask import Flask, jsonify, request

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = True
ADMIN_USER = os.getenv("ZTNA_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ZTNA_ADMIN_PASSWORD", "change-me-now")
TOKEN_TTL_SECONDS = int(os.getenv("ZTNA_TOKEN_TTL_SECONDS", "3600"))
AUDIT_LOG = Path(os.getenv("ZTNA_AUDIT_LOG", "/tmp/ztna-audit.jsonl"))
TOKENS: dict[str, dict] = {}


def audit(event: str, user: str | None, detail: dict) -> None:
    record = {"time": int(time.time()), "event": event, "user": user,
              "source_ip": request.remote_addr, "detail": detail}
    try:
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_LOG.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, separators=(",", ":")) + "\n")
    except OSError:
        app.logger.exception("Could not write audit event")


def current_identity() -> dict | None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth.removeprefix("Bearer ").strip()
    identity = TOKENS.get(token)
    if identity and identity["expires_at"] > time.time():
        return identity
    if identity:
        TOKENS.pop(token, None)
    return None


def requires_identity(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        identity = current_identity()
        if not identity:
            audit("access_denied", None, {"path": request.path, "reason": "missing_or_expired_token"})
            return jsonify(error="authentication_required"), 401
        request.identity = identity
        return fn(*args, **kwargs)
    return wrapped


@app.get("/")
def index():
    return jsonify(service="ZTNA demonstration gateway", status="ok",
                   endpoints=["POST /login", "GET /apps/portal", "GET /apps/admin", "GET /health"])


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.post("/login")
def login():
    body = request.get_json(silent=True) or {}
    username, password = str(body.get("username", "")), str(body.get("password", ""))
    if not (hmac.compare_digest(username, ADMIN_USER) and hmac.compare_digest(password, ADMIN_PASSWORD)):
        audit("login_denied", username or None, {"reason": "invalid_credentials"})
        return jsonify(error="invalid_credentials"), 401
    token = token_urlsafe(32)
    TOKENS[token] = {"user": username, "role": "admin", "expires_at": time.time() + TOKEN_TTL_SECONDS}
    audit("login_success", username, {"expires_in": TOKEN_TTL_SECONDS})
    return jsonify(access_token=token, token_type="Bearer", expires_in=TOKEN_TTL_SECONDS)


def device_posture() -> tuple[bool, dict]:
    # Demo attestation: client supplies these claims; production requires trusted attestation.
    managed = request.headers.get("X-Device-Managed", "false").lower() == "true"
    compliant = request.headers.get("X-Device-Compliant", "false").lower() == "true"
    return managed and compliant, {"managed": managed, "compliant": compliant}


def authorize(app_name: str, allowed_roles: set[str]):
    identity = request.identity
    trusted, posture = device_posture()
    allowed = identity["role"] in allowed_roles and trusted
    audit("access_allowed" if allowed else "access_denied", identity["user"],
          {"application": app_name, "role": identity["role"], "device_posture": posture,
           "reason": "policy_permit" if allowed else "policy_denied"})
    if not allowed:
        return jsonify(error="access_denied", application=app_name,
                       device_posture=posture, policy="role_and_managed_compliant_device_required"), 403
    return None


@app.get("/apps/portal")
@requires_identity
def portal():
    denial = authorize("portal", {"admin", "employee"})
    if denial:
        return denial
    return jsonify(application="employee-portal", message="Access granted by ZTNA policy",
                   user=request.identity["user"])


@app.get("/apps/admin")
@requires_identity
def admin_app():
    denial = authorize("admin-console", {"admin"})
    if denial:
        return denial
    return jsonify(application="admin-console", message="Administrative access granted",
                   user=request.identity["user"])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
