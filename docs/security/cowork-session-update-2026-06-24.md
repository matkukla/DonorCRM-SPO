# Security Session Update — 2026-06-24 (context for Cowork)

> **Purpose.** This is a source/context document for Claude Cowork to use when
> updating the customer-facing SPO security document. It summarizes everything
> changed in the 2026-06-24 pilot-readiness security session: what was fixed,
> what claims must be corrected, the final risk posture, and the evidence.
>
> **How to use it:** apply the "Claims to change in the SPO security doc"
> section as deltas, reflect the new verdict and risk register, and keep the
> tone guardrails at the bottom. Pull detail from the linked source docs.
>
> **Companion source docs (authoritative):**
> - [pilot-security-brief.md](pilot-security-brief.md) — encryption & transport
> - [pilot-readiness-addendum.md](pilot-readiness-addendum.md) — authorization, lifecycle, IR, backup, risk register, go/no-go
> - [evidence-map.md](evidence-map.md) — control-to-framework mapping
> - [restore-tests.md](restore-tests.md) — backup restore evidence

---

## 1. Headline for the SPO doc

An internal, authorization-focused security review was completed on
**2026-06-24**. The donor data-isolation architecture was found **sound and is
now backed by automated tests**. One real defect (a coach could see one
financial figure) was found and fixed. The backup is now **restore-tested**,
the database is **locked to internal-only**, and several customer-facing claims
were **corrected for accuracy**.

**Verdict: GO-WITH-CAVEATS for a limited internal SPO pilot with real donor
data.** No unresolved blockers. Remaining items are disclosed, accepted
residual risks.

---

## 2. Claims to CHANGE in the existing SPO security doc

These are accuracy corrections — the prior doc overstated or under-stated them.

| Topic | OLD (incorrect/outdated) | NEW (accurate) |
|-------|--------------------------|----------------|
| **Password hashing** | "Argon2 password hashing" | **PBKDF2-SHA256** (Django's default; salted, high iteration count). Argon2 is **not** installed/configured. Do **not** say Argon2. |
| **Backup restore** | "configured" / "quarterly restore tests" (implying done) | **Restore drill performed and verified 2026-06-24** — a production snapshot was restored to a fresh instance and row counts, total gift amount (to the cent), and latest gift date matched production exactly. Re-run quarterly. |
| **Coach financial restriction** | "enforced server-side" (was true except one endpoint) | Now true **without exception** — a missed field (a journal's fundraising goal) was gated and regression-tested. |
| **Database network exposure** | (not stated) | Database accepts **no public connections** — locked to Render's internal network only (the prior `0.0.0.0/0` allow-list was removed). |
| **Retention purge** | "nightly cron" | Run **manually, quarterly** (the cron is intentionally not scheduled while pre-revenue). |

---

## 3. What was fixed / added this session

**Security fixes**
- **Coach financial-data leak closed.** A coach could read a journal's
  `goal_amount` (a fundraising target) via the contact "Journals" endpoint.
  Now gated server-side and covered by a regression test.
- **Token revocation on deactivation.** Deactivating a user now revokes their
  refresh tokens (previously only the password-change paths did).
- **Database locked to internal-only** (removed public IP exposure).
- **Import money parser hardened** — rounds half-up instead of truncating, and
  rejects negative amounts cleanly (prevents silent sub-cent loss / crashes on
  malformed import cells). Real 2-decimal exports are unaffected.

**New privacy/lifecycle capabilities (support customer "how do you…" questions)**
- **Donor delete-on-request (DSAR / right-to-erasure):** an admin can
  permanently delete a donor and all related records (gifts, pledges, journals,
  tasks, prayers); the deletion is audit-logged.
- **Departed-user offboarding:** an admin can bulk-reassign a departed
  missionary's contacts to a new active owner.

**Evidence (authorization proof)**
- Added automated negative tests proving: cross-user object access is blocked
  (returns "not found"), URL/search/query parameters can't widen scope, coaches
  receive no financial fields, "View As" reads are audit-logged, and View-As
  cannot mutate. Full backend suite: **1,497 tests passing, 0 failing.**

**Operational / documentation**
- **Incident-response plan completed** — real responder named; outside privacy
  counsel and cyber-insurance accurately marked "not yet retained"; donor and
  Attorney-General notification letter templates added.
- **Two minor performance fixes** (N+1 queries on two list endpoints).

---

## 4. Final risk register (disclose, don't bury)

| # | Risk | Status |
|---|------|--------|
| R1 | Backup recoverability | ✅ **Closed** — restore drill passed 2026-06-24 (exact data match) |
| R2 | Audit log erasable with DB credentials (app-layer append-only only) | ⏸️ **Deferred** — accepted residual for the internal pilot; DB-privilege lockdown script + runbook staged for before external prospects |
| R3 | Access token valid ≤15 min after logout (stateless JWT) | ✅ **Accepted** — tokens are in browser storage so XSS (mitigated by a strict CSP), not the window, is the dominant risk; refresh tokens are revoked on logout/deactivation |
| R4 | Donor delete-on-request | ✅ **Closed** — admin erase capability shipped |
| R5 | Privacy counsel / cyber-insurance not retained | 📋 **Business decision** — accepted residual; engage before scaling beyond the pilot |
| R6 | Very large CSV import could approach the request timeout | ⏸️ **Deferred** — accepted residual; row caps (25k) + 10-min timeout adequate for pilot volumes |
| R7 | Departed-user contacts stranded | ✅ **Closed** — admin bulk-reassignment shipped |
| R8 | Database publicly reachable | ✅ **Closed** — locked to internal-only |

No unresolved Critical or Blocker items.

---

## 5. What is verified vs. accepted vs. unverified

- **Verified in code/tests:** owner-scoped data isolation; object-level access
  (no cross-user reads); View-As is read-only and audit-logged; coach financial
  gating; JWT lifecycle (rotation, blacklist on logout/deactivation/password
  change); brute-force lockout; field-level donor-PII encryption present; CI
  dependency-CVE + static-analysis scans.
- **Verified live:** backup restore (2026-06-24); database internal-only.
- **Accepted residual (disclosed):** R2, R3, R5, R6 above.
- **Re-verify at pilot start / periodically:** live TLS posture (last probed
  2026-06-22); quarterly restore drill; quarterly retention purge.

---

## 6. Tone guardrails for the SPO document (keep these)

- **Scope:** US-based donors only. No card data (no PCI), health (no HIPAA), or
  EU (no GDPR). State breach-notification laws apply.
- **Do not claim SOC 2 compliance.** Say "SOC 2-aligned controls" only where
  accurate.
- **Do not overclaim.** Don't say "restore-tested" beyond the single recorded
  drill; don't say "Argon2"; don't imply the audit log is tamper-*proof* (it is
  tamper-*resistant* / append-only at the application layer until R2 ships).
- **Disclose residual risks** (Section 4) in plain English; do not bury them.
- Professional, sober, non-hype.
