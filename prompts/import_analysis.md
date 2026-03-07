PLAN MODE: Analyze my current DonorCRM data model, import structure, and routing of fundraising data against the CSV formats I will be uploading into the app. The uploaded files are:

- test_constituents.csv
- test_solicitors.csv
- test_gifts.csv
- test_recurring_gifts.csv

GOAL
Determine whether my current backend models, relationships, and import assumptions correctly support these CSV formats. If there are discrepancies, propose the optimal structure and migration path so these files can map cleanly and accurately into the application.

WHAT TO DO

1) Inspect the uploaded CSV files
- Read the headers and sample rows from all 4 CSVs.
- Infer the structure and relationships between:
  - Constituents
  - Solicitors
  - Gifts
  - Recurring Gifts
- Identify key IDs and foreign-key style references in the files.
- Determine whether Gifts contain split/allocation behavior or other DonorElf-style quirks.

2) Inspect my current Django/backend structure
- Find the models currently representing:
  - contacts / donors / constituents
  - missionaries / solicitors / users
  - gifts / donations / transactions
  - recurring gifts / pledges / commitments
  - funds / accounts if present
  - prayer intentions if present
- Inspect import-related services, serializers, views, commands, or admin tools if they already exist.
- Summarize the current structure in plain English.

3) Compare current structure vs CSV reality
For each CSV file:
- Explain what it appears to represent
- Show how it should map into my current models
- Identify mismatches, missing fields, wrong assumptions, weak relationships, or places where import bugs are likely
- Be explicit about whether the current structure is sufficient or not

4) Propose the optimal structure
If my current structure is not ideal, propose the cleanest structure for this application so these 4 CSVs can import correctly and safely.

Use DonorElf-style concepts, but keep the structure clean and practical for SPO.

At minimum, evaluate whether I should have models like:
- Contact (Constituent)
- Missionary / Solicitor
- Donation / Gift
- Commitment / Recurring Gift
- Fund
- DonationAllocation / GiftSplit (if gifts are split across funds)
- ImportRun / ImportError logging

For each recommended model:
- Explain why it is needed
- Explain what CSV fields map into it
- Explain what external_id field should be used for idempotent imports

5) Recommend the correct import order
Determine the correct order for importing these 4 files based on their dependencies.
Explicitly state:
- which file must be imported first
- which files depend on which other files
- how foreign key relationships should be resolved

6) Recommend the correct import strategy
Explain the best technical import approach:
- upsert keys for each file
- required validations
- handling of missing references
- duplicate prevention
- how to safely rerun imports
- how to handle anonymous donors
- how to handle prayer intentions if present
- how to handle gift rows that may represent fund splits rather than standalone donations

7) Deliverables
Produce:
A) A concise summary of whether my current structure is compatible with these CSVs
B) A discrepancy list:
   - CSV expectation
   - current app structure
   - problem
   - recommended fix
C) A proposed target data model
D) A recommended import order
E) A step-by-step implementation plan
F) A list of specific files in my repo that should be changed to support this cleanly

IMPORTANT CONSTRAINTS
- Do not rewrite everything unless truly necessary.
- Prefer the smallest set of structural changes that will make the CSV imports reliable and correct.
- Prioritize correctness over convenience.
- Do not silently guess ambiguous mappings.
- If the current structure is already good enough in some areas, say so clearly.

OUTPUT FORMAT
Please structure the output as:
1. What the 4 CSV files represent
2. Current application structure
3. Discrepancies found
4. Recommended target structure
5. Recommended import workflow
6. Exact implementation plan

The final goal is to ensure these four CSV formats can map accurately into DonorCRM with minimal ambiguity and minimal future pain.