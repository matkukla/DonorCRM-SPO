PROMPT START
You are a senior full-stack engineer. Implement daily CSV imports for DonorCRM (Node/Express + Prisma + Postgres + Zod).

CRITICAL RULES (READ FIRST)
DO NOT:
❌ Change CSV file names or column headers (these come from Raiser's Edge - we cannot modify them)
❌ Refactor unrelated code
❌ Change existing API contracts
❌ Over-engineer - keep it simple and working
❌ Stop on row errors - process ALL rows, collect errors
DO:
✅ Keep changes minimal and focused
✅ Use existing app patterns (auth, error handling, etc.)
✅ Make imports idempotent (safe to run daily)
✅ Return detailed reports with row-level errors
✅ Test each phase before moving to next
CONTEXT
Workflow: Admin exports 4 CSVs from Raiser's Edge daily (5 days/week) and uploads them one at a time to DonorCRM.

The 4 CSV Types:

Constituent → Creates/updates Contacts (donors)
Solicitor → List of missionary names
Gift → One-time donations
Recurring gifts → Pledges/recurring donations
Key Relationship:

One Gift can credit MULTIPLE missionaries (solicitors)
CSV may have multiple rows with same Gift ID but different Solicitor Name
Must GROUP rows by Gift ID, create one Gift record, multiple GiftCredit records
CSV HEADERS (EXACT - DO NOT CHANGE)
Type 1: Constituent CSV
Constituent Date Last Changed
Constituent ID
First Name
Last Name
Organization Name
Address Line 1
Address Line 2
City
State
ZIP
Country
Phone
Email
Type 2: Solicitor CSV
Name
Type 3: Gift CSV
Gift ID
Gift Date Last Changed
Gift Date
Gift Type
Fund ID
Fund Split Amount
Constituent ID
Gift Is Anonymous
Solicitor Name
Solicitor Amount
Gift Payment Type
Gift Specific Attributes Prayer Requests Description
Type 4: Recurring Gifts CSV
Gift ID
Gift Date Last Changed
Gift Date
Gift Type
Gift First Installment Due
Last Installment/Payment Date Due
Gift Installment Frequency
Number of Installments Scheduled
Gift First Installment Due_1
Fund ID
Constituent ID
Gift Is Anonymous
Solicitor Name
Solicitor Amount
Gift Payment Type
Gift Status
Gift Status Date
Gift Specific Attributes Prayer Requests Description
DATA MODEL DESIGN
New Prisma Models Needed
