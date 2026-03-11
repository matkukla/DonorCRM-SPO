---
phase: quick-16
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/assets/spo_logo.png
  - frontend/src/components/layout/Sidebar.tsx
autonomous: true
requirements: []
must_haves:
  truths:
    - "The sidebar header shows the SPO logo image instead of 'DonorCRM' text"
    - "The logo is visible in both light and dark mode (white background on dark if needed)"
  artifacts:
    - path: "frontend/src/assets/spo_logo.png"
      provides: "SPO logo image asset"
    - path: "frontend/src/components/layout/Sidebar.tsx"
      provides: "Sidebar with logo replacing text"
  key_links:
    - from: "frontend/src/components/layout/Sidebar.tsx"
      to: "frontend/src/assets/spo_logo.png"
      via: "import spoLogo from '@/assets/spo_logo.png'"
      pattern: "import.*spo_logo"
---

<objective>
Replace the "DonorCRM" text in the top-left sidebar header with the SPO logo image.

Purpose: Brand the application with the SPO logo rather than generic "DonorCRM" text.
Output: Sidebar.tsx updated to display spo_logo.png in the header area; logo file copied to frontend assets.
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
  <name>Task 1: Copy SPO logo to frontend assets and update Sidebar</name>
  <files>frontend/src/assets/spo_logo.png, frontend/src/components/layout/Sidebar.tsx</files>
  <action>
    1. Copy the existing logo file into frontend assets:
       `cp /home/matkukla/projects/DonorCRM/spo_logo.png /home/matkukla/projects/DonorCRM/frontend/src/assets/spo_logo.png`

    2. In `frontend/src/components/layout/Sidebar.tsx`:
       - Add import at the top (after existing imports):
         `import spoLogo from "@/assets/spo_logo.png"`
       - Replace the logo `<div>` block (lines 109-111) which currently renders:
         ```tsx
         <div className="h-16 flex items-center px-6 border-b border-border">
           <span className="text-xl font-semibold text-primary">DonorCRM</span>
         </div>
         ```
         With:
         ```tsx
         <div className="h-16 flex items-center px-4 border-b border-border">
           <img src={spoLogo} alt="SPO" className="h-8 w-auto object-contain" />
         </div>
         ```
       The logo has a white background (PNG with white fill), so no dark mode adjustment is needed — it will render as-is on the sidebar background. Use `h-8` (32px height) to keep it proportional in the 64px header. `w-auto` preserves aspect ratio. `object-contain` prevents distortion.
  </action>
  <verify>
    <automated>cd /home/matkukla/projects/DonorCRM/frontend && npx tsc --noEmit 2>&1 | head -20</automated>
  </verify>
  <done>
    - `frontend/src/assets/spo_logo.png` exists
    - Sidebar.tsx imports `spoLogo` and renders `&lt;img src={spoLogo} alt="SPO" /&gt;` in the header div
    - No TypeScript errors
    - "DonorCRM" text span is removed from the sidebar header
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>SPO logo replacing the "DonorCRM" text in the top-left sidebar header. Logo is 32px tall, auto-width, centered vertically in the 64px header bar.</what-built>
  <how-to-verify>
    1. Run the dev server: `cd frontend && npm run dev`
    2. Open http://localhost:5173 in browser
    3. Confirm: top-left of sidebar shows the SPO mountain/logo image instead of "DonorCRM" text
    4. Confirm: logo is not stretched or distorted
    5. Toggle dark mode (if applicable) and confirm logo is still visible
  </how-to-verify>
  <resume-signal>Type "approved" or describe any issues (e.g., logo too large, wrong position, not visible)</resume-signal>
</task>

</tasks>

<verification>
- `frontend/src/assets/spo_logo.png` exists (file copy succeeded)
- `frontend/src/components/layout/Sidebar.tsx` contains `import spoLogo` and `<img src={spoLogo}`
- No "DonorCRM" text span remains in the sidebar header div
- TypeScript compiles without errors
</verification>

<success_criteria>
The SPO logo image is displayed in the top-left sidebar header, replacing the "DonorCRM" text, and renders correctly at an appropriate size without distortion.
</success_criteria>

<output>
After completion, create `.planning/quick/16-add-spo-logo-to-the-top-left-of-the-appl/16-SUMMARY.md`
</output>
