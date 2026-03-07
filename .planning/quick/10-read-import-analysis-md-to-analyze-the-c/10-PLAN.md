---
phase: quick-10
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/quick/10-read-import-analysis-md-to-analyze-the-c/10-ANALYSIS.md
autonomous: true
requirements: []
must_haves:
  truths:
    - "Analysis document exists at the output path"
    - "All 6 sections from import_analysis.md prompt are addressed"
    - "Each CSV file is explicitly characterized (structure, fields, relationships)"
    - "Every gap or discrepancy between CSV reality and current implementation is named"
    - "Phase 44 coverage verdict is explicit (covered / partially covered / not covered)"
  artifacts:
    - path: ".planning/quick/10-read-import-analysis-md-to-analyze-the-c/10-ANALYSIS.md"
      provides: "Structured analysis report"
      min_lines: 150
  key_links:
    - from: "CSV files (test_data/*.csv)"
      to: "Django models (apps/gifts/models.py, apps/contacts/models.py)"
      via: "field-by-field mapping in section 3 of analysis"
    - from: "import_analysis.md requirements"
      to: "Phase 44 implementation (spo_services.py, re_services.py)"
      via: "gap/coverage assessment in section 3"
---

<objective>
Produce a structured analysis report at 10-ANALYSIS.md that addresses all requirements from prompts/import_analysis.md.

Purpose: Determine whether Phase 44's SPO import workflow correctly and completely handles all 4 CSV formats. Surface any gaps for potential future work.

Output: .planning/quick/10-read-import-analysis-md-to-analyze-the-c/10-ANALYSIS.md covering all 6 required sections from the analysis prompt.
</objective>

<execution_context>
@/home/matkukla/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/STATE.md
@prompts/import_analysis.md

All 4 CSV files have already been read and their structure is understood. The key files implementing the current import pipeline are:

- apps/imports/spo_services.py — reconcile_missionaries(), import_spo_gifts(), import_spo_prayers()
- apps/imports/re_services.py — import_re_constituents(), import_re_recurring_gifts()
- apps/imports/models.py — ImportBatch, ImportBatchType, Fund, MissionaryAlias
- apps/gifts/models.py — Gift, GiftCredit, RecurringGift, RecurringGiftCredit, Solicitor
- apps/contacts/models.py — Contact (with external_constituent_id field)

Phase 44 implemented: Step 1 (reconcile_missionaries via solicitors CSV), Step 2 (import_spo_gifts via gifts CSV), Step 3 (import_spo_prayers). RE-style imports exist for constituents and recurring gifts via re_services.py.

The analysis must evaluate coverage against the requirements in prompts/import_analysis.md.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write the structured import analysis report</name>
  <files>.planning/quick/10-read-import-analysis-md-to-analyze-the-c/10-ANALYSIS.md</files>
  <action>
Write 10-ANALYSIS.md covering all 6 sections required by import_analysis.md. The analysis must use the information already gathered about the 4 CSV files and the current backend structure. Do NOT add speculative information — draw only from what is confirmed by reading the source files.

Section 1 — What the 4 CSV files represent:
- test_constituents.csv: RE Constituent export. Type-label row "Constituent". Fields: Constituent Date Last Changed, Constituent ID (6-digit, e.g. 100001), First Name, Last Name, Organization Name (for org-type rows), Address Line 1/2, City, State, ZIP, Country, Phone, Email. 100 rows. Constituent ID is the primary FK used by gifts and recurring gifts to link to donors. Mixed individual + organization rows (Organization Name present, First/Last blank).
- test_solicitors.csv: SPO Solicitor export. Type-label row "Solicitor". Single column: Name (e.g. "Peter Anderson"). 25 rows. These are missionary names — not SPO constituent IDs. No numeric IDs. Sole purpose: establish the missionary User population before gift import.
- test_gifts.csv: RE Gift export. Type-label row "Gift". Fields: Gift ID (200xxx), Gift Date Last Changed, Gift Date, Gift Type, Fund ID ("Staff MPD"), Fund Split Amount (dollar string e.g. "$100.00"), Constituent ID (links to constituents), Gift Is Anonymous (Yes/No), Solicitor Name (missionary name string), Solicitor Amount, Gift Payment Type, Gift Specific Attributes Prayer Requests Description, Soft Credit Recipient ID. 100 rows. No split-fund rows observed — all gifts go to a single "Staff MPD" fund. Payment types: EFT, Check, Credit Card, Direct Debit, Cash (note: not all match PaymentType choices).
- test_recurring_gifts.csv: RE Recurring Gift export. Type-label row "Recurring Gift". Fields: Gift ID (300xxx), Gift Date Last Changed, Gift Date, Gift Type, Gift First Installment Due (empty in test data), Last Installment/Payment Date Due (empty), Gift Installment Frequency (Monthly/Quarterly/Annually), Number of Installments Scheduled (empty), Gift First Installment Due_1 (empty), Fund ID, Constituent ID, Gift Is Anonymous, Solicitor Name, Solicitor Amount, Gift Payment Type, Gift Status (Active/Held/Completed), Gift Status Date, Gift Specific Attributes Prayer Requests Description, Soft Credit Recipient ID. 100 rows. Status maps to RecurringGiftStatus. Frequency: Monthly, Quarterly, Annually only in test data.

Section 2 — Current application structure:
Summarize the models (Contact, Solicitor, Gift, GiftCredit, RecurringGift, RecurringGiftCredit, Fund, ImportBatch, MissionaryAlias) and the two import pipelines (RE pipeline: import_re_constituents + import_re_recurring_gifts via re_services.py; SPO pipeline: reconcile_missionaries + import_spo_gifts + import_spo_prayers via spo_services.py). Note what each pipeline covers.

Section 3 — Discrepancies found:
For each discrepancy, use the table format: CSV expectation | current app structure | problem | recommended fix.

Key discrepancies to analyze:
1. Payment type mismatch: CSV has "EFT", "Direct Debit", "Cash" but PaymentType choices are credit_card, direct_deposit, check only. Current spo_services.py does NOT map payment_type at all (Gift is created without payment_type). The RE import (re_services.py) handles payment_type but must be checked for mapping coverage.
2. Fund ID: CSV has "Staff MPD" as Fund ID string. Current import creates Fund records, but gift import does NOT link Fund to Gift (spo_services.py creates Gift without fund= argument). The Gift.fund FK exists but is unused by the SPO pipeline.
3. Soft Credit Recipient ID: present in both gifts and recurring gifts CSVs. Not handled by any import service.
4. Recurring gift import uses re_services.py (RE pipeline), not spo_services.py (SPO pipeline) — they use different services. The recurring_gifts fixture test calls import_re_recurring_gifts() with an owner parameter; spo_services.py has no recurring gift support.
5. Contact scoping: Each Contact is owned by a specific missionary User (owner FK). The constituent import requires an explicit --owner user. In a multi-missionary org, each missionary's contacts must be imported separately with the correct owner. The SPO gifts pipeline uses a different approach (anonymous contact per missionary) — so constituent-based contact lookup (by external_constituent_id) requires constituents already imported with the correct owner.
6. Gift Date Last Changed vs Gift Date: CSV has both columns. Only Gift Date is imported (gift_date). Changed date is not tracked.
7. Prayer requests: handled by import_spo_gifts (inline) and import_spo_prayers (standalone). Coverage is good. Recurring gift prayer requests are NOT extracted (no prayer extraction in import_re_recurring_gifts).
8. Organization constituents: CSV has rows where First Name and Last Name are blank but Organization Name is populated. The Contact model has organization_name field. The RE constituent import presumably handles this — confirm via re_services.py.

Section 4 — Recommended target structure:
State which models are sufficient as-is and which need changes. The core model set (Contact, Gift, GiftCredit, RecurringGift, RecurringGiftCredit, Fund, Solicitor, ImportBatch, MissionaryAlias) is already well-designed. Surface specific field additions or behavioral changes needed.

Section 5 — Recommended import workflow:
State the correct order: constituents → solicitors (missionary reconciliation) → gifts → recurring gifts. Explain why. Note that prayer extraction from recurring gifts is missing.

Section 6 — Exact implementation plan:
List the specific files to change and the minimal changes required. Focus on the gaps identified in Section 3. Do not recommend rewrites. Note which gaps are true bugs vs acceptable limitations in the current design.

Format requirements:
- Use markdown headers (##, ###)
- Use tables for discrepancy list (section 3)
- Be explicit about Phase 44 coverage: for each requirement from import_analysis.md, say whether Phase 44 covers it
- Use plain factual language — no marketing, no hedging phrases like "might", "could", "perhaps" unless genuinely uncertain
- Minimum 200 lines
  </action>
  <verify>
    <automated>test -f /home/matkukla/projects/DonorCRM/.planning/quick/10-read-import-analysis-md-to-analyze-the-c/10-ANALYSIS.md && wc -l /home/matkukla/projects/DonorCRM/.planning/quick/10-read-import-analysis-md-to-analyze-the-c/10-ANALYSIS.md | awk '{print "Line count:", $1}'</automated>
  </verify>
  <done>10-ANALYSIS.md exists with all 6 sections, minimum 150 lines, no placeholder content. All discrepancies are explicitly named with recommended fixes.</done>
</task>

</tasks>

<verification>
File exists and has content. All 6 sections from import_analysis.md prompt are addressed. Discrepancy table is populated. Phase 44 verdict is explicit per requirement area.
</verification>

<success_criteria>
10-ANALYSIS.md written to output path. Covers: what each CSV represents, current model structure, discrepancy list with fixes, recommended target structure, import order, and implementation plan. File is self-contained — no further reading required to understand the conclusions.
</success_criteria>

<output>
No SUMMARY.md required for quick tasks. Deliver the analysis file at:
.planning/quick/10-read-import-analysis-md-to-analyze-the-c/10-ANALYSIS.md
</output>
