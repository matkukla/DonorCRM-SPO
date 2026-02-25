---
created: 2026-02-20T15:29:32.427Z
title: Revamp CSV import system
area: general
files:
  - backend/src/
  - frontend/src/
---

## Problem

The current CSV import system needs a revamp to improve reliability, user experience, and flexibility. This may include better column mapping, validation feedback, error handling, support for more data types, and a more intuitive import workflow for missionaries uploading donor/contact/transaction data.

## Solution

Redesign the CSV import pipeline — improve the column mapping UI, add preview/validation step before committing data, better error reporting with row-level feedback, and potentially support for additional file formats. Consider a step-by-step wizard approach for the import flow.
