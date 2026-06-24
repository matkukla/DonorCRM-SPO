# Backup Restore Test Log

Canonical, dated record of every backup restore drill. The step-by-step
procedure lives in [restore-test-checklist.md](restore-test-checklist.md);
the backup design lives in [backup-runbook.md](backup-runbook.md). This file
is the **evidence** — the proof that a backup is recoverable, not just
configured.

> Principle: a backup that has never been restored is not a backup, it's a wish.

---

## ✅ Pilot-readiness status: RESTORE VERIFIED (2026-06-24)

**A backup restore was performed and verified on 2026-06-24** (Drill #1 below).
A Render snapshot of production `donorcrm-db` was restored to a new instance and
its row counts, total gift amount (to the cent), and latest gift date matched
production **exactly** — proving the backup is recoverable with full data
integrity, well within the 4-hour RTO target.

Scope note: this drill verified **data restoration** (counts + integrity).
End-to-end application-against-restored-DB with live PII decryption was not run
this round (the restored instance had no app deployed); the restored data is
ciphertext-intact and decrypts whenever an app with `PII_ENCRYPTION_KEYS` is
pointed at it. Re-run quarterly per
[restore-test-checklist.md](restore-test-checklist.md).

---

## Production baseline (for smoke-test comparison)

Captured from production `donorcrm-db` on **2026-06-24** (read-only aggregate
query — no PII). A restored snapshot reflects the backup's point in time, so
expect these or slightly fewer (whatever existed when the backup was taken):

| Metric | Value |
|--------|-------|
| Contacts | 688 |
| Gifts | 522 |
| Recurring gifts | 301 |
| Users | 43 |
| Journals | 11 |
| Sum of all gift amounts | 31,653,500 cents = **$316,535.00** |
| Latest gift date | 2026-04-30 |

A successful restore should return counts in this neighborhood and a gift-cents
sum that matches the backup point-in-time. (Re-capture the baseline just before
a drill if production has changed materially.)

## Historical results

(append completed drills here in reverse chronological order — quarterly
snapshot, annual off-provider, and annual tabletop, per the checklist)

### Quarterly snapshot test — 2026-06-24   [PASS]

- **Method:** Render dashboard restore of a production `donorcrm-db` snapshot to
  a new instance, `donorcrm-db-copy` (`dpg-d8u211ojs32c73ca8mhg-a`). Production
  was never touched.
- **Restore wall time:** a few minutes for a ~1 GB database — well under the
  4-hour RTO target. (Render-managed restore; the new instance reached
  `available` shortly after kickoff.)
- **Data-integrity smoke test (vs. same-day production baseline):**

  | Metric | Production | Restored copy | Match |
  |--------|-----------|---------------|-------|
  | Contacts | 688 | 688 | ✅ |
  | Gifts | 522 | 522 | ✅ |
  | Recurring gifts | 301 | 301 | ✅ |
  | Users | 43 | 43 | ✅ |
  | Journals | 11 | 11 | ✅ |
  | Σ gift amount | 31,653,500¢ | 31,653,500¢ ($316,535.00) | ✅ |
  | Latest gift date | 2026-04-30 | 2026-04-30 | ✅ |

- **Result:** PASS — exact match on counts, total amount to the cent, and latest
  gift date. The backup restored with full data integrity.
- **Not covered this round:** app-level login + live PII decryption against the
  restored DB (no app was deployed against the copy). Restored data is
  ciphertext-intact; decryption is an app-config concern, not a backup concern.
- **Cleanup:** temporary single-IP allow-list rule and the `donorcrm-db-copy`
  instance removed after verification.
- **Run by:** Matthew Kukla.
