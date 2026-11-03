# Architecture and threat model

## Components and request path

```text
Remote client
    | HTTPS should be terminated by a trusted edge in a real deployment
    v
Flask access gateway (/login, /apps/*)
    |-- configured credential check -> short-lived in-memory bearer token
    |-- policy decision: authenticated identity + role + device posture claims
    |-- append-only JSONL decision event (local file)
    v
Named application route (portal or admin console)
```

The prototype exposes only named application routes and never places the client on an internal subnet. Each request to a protected route is checked independently. `/apps/portal` permits admin and employee roles; `/apps/admin` permits only admin. Both require a valid token and managed/compliant posture claims.

## Policy rule

`permit = token_valid AND role_allowed_for_application AND managed_claim AND compliant_claim`

A failed authentication yields HTTP 401. A failed authorization or posture decision yields HTTP 403. The gateway records permit and deny events with timestamp, username where known, source IP, application, and decision details.

## Trust boundaries and assumptions

- The client-to-gateway boundary is untrusted. The prototype itself does not configure TLS.
- Identity is a single configured username/password, with constant-time string comparisons, not an enterprise IdP.
- Device posture headers are caller-controlled demonstration inputs. They do not prove device state.
- Tokens are random bearer strings, expire after a configurable TTL, and exist only in one process's memory. Restarting a worker invalidates its tokens; multiple workers do not share tokens.
- Audit events are local append operations; they are not tamper-proof or durable in ephemeral hosting.

## Threats addressed in demonstration

| Threat | Demonstration control | Limitation |
|---|---|---|
| Unauthenticated access | Bearer token required on protected app routes | No MFA or external identity integration |
| Stolen/guessable session identifier | Cryptographically random token and expiry | Bearer token theft remains possible; no revocation endpoint |
| Broad network reach after login | Explicit application routes and per-route policy | Only two demonstration routes |
| Untrusted device | Managed/compliant claims checked on every request | Claims are spoofable and not device attestation |
| Untraceable decisions | JSONL permit/deny events | Local file is not durable or tamper resistant |

## Production evolution

Use a supported OIDC identity provider (for example, Keycloak), MFA, signed and audience-scoped sessions, a shared revocation/session store, cryptographically verified device posture from an MDM/EDR trust source, TLS at a controlled ingress, rate limiting, CSRF protections where browser cookies are introduced, hardened secret management, centralized protected audit storage, and penetration testing. Place the gateway behind a private application connector where appropriate. These are future work, not implemented claims.
