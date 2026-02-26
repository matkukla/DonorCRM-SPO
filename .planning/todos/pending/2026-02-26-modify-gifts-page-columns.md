---
created: 2026-02-26T14:05:00.000Z
title: Modify gifts page columns
area: ui
files:
  - frontend/src/pages/gifts/GiftList.tsx
  - apps/gifts/models.py
  - apps/gifts/serializers.py
---

## Problem

The Gifts (Donations) list page needs column changes:

1. **Remove** "Funds" column
2. **Remove** "Description" column
3. **Add** "Type" column with options: Credit Card, Direct Deposit, Check

The "Type" field likely needs a new `gift_type` or `payment_type` field on the Gift model (CharField with choices), backend serializer update, and frontend column definition + filter support.

## Solution

- Add `payment_type` CharField with choices (`credit_card`, `direct_deposit`, `check`) to Gift model + migration
- Update GiftSerializer to include the new field
- In GiftList.tsx: remove Funds and Description column definitions, add Type column with display labels
- Add Type to filter options if desired
