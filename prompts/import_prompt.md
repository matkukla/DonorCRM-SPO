PLAN MODE: Modify the SPO data import + reconciliation workflow in DonorCRM using Solicitors CSV, Gifts/Donations data, Prayer Intentions data, and SmartSheets data. The goal is to create 25 missionary accounts, correctly attribute donations to them, handle anonymous donors safely, ensure prayer intentions go to the right place, and reconcile all missionary names against any that exist in the system

CONTEXT
- App: DonorCRM (Vite React frontend, Django backend).
- We already expect 25 missionaries/solicitors in the system.
- Source data includes:
  1) Solicitors CSV
  2) Gifts/Donations data
  3) Prayer intentions data (possibly embedded in gifts or related files)
  4) SmartSheets data
- The critical requirement is accuracy: names must match correctly, donations cannot be missed, and prayer intentions must go to the correct missionary/contact context.

GOALS
1) Create or verify 25 missionary accounts from the Solicitors CSV.
2) Reconcile missionary names across:
   - existing missionary accounts in our DB
   - Solicitors CSV
   - SmartSheets data
3) Import gifts/donations and correctly assign them to the right missionary.
4) Detect and account for anonymous donors.
5) Ensure prayer intentions are routed to the correct place.
6) Produce an import/audit summary so we can verify nothing was missed.

NON-GOALS
- Do not build speculative matching logic that silently guesses ambiguous names.
- Do not auto-assign uncertain donations to the wrong missionary.
- Do not redesign the whole data model unless needed.

PHASE 1: INSPECT CURRENT DATA MODEL + FILES
- Inspect the current Django models for:
  - Missionary / User / Staff
  - Contact / Donor / Constituent
  - Donation / Gift / Transaction
  - Commitment / Pledge if relevant
  - Prayer intention / notes fields if any
- Inspect sample headers/rows for:
  - Solicitors CSV
  - Gifts/Donations file(s)
  - SmartSheets file(s)
  - Any prayer intention-related columns
- Summarize how each source currently maps to our DB.

PHASE 2: MISSIONARY ACCOUNT CREATION + NAME RECONCILIATION
Implement a reconciliation pipeline for missionaries/solicitors:
- Use Solicitors CSV to identify the target 25 missionaries.
- Compare against missionaries already in the system.
- Compare against SmartSheets names.
- Build a normalized name matching process:
  1) exact match
  2) normalized match (trim spaces, lowercase, punctuation-insensitive)
  3) alias/fallback table if needed
  4) unresolved/ambiguous names go to a manual review queue
- Do NOT auto-merge ambiguous matches.

Deliverables for this phase:
- Ensure 25 missionary accounts exist in the DB.
- Create a mapping table or reconciliation artifact showing:
  - source name
  - matched missionary account
  - match type (exact / normalized / manual)
  - unresolved items

PHASE 3: DONATION ATTRIBUTION
Implement donation import/assignment logic:
- Import all donations/gifts.
- Link each donation to:
  - donor/contact if possible
  - missionary/solicitor
- Validate that every donation is accounted for:
  - imported successfully
  - or explicitly flagged as unmatched
- Do not silently drop rows.

Anonymous donor handling:
- If a donation is marked anonymous, preserve that status.
- Design a consistent rule:
  - either use a shared “Anonymous Donor” contact
  - or allow donor/contact to be blank while keeping the donation + missionary assignment intact
- Make this rule explicit in code and summary output.

PHASE 4: PRAYER INTENTIONS
- Identify where prayer intentions live in the input data.
- Map them to the correct domain object:
  - preferably the correct contact and/or donation and visible in the correct missionary context
- Do not lose prayer intentions during import.
- If the existing model is unclear, propose the minimal clean model extension needed.

PHASE 5: VALIDATION + AUDIT OUTPUT
After import/reconciliation, generate an audit summary with:
- total missionaries expected
- missionaries created
- missionaries matched
- unresolved missionary names
- total donations processed
- donations imported successfully
- donations unmatched
- anonymous donations count
- prayer intentions imported
- donations per missionary
- missionaries with zero donations
- any rows skipped and why

IMPORTANT RULES
- Accuracy is more important than cleverness.
- If a missionary name match is uncertain, put it in a review queue instead of auto-matching.
- If a donation cannot be confidently assigned, mark it unmatched and report it.
- Preserve external IDs from source files for idempotent re-runs.
- Make the workflow safe to rerun without creating duplicates.

IMPLEMENTATION PREFERENCE
- Keep logic modular:
  - missionary reconciliation service
  - donation import/assignment service
  - prayer intention mapping service
  - import audit/report service
- Reuse existing models when possible.
- Add only minimal new models/tables if required (e.g. import run log, unresolved mapping queue, alias table).

DELIVERABLES
1) A technical implementation plan based on the actual repo/models/files.
2) A proposed mapping/reconciliation strategy for missionary names.
3) Backend implementation for import + reconciliation + audit reporting.
4) Minimal admin/internal UI or management command(s) to run and review the process.
5) A final summary of assumptions, edge cases, and any manual review items.

ACCEPTANCE CRITERIA
- There are exactly 25 valid missionary accounts matched to the imported solicitor data.
- Donations are assigned to the correct missionaries with unmatched cases explicitly reported.
- Anonymous donations are preserved and handled consistently.
- Prayer intentions are attached to the correct destination and not lost.
- The workflow can be rerun safely.
- We get a clear audit summary proving whether any donations were missed.