---
phase: quick-17
plan: 17
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/public/spo_favicon.png
  - frontend/index.html
autonomous: true
requirements: [QUICK-17]

must_haves:
  truths:
    - "Browser tab shows the SPO favicon instead of the default Vite logo"
  artifacts:
    - path: "frontend/public/spo_favicon.png"
      provides: "Favicon image served by Vite dev server and production build"
    - path: "frontend/index.html"
      provides: "HTML referencing spo_favicon.png as the page icon"
  key_links:
    - from: "frontend/index.html"
      to: "frontend/public/spo_favicon.png"
      via: "<link rel=\"icon\"> href"
      pattern: "spo_favicon\\.png"
---

<objective>
Replace the default Vite SVG favicon with the SPO favicon image so the browser tab shows the correct branding.

Purpose: Correct branding — the app should display the SPO icon in the browser tab, not the Vite logo.
Output: `frontend/public/spo_favicon.png` present, `index.html` icon link updated.
</objective>

<execution_context>
@/home/matkukla/.claude/get-shit-done/workflows/execute-plan.md
@/home/matkukla/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Copy spo_favicon.png into frontend/public and update index.html</name>
  <files>frontend/public/spo_favicon.png, frontend/index.html</files>
  <action>
    1. Copy the file at the repo root `spo_favicon.png` to `frontend/public/spo_favicon.png`.
       Use: `cp spo_favicon.png frontend/public/spo_favicon.png`

    2. In `frontend/index.html`, replace the existing favicon link:
       FROM: `<link rel="icon" type="image/svg+xml" href="/vite.svg" />`
       TO:   `<link rel="icon" type="image/png" href="/spo_favicon.png" />`

    Do not remove the vite.svg file — just stop referencing it in index.html.
  </action>
  <verify>
    <automated>grep 'spo_favicon.png' /home/matkukla/projects/DonorCRM/frontend/index.html && test -f /home/matkukla/projects/DonorCRM/frontend/public/spo_favicon.png && echo "PASS"</automated>
  </verify>
  <done>frontend/public/spo_favicon.png exists and index.html link rel="icon" points to /spo_favicon.png with type="image/png".</done>
</task>

</tasks>

<verification>
- `grep 'spo_favicon.png' frontend/index.html` returns the link tag
- `test -f frontend/public/spo_favicon.png` succeeds
- Browser tab shows SPO icon when visiting the app
</verification>

<success_criteria>
The Vite SVG favicon is no longer referenced in index.html. The SPO PNG is served from /spo_favicon.png and the browser tab displays it.
</success_criteria>

<output>
After completion, create `.planning/quick/17-make-spo-favicon-png-the-favicon-for-the/17-SUMMARY.md`
</output>
