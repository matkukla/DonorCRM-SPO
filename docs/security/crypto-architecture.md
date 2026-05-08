# DonorCRM Cryptographic Architecture

**Status:** AES-256-GCM (v1) shipped 2026-05-07.
**Owner:** engineering.
**Audience:** internal engineers, external security auditors.

## Goals

1. Donor PII and free-text donor-interaction notes are unreadable in any
   data-egress path that does not have a live application key (DB dumps,
   read-replicas, analytics exports, snapshots, backup tarballs).
2. Algorithm primitives meet contemporary "industry-standard" expectations
   (AES-256, TLS 1.3) that map cleanly onto SOC 2-style control language.
3. Cryptographic agility — algorithm or key-custody changes require a
   single rotation pass over each encrypted column, not a redesign.

## Layers (defense in depth)

| Layer | Mechanism | Algorithm | Key custody |
|-------|-----------|-----------|-------------|
| Render-managed disk | At-rest encryption (Render-controlled) | AES-256 | Render |
| Application — field level (this doc) | AES-256-GCM v1 envelope | AES-256-GCM | App env var (Phase 5: KMS) |
| Application → Postgres (in-transit) | TLS | TLS 1.2+, TLS 1.3 ideal | Render TLS cert |
| Browser → app (in-transit) | TLS | TLS 1.3 (TLS_AES_256_GCM_SHA384) | Render edge cert |
| Off-provider backups | GPG symmetric | AES-256 (`--cipher-algo AES256`) | Operator passphrase |

## Field-level encryption — v1 envelope

Storage format (UTF-8 string, stored in a Postgres `TEXT` column):

```
v1:<base64url-unpadded(nonce || ciphertext || tag)>
```

| Component | Bytes | Notes |
|-----------|-------|-------|
| Version prefix | 3 (text) | `v1:` — outside the base64 payload so detection is unambiguous |
| Nonce | 12 | NIST SP 800-38D recommended length; from `os.urandom` per write |
| Ciphertext | varlen | Equal to plaintext length (GCM is a stream cipher) |
| Auth tag | 16 | Appended to ciphertext by the `cryptography` library |

### Why GCM (and why not Fernet)

- Fernet is AES-128-CBC + HMAC-SHA256 — fine for confidentiality but uses
  a 128-bit key; auditors and customer security questionnaires often ask
  for "AES-256."
- GCM is the AEAD mode used in TLS 1.3 cipher suites (`TLS_AES_256_GCM_*`),
  HTTPS-grade familiarity for reviewers.
- Authenticated encryption (the GCM tag) detects tampering; a flipped byte
  raises `InvalidTag` rather than returning corrupt plaintext.

### Read-path dispatch (rolling-migration safety)

`apps/core/encryption.py::decrypt_str` recognizes three storage shapes:

1. `v1:` prefix → AES-256-GCM, tries each configured aes256 key.
2. `gAAAAA...` → legacy Fernet ciphertext, decrypted via configured fernet keys.
3. Anything else → legacy plaintext (column not yet through the data
   migration). Returned as-is so a partial rollout doesn't crash.

Every column retains shape (1) after a sweep with
`python manage.py rotate_pii_encryption --all`.

## Key-derivation and randomness

- AES-256 keys: 32 bytes from `os.urandom`, base64-urlsafe-encoded.
- Nonces: 12 bytes from `os.urandom` per encryption call. The 96-bit
  nonce space + random sampling makes nonce reuse (which would catastrophically
  break GCM confidentiality) negligibly unlikely below ~`2^32` writes per key.
  Key rotation cadence (annual recommended) keeps the per-key write count
  far below this threshold.
- PRNG: CPython's `os.urandom` reads from the kernel CSPRNG (`getrandom(2)`
  on Linux). No application-level seeding.

## Forward compatibility

The `v1:` version prefix lets future algorithms or key-custody schemes
coexist with v1 ciphertext during their rollout. Anticipated successors:

| Version | Likely use | Status |
|---------|-----------|--------|
| v2 | KMS-wrapped Data Encryption Keys (Phase 5) | Designed; not implemented |
| v3 | Postquantum hybrid (e.g. AES-256-GCM + ML-KEM) | Speculative |

A new version is implemented as an additional branch in `decrypt_str`
plus an updated `encrypt_str` that emits the new prefix; legacy rows
are migrated by re-running `rotate_pii_encryption --all`.

## Threats addressed and not addressed

| Scenario | v1 protects? | Notes |
|----------|--------------|-------|
| Stolen DB backup tarball | ✅ | Tarball contains only ciphertext + nonces |
| SQL-injection bug returning rows | ✅ | Ciphertext only |
| Read-only analytics credential leak | ✅ | Ciphertext only |
| Logical replication to lower env | ✅ | Lower env without keys cannot decrypt |
| Compromised app server (RCE) | ❌ | Attacker holds the keys (in process memory). Phase 5 KMS partially mitigates by moving key custody to KMS HSM with auditable decrypt events. |
| Stolen `.env` file | ❌ | Same as above. |
| MitM on TLS | ❌ | Out of scope for this layer; transport TLS does that. |

## File map

| Concern | Path |
|---------|------|
| Algorithm + envelope | [apps/core/encryption.py](../../apps/core/encryption.py) |
| Field type | `EncryptedTextField` in same file |
| Registry | [apps/core/encryption_registry.py](../../apps/core/encryption_registry.py) |
| Re-encryption sweep | [apps/core/management/commands/rotate_pii_encryption.py](../../apps/core/management/commands/rotate_pii_encryption.py) |
| Tests | [apps/core/tests/test_encryption.py](../../apps/core/tests/test_encryption.py), [apps/core/tests/test_rotate_pii_encryption.py](../../apps/core/tests/test_rotate_pii_encryption.py) |
| Per-column data migrations | `apps/<app>/migrations/00XX_*` per encrypted field |
| Rollout doc | [encryption-rollout.md](encryption-rollout.md) |
| Key custody runbook | [key-management.md](key-management.md) |
