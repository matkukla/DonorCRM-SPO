# TLS Evidence

This document captures the live TLS posture of DonorCRM's production hosts
and Postgres connection. Refresh quarterly or before any security review.

**Last verified: 2026-05-07** (US-based donors only; no PCI / HIPAA / GDPR
scope confirmed by product owner).

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
See [apps/core/db_tls_check.py](../../apps/core/db_tls_check.py).

To upgrade from `sslmode=require` to `sslmode=verify-full` (recommended for
audit-grade evidence):

1. Confirm Render's Postgres certificate chains to a public CA, or download
   the Render-provided CA bundle as a build asset.
2. Set `DB_SSLMODE=verify-full` and `DB_SSLROOTCERT=/path/to/ca-bundle` in
   the Render web service environment.
3. Redeploy. The startup check logs `db.tls.check` with the negotiated
   version; verify it appears in Render logs.

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
