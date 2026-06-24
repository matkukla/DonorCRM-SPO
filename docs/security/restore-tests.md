# Backup Restore Test Log

Canonical, dated record of every backup restore drill. The step-by-step
procedure lives in [restore-test-checklist.md](restore-test-checklist.md);
the backup design lives in [backup-runbook.md](backup-runbook.md). This file
is the **evidence** — the proof that a backup is recoverable, not just
configured.

> Principle: a backup that has never been restored is not a backup, it's a wish.

---

## ⛔ Pilot-readiness status: NOT YET PERFORMED

**As of this file's creation, no restore drill has ever been run and recorded.**

This is a **pilot blocker** for handing the system real donor data: the daily
Render Postgres snapshots and the off-provider GPG archive are *configured*,
but we have **no evidence** that either can actually be restored to a working
DonorCRM within the 4-hour RTO target. Until the first quarterly snapshot drill
below is completed and signed off, the honest posture in any customer-facing
material is: *"automated backups are in place; restore has not yet been
tested."* Do not claim "restore-tested" before an entry appears under
**Historical results**.

**To clear this blocker:** run the *Quarterly: Render snapshot → staging
restore* procedure in [restore-test-checklist.md](restore-test-checklist.md),
fill in Drill #1 below, and change this status line to ✅.

---

## Drill #1 — Quarterly snapshot restore (PENDING)

Copy the values in as you run it; leave `PENDING` until complete.

```markdown
### Quarterly snapshot test — YYYY-MM-DD   [PENDING]

- Snapshot timestamp restored: YYYY-MM-DD HH:MM UTC
- Restore start → end:         HH:MM → HH:MM
- Restore wall time:           HH:MM   (target: ≤ 4h)
- Staging redeploy green at:   HH:MM
- Smoke tests pass:            ⬜ login+JWT  ⬜ contacts ≥1  ⬜ gifts ≥1
                               ⬜ known contact name  ⬜ known gift amount
                               ⬜ encrypted PII reads correctly  ⬜ Sentry event
- Total RTO measured:          HH:MM
- Issues found:                <list, or "none">
- Action items:                <list, or "none">
- Run by:                      <name>
```

---

## Historical results

(append completed drills here in reverse chronological order — quarterly
snapshot, annual off-provider, and annual tabletop, per the checklist)

_No drills recorded yet._
