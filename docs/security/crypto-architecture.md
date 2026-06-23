# DonorCRM Cryptographic Architecture

**Status:** AES-256-GCM shipped 2026-05-07; **v2 per-field AAD binding** is the
current write format. Live transit posture re-verified 2026-06-22.
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
| Application — field level (this doc) | AES-256-GCM v2 envelope (per-field AAD) | AES-256-GCM | App env var (Phase 5: KMS) |
| Application → Postgres (in-transit) | TLS | TLS 1.2+, TLS 1.3 ideal | Render TLS cert |
| Browser → app (in-transit) | TLS | TLS 1.3 (TLS_AES_256_GCM_SHA384) | Render edge cert |
| Off-provider backups | GPG symmetric | AES-256 (`--cipher-algo AES256`) | Operator passphrase |

## Field-level encryption — v2 envelope (AAD-bound)

Storage format (UTF-8 string, stored in a Postgres `TEXT` column):

```
v2:<base64url-unpadded(nonce || ciphertext || tag)>   # current write format, AAD-bound
v1:<base64url-unpadded(nonce || ciphertext || tag)>   # legacy read path, no AAD
```

| Component | Bytes | Notes |
|-----------|-------|-------|
| Version prefix | 3 (text) | `v2:` (current) / `v1:` (legacy) — outside the base64 payload so detection is unambiguous |
| Nonce | 12 | NIST SP 800-38D recommended length; from `os.urandom` per write |
| Ciphertext | varlen | Equal to plaintext length (GCM is a stream cipher) |
| Auth tag | 16 | Appended to ciphertext by the `cryptography` library |

### Why v2 — associated data (AAD)

`EncryptedTextField` writes `v2:` on every save, binding the ciphertext to its
column with AES-GCM associated data `b"<app_label>.<ModelName>.<attname>"`. A
ciphertext blob copied between columns, rows, or models fails authentication
(`InvalidTag`) on read, so a database-level relocation attack cannot silently
move a value into a less-protected context. `v1:` (no AAD) remains decryptable
for rows written before the AAD change; a `rotate_pii_encryption --all` sweep
upgrades them to `v2:`.

### Why GCM (and why not Fernet)

- Fernet is AES-128-CBC + HMAC-SHA256 — fine for confidentiality but uses
  a 128-bit key; auditors and customer security questionnaires often ask
  for "AES-256."
- GCM is the AEAD mode used in TLS 1.3 cipher suites (`TLS_AES_256_GCM_*`),
  HTTPS-grade familiarity for reviewers.
- Authenticated encryption (the GCM tag) detects tampering; a flipped byte
  raises `InvalidTag` rather than returning corrupt plaintext.

### Read-path dispatch (rolling-migration safety)

`apps/core/encryption.py::decrypt_str` recognizes four storage shapes:

1. `v2:` prefix → AES-256-GCM with per-field AAD; the AAD must match or
   authentication fails. Current write format.
2. `v1:` prefix → AES-256-GCM, no AAD (AAD ignored on this path). Legacy rows
   written before AAD binding.
3. `gAAAAA...` → legacy Fernet ciphertext, decrypted via configured fernet keys.
4. Anything else → legacy plaintext (column not yet through the data
   migration). Returned as-is so a partial rollout doesn't crash.

Every column converges to shape (1) after a sweep with
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

The versioned prefix (`v1:` / `v2:`) lets algorithms or key-custody schemes
coexist during rollout. History and anticipated successors:

| Version | Use | Status |
|---------|-----------|--------|
| v1 | AES-256-GCM, no AAD | Legacy read path (superseded by v2) |
| v2 | AES-256-GCM with per-field AAD binding | ✅ Shipped — current write format |
| v3 | KMS-wrapped Data Encryption Keys (Phase 5) | Designed; not implemented |
| v4 | Postquantum hybrid (e.g. AES-256-GCM + ML-KEM) | Speculative |

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
| Ciphertext copied between columns/rows | ✅ (v2) | Per-field AAD binds the blob to its model + column; a relocated value fails GCM authentication |
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
