# Phase 24 Context: Smartsheet MPD Report Import Backend

> **REVISED 2026-02-19** — Original context assumed generic donor/donation/pledge import.
> After reviewing the actual sample Smartsheet file, the feature is completely different:
> admin uploads a monthly MPD financial report where each row is a missionary, not a donor.

## What This Feature Actually Is

An admin uploads their organization's monthly **Smartsheet MPD Dashboard Report** (CSV or XLSX export). Each row represents a **missionary** (a DonorCRM User), not a donor/contact. The system:

1. Parses the file (auto-detect CSV vs XLSX)
2. Matches each row to an existing DonorCRM user by **First Name + Last Name**
3. Creates a monthly **MPD snapshot** per matched user, storing ~20 financial summary columns
4. Accumulates snapshots over time (historical, not replace-on-upload)
5. Surfaces MPD data on the **admin dashboard** AND **individual missionary views**

## Sample File Reference

See: `test_data/Sample Smartsheet MPD Dashboard Report.xlsx - MPD Dashboard 2025-2026.csv`

Columns in the actual Smartsheet export:
- `Full Name`, `First Name`, `Last Name` — missionary identity (matching keys)
- `Active Recurring Gifts` — currency
- `Annual Gifts` — currency
- `Monthly Average` — currency
- `Annual MPD Estimate` — currency
- `MPD Standard` — currency
- `$ Amount Below MPD Standard` — currency (can be negative)
- `% Standard to Max` — percentage string (e.g., "104%")
- `Met MPD Standard` — Yes/No
- `MPD Maximum` — currency
- `Met MAXIMUM` — Yes/No
- `Amount Above/Below Maximum` — currency (can be negative)
- `Match Met` — Yes/No
- `Match Met for Rest of Fiscal Year (Based on RFB)` — Yes/No
- `Latest Roll Forward Balance` — currency
- `Current MPD Cap` — currency
- `Months Remaining in RF` — decimal (can be "infinite")
- `Proj. Monthly Deduction from RFB (Cap - Rec.Gifts)` — currency
- `PAY FORECAST Over 12 Months` — currency
- `Pay Forecast Over Fiscal Year` — currency
- `Total One-Time Gifts - April` — currency (often empty)

**Columns to SKIP (coaching — not stored):**
- `Will be a Coach in 2022 MPD Season?`
- `Do you understand the Coaching Contract?`
- `Have you made these decisions w/ your supervisor?`

## Data Model

### MPDSnapshot Model
- Linked to User (ForeignKey) — one snapshot per user per upload
- Linked to an MPDUpload record (ForeignKey) — groups all snapshots from one file
- All financial fields stored as Decimal (parsed from currency strings like "$3,085.00")
- Boolean fields for Yes/No columns
- `months_remaining_rf` as CharField (can be "infinite")
- `report_month` or `upload_date` for time-series queries

### MPDUpload Model (audit trail)
- Tracks each file upload: timestamp, admin who uploaded, filename
- Row counts: total rows, matched, unmatched
- Status: processing, completed, failed

### Accumulate Snapshots (Historical)
- Each monthly upload creates NEW snapshot records (does not overwrite)
- Enables trend analysis (e.g., "MPD Cap over time", "Recurring Gifts trend")
- Old snapshots are preserved indefinitely

## Missionary Matching

### Match by First Name + Last Name
- Match `First Name` + `Last Name` columns against `User.first_name` + `User.last_name`
- Case-insensitive matching
- **Claude decides** how to handle unmatched rows (skip and report, or let admin map manually)

## Column Detection

### Claude decides
- Whether column names should be hardcoded (this is a specific report format) or semi-flexible (auto-detect by known names, allow remap if format changes)
- Research should look at how stable Smartsheet export column names are

## Import Workflow

### Single-Step Upload
- Admin uploads file → backend parses, matches users, creates snapshots → returns results
- No column mapping step needed (columns are known/fixed from the Smartsheet report)
- Simpler than the original two-step plan since columns are predictable

### File Format Detection
- Auto-detect CSV vs XLSX from magic bytes (same as original plan)
- Support both formats from Smartsheet export

### File Size
- Realistic: ~10-50 rows (one per missionary in the org)
- Max file size: 10 MB is plenty (no need for 25 MB)
- Synchronous processing

## UI Integration (Phase 25 scope, but informs backend API)

### Admin Dashboard
- Show MPD data on admin analytics dashboard (overview + user detail pages)
- Latest snapshot values per missionary

### Missionary View
- Each missionary sees their own MPD data in their view
- Historical trend if snapshots accumulate

## Security

### Formula Injection Prevention
- Strip formula injection characters from cell values on parse (same as before)

## What This Is NOT

- NOT a generic donor/contact/donation/pledge import
- NOT a column mapping wizard (columns are from a known report format)
- NOT creating Contact, Donation, or Pledge records
- The existing SPO CSV import (funds, entities, transactions, pledges) remains unchanged

## Deferred Ideas
_(None captured during discussion)_
