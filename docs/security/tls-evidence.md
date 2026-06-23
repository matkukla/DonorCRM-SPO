# TLS Evidence

This document captures the live TLS posture of DonorCRM's production hosts
and Postgres connection. Refresh quarterly or before any security review.

**Last verified: 2026-06-22** (re-probed live; previous: 2026-05-07).
US-based donors only; no PCI / HIPAA / GDPR scope confirmed by product owner.

2026-06-22 live probe reproduced TLS 1.3 with `TLS_AES_256_GCM_SHA384` on both
edge hosts, and HSTS present on both (web `max-age=31536000`, frontend
`max-age=315360000`, both `includeSubDomains; preload`).

## Edge — `donorcrm-web.onrender.com` (Django API)

```bash
curl -sI -v --tlsv1.3 --tls-max 1.3 https://donorcrm-web.onrender.com/api/v1/health/ 2>&1 \
  | grep "SSL connection"
# SSL connection using TLSv1.3 / TLS_AES_256_GCM_SHA384 / X25519 / id-ecPublicKey
```

- **Negotiated:** TLS 1.3, cipher `TLS_AES_256_GCM_SHA384`, key exchange X25519.
- **Also accepted:** TLS 1.2 (for legacy clients).
- **Rejected:** TLS 1.1, TLS 1.0.
- **HSTS header (Django + Render edge):**
  `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
  emitted via `SECURE_HSTS_*` settings in [config/settings/prod.py](../../config/settings/prod.py).

## Edge — `donorcrm-frontend.onrender.com` (React static site)

```bash
curl -sI -v --tlsv1.3 --tls-max 1.3 https://donorcrm-frontend.onrender.com/ 2>&1 \
  | grep "SSL connection"
# SSL connection using TLSv1.3 / TLS_AES_256_GCM_SHA384 / X25519 / id-ecPublicKey
```

- **Negotiated:** TLS 1.3, cipher `TLS_AES_256_GCM_SHA384`.
- **HSTS:** `strict-transport-security: max-age=315360000; includeSubdomains; preload`.
  Render's edge sets a 10-year HSTS automatically; [render.yaml](../../render.yaml)
  also declares an explicit 1-year HSTS as a belt-and-suspenders measure
  (Render's value wins because the edge sets the header last).

## Application → Postgres

Connection enforced TLS via `dj_database_url(..., ssl_require=True)` in
[config/settings/prod.py](../../config/settings/prod.py).

The application performs a startup self-check that queries
`pg_stat_ssl` and refuses to start if the connection is not TLS 1.2+.
See [apps/core/db_tls_check.py](../../apps/core/db_tls_check.py). Because the
check is fail-closed, a running production web service is itself evidence that
the app↔DB link negotiated TLS 1.2+.

`DB_SSLMODE` now defaults to **`verify-full`** (cert chain + hostname
verification) in [config/settings/prod.py](../../config/settings/prod.py).
Operator notes:

1. If a deploy fails with "could not get server's host name from server
   certificate", Render's internal Postgres cert chains to a private CA not in
   the system bundle. Either set `DB_SSLROOTCERT` to a matching CA bundle, or
   fall back to `DB_SSLMODE=verify-ca`. **Never** downgrade to `require`
   (TLS without verification defeats the MITM protection).
2. The startup check logs `db.tls.check` with the negotiated version; confirm
   it appears in Render logs after each deploy.

## Application → External services

| Hop | TLS guarantee | Source |
|-----|---------------|--------|
| Sentry | TLS 1.2+ | `sentry-sdk` defaults; no override |
| SMTP (email) | TLS 1.2+ | `EMAIL_USE_TLS=True` in [config/settings/base.py](../../config/settings/base.py) |
| Render API (deploy) | TLS 1.2+ | Render-controlled |

No outbound integrations to third-party APIs at the application layer
beyond the above.

## Verification cadence

Run the curl probes quarterly. Re-run any time:
- A Django/Postgres major version bumps.
- Render announces an edge TLS policy change.
- A penetration test covers transit security.

A `testssl.sh` report can be added here for fuller cipher-suite coverage —
recommended before any external audit.
