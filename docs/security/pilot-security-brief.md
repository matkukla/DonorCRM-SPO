# DonorCRM — Pilot Security Brief

> **Purpose of this file.** This is a source brief for Claude Cowork to turn
> into a polished, customer-facing security overview (one-pager / PDF / slide).
> It is self-contained — every claim below is drawn from verified code,
> configuration, passing tests, or a live production probe. Dates and figures
> are accurate as of the verification date.
>
> **Verification date:** 2026-06-22
> **Scope:** US-based donors only. No card (PCI), health (HIPAA), or EU
> (GDPR) data in scope. State breach-notification laws (50-state baseline) apply.
> **Audience for the finished document:** prospective pilot organizations,
> their security reviewers, and internal stakeholders.

---

## 1. Executive summary

DonorCRM protects donor data with **industry-standard encryption in transit and
at rest**, verified both by an automated test suite and by a live probe of the
production environment:

- **In transit: TLS 1.3** end to end, negotiating `TLS_AES_256_GCM_SHA384`.
- **At rest: AES-256**, in two independent layers — full-database disk
  encryption *plus* application-level field encryption of donor PII.

The encryption posture is **cleared for pilot**. Remaining hardening items
(hardware-backed key custody, an external penetration test) are roadmap
enhancements, not gaps that block a controlled pilot with real donor data.

---

## 2. Encryption in transit — TLS 1.3

| Hop | Guarantee | How it is enforced |
|-----|-----------|--------------------|
| Browser → application | **TLS 1.3**, cipher `TLS_AES_256_GCM_SHA384`, X25519 key exchange | Managed TLS at the platform edge; verified live 2026-06-22 |
| Browser → application | HTTPS only | HTTP→HTTPS redirect; HSTS with `includeSubDomains; preload` (1-year app header, 10-year edge header) |
| Application → database | **TLS 1.2+ required**, cert chain + hostname verified (`verify-full`) | Connection refuses non-TLS; a **fail-closed startup check** queries the live connection and refuses to boot under TLS < 1.2 |
| Application → email / error-monitoring | TLS 1.2+ | Provider defaults; TLS enforced for outbound mail |

Supporting controls: secure (HTTPS-only) session and CSRF cookies, a strict
Content-Security-Policy, and standard hardening headers (`X-Frame-Options:
DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`,
`Permissions-Policy`).

**Why it matters:** TLS 1.3 removes the legacy cipher and downgrade weaknesses
of older versions. Because the application-to-database TLS check is fail-closed,
a running production system is itself continuous evidence that the internal link
is encrypted.

---

## 3. Encryption at rest — AES-256 (defense in depth)

Donor data is protected by **two independent AES-256 layers**, so a compromise
of one does not expose plaintext:

| Layer | What it protects | Mechanism |
|-------|------------------|-----------|
| **Disk** | The entire database volume | Platform-managed at-rest encryption, AES-256 |
| **Field-level** | Sensitive donor PII columns | Application AES-256-GCM (authenticated encryption), keys held by the application — *not* the database |
| **Backups** | Off-platform backup archives | GPG symmetric AES-256 |

### Field-level encryption details

- **Algorithm:** AES-256-GCM (authenticated encryption). Tampering with stored
  ciphertext is detected and rejected on read, not returned as corrupt data.
- **Per-field binding (v2 envelope):** each value is cryptographically bound to
  its specific model and column. A ciphertext copied to a different column or
  row fails authentication — defending against database-level relocation.
- **Random, non-reused nonces:** a fresh 96-bit nonce per write.
- **Key rotation:** supported and tooled; an idempotent, resumable command
  re-encrypts all protected data under a new key with no downtime.

### What field-level encryption defends against

Beyond physical disk theft (covered by the disk layer), field-level encryption
ensures these data-egress paths reveal **ciphertext only**:

- a leaked read-only database credential (e.g. an analytics pipeline),
- an accidental database dump copied to object storage,
- a future SQL-injection or application bug that surfaces rows,
- a snapshot restored into a lower (non-production) environment.

### Protected donor PII (9 fields)

Email, primary phone, secondary phone, street address, contact notes,
relationship/journal notes, prayer-intention notes, and gift descriptions
(one-time and recurring). Encrypted fields that must remain searchable (email,
phone) use a separate keyed blind-index column so exact-match lookups work
without exposing plaintext.

### Documented data-handling decision

Contact **names** and coarse location fields (city/state/postal code) are stored
unencrypted by deliberate policy: encrypting them would break typeahead search
and alphabetical ordering, while the high-sensitivity *identifiers* paired with
those names (email, phone) **are** encrypted. This is a reasoned trade-off for
the US-only scope, documented in the data-classification policy.

---

## 4. Access control & authentication

- **Role-based authorization** with four roles (admin, missionary, supervisor,
  coach) and object-level ownership checks; a single central data-scoping
  function governs whose records each user can see.
- **JWT authentication** with short-lived access tokens and refresh-token
  revocation.
- **Passwords** hashed with a modern algorithm (Argon2/PBKDF2).
- **Brute-force protection** via account lockout after repeated failures.
- **Administrative "view-as"** access is audit-logged.

---

## 5. Logging, monitoring & data lifecycle

- **Structured security audit log** for authentication, cryptographic
  operations, and the database TLS startup check.
- **PII scrubbing in error monitoring** — donor values are filtered before any
  error report leaves the system.
- **Append-only PII access log** with retention-based purge tooling.
- **Automated daily database backups**, plus quarterly restore tests against a
  documented checklist.

---

## 6. Vulnerability management

- Dependency CVE scanning and static security analysis run in CI.
- Repository-level secret scanning is enabled.
- External penetration test: recommended annually (see roadmap).

---

## 7. Roadmap — items beyond pilot scope

These are enhancements, not pilot blockers:

| Item | Benefit | Status |
|------|---------|--------|
| Hardware-backed key custody (KMS/HSM) | Protects keys even against application-server compromise; common enterprise ask | Designed; pending vendor decision |
| External penetration test | Independent assurance | Recommended annually |
| Encrypt login email / additional fields | Broader coverage | Deferred (touches auth flow) |

---

## 8. Verification cadence

- **Per release:** automated security scans and the encryption test suite must pass.
- **Quarterly:** refresh the live TLS probe, run a backup restore test, verify key backups.
- **Annual:** key rotation, security-control review, penetration test.

---

## 9. Source-of-truth references (internal)

For the finished external document these can be summarized rather than linked:

- Cryptographic architecture: `docs/security/crypto-architecture.md`
- Live TLS evidence: `docs/security/tls-evidence.md`
- Data classification: `docs/security/data-classification.md`
- Control-to-framework mapping: `docs/security/evidence-map.md`
- Encryption rollout runbook: `docs/security/encryption-rollout.md`
- Key management: `docs/security/key-management.md`
