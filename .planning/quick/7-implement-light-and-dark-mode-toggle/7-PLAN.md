---
phase: quick
plan: 7
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/styles/globals.css
  - frontend/src/providers/ThemeProvider.tsx
  - frontend/src/components/layout/Header.tsx
  - frontend/src/components/layout/Sidebar.tsx
  - frontend/src/App.tsx
  - frontend/index.html
autonomous: true

must_haves:
  truths:
    - "User can toggle between light and dark mode via a button in the header"
    - "Theme preference persists across page refreshes via localStorage"
    - "Dark mode applies across all pages -- backgrounds, text, cards, borders all adapt"
    - "On first visit, theme defaults to system preference (prefers-color-scheme)"
    - "No flash of wrong theme on page load"
  artifacts:
    - path: "frontend/src/providers/ThemeProvider.tsx"
      provides: "Theme context with toggle function, localStorage persistence, system preference detection"
    - path: "frontend/src/styles/globals.css"
      provides: "Dark mode CSS variables under .dark selector"
    - path: "frontend/src/components/layout/Header.tsx"
      provides: "Theme toggle button"
  key_links:
    - from: "frontend/index.html"
      to: "localStorage theme"
      via: "inline script that sets .dark class on <html> before React hydrates (prevents flash)"
    - from: "frontend/src/providers/ThemeProvider.tsx"
      to: "document.documentElement.classList"
      via: "useEffect that syncs theme state to DOM class"
    - from: "frontend/src/components/layout/Header.tsx"
      to: "ThemeProvider"
      via: "useTheme hook to get current theme and toggle function"
---

<objective>
Add light/dark mode toggle to DonorCRM. The app already uses shadcn/ui with CSS variable-based theming and `darkMode: ["class"]` in tailwind.config.js, so the infrastructure is ready -- we need to define dark CSS variables, create a ThemeProvider, add a toggle button, and fix the few hardcoded `bg-white` usages.

Purpose: Let users choose their preferred color scheme for comfortable use in different lighting conditions.
Output: Working theme toggle in the header, dark mode CSS variables, localStorage persistence, no FOUC.
</objective>

<execution_context>
@/home/matkukla/.claude/get-shit-done/workflows/execute-plan.md
@/home/matkukla/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/tailwind.config.js (already has `darkMode: ["class"]`)
@frontend/src/styles/globals.css (light-only CSS variables, needs .dark block)
@frontend/src/providers/AuthProvider.tsx (existing provider pattern to follow)
@frontend/src/components/layout/Header.tsx (where toggle button goes)
@frontend/src/components/layout/Sidebar.tsx (has hardcoded bg-white to fix)
@frontend/src/App.tsx (needs ThemeProvider wrapping)
@frontend/index.html (needs inline script for FOUC prevention)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create ThemeProvider, dark CSS variables, and FOUC prevention script</name>
  <files>
    frontend/src/providers/ThemeProvider.tsx
    frontend/src/styles/globals.css
    frontend/index.html
    frontend/src/App.tsx
  </files>
  <action>
    1. Create `frontend/src/providers/ThemeProvider.tsx`:
       - Export type `Theme = "light" | "dark" | "system"`
       - Export `ThemeProvider` component and `useTheme` hook
       - ThemeProvider manages state with useState, defaulting to localStorage value or "system"
       - On mount + theme change, resolve "system" to actual light/dark using `window.matchMedia("(prefers-color-scheme: dark)")`, then apply/remove "dark" class on `document.documentElement`
       - Listen for system preference changes (matchMedia change event) when theme is "system"
       - Persist theme choice to localStorage under key "donorcrm-theme"
       - useTheme returns `{ theme, setTheme, resolvedTheme }` where resolvedTheme is always "light" or "dark"
       - Follow the same provider pattern as AuthProvider.tsx (createContext, provider component, hook with null check)

    2. Update `frontend/src/styles/globals.css`:
       - Keep all existing `:root` variables unchanged
       - Add a `.dark` block inside `@layer base` with dark mode values:
         - --background: 222 47% 11%  (dark navy, ~#0f172a)
         - --foreground: 210 40% 98%  (~#f8fafc)
         - --card: 222 47% 14%  (~#1e293b, slightly lighter than bg)
         - --card-foreground: 210 40% 98%
         - --popover: 222 47% 14%
         - --popover-foreground: 210 40% 98%
         - --primary: 348 85% 61%  (keep SPO Red the same)
         - --primary-foreground: 0 0% 100%
         - --secondary: 217 33% 20%
         - --secondary-foreground: 210 40% 98%
         - --muted: 217 33% 18%
         - --muted-foreground: 215 20% 65%
         - --accent: 355 62% 58%  (keep SPO Red)
         - --accent-foreground: 0 0% 100%
         - --destructive: 0 63% 55%
         - --destructive-foreground: 0 0% 100%
         - --border: 217 33% 25%
         - --input: 217 33% 25%
         - --ring: 210 40% 70%
       - Update the comment at top from "Light Only" to "Light & Dark Mode"

    3. Update `frontend/index.html`:
       - Add an inline script BEFORE the React script tag (inside <body>, before <div id="root">):
         ```html
         <script>
           (function(){var t=localStorage.getItem("donorcrm-theme");if(t==="dark"||(t!=="light"&&window.matchMedia("(prefers-color-scheme: dark)").matches)){document.documentElement.classList.add("dark")}})();
         </script>
         ```
       - This prevents flash of light theme when user prefers dark

    4. Update `frontend/src/App.tsx`:
       - Import ThemeProvider from "@/providers/ThemeProvider"
       - Wrap the existing component tree: ThemeProvider should wrap inside QueryProvider but outside AuthProvider (theme is independent of auth):
         ```
         <QueryProvider>
           <ThemeProvider>
             <AuthProvider>
               ...existing...
             </AuthProvider>
             <Toaster ... />
           </ThemeProvider>
         </QueryProvider>
         ```
  </action>
  <verify>
    Run `cd /home/matkukla/projects/DonorCRM/frontend && npx tsc --noEmit` -- should compile without errors.
    Grep for "donorcrm-theme" in ThemeProvider.tsx and index.html -- both should have matching localStorage key.
    Grep for ".dark" in globals.css -- should find the dark variable block.
  </verify>
  <done>
    ThemeProvider exists with useTheme hook. Dark CSS variables defined. FOUC prevention script in index.html. App.tsx wraps tree in ThemeProvider. TypeScript compiles cleanly.
  </done>
</task>

<task type="auto">
  <name>Task 2: Add theme toggle button to Header and fix hardcoded bg-white</name>
  <files>
    frontend/src/components/layout/Header.tsx
    frontend/src/components/layout/Sidebar.tsx
  </files>
  <action>
    1. Update `frontend/src/components/layout/Header.tsx`:
       - Import `useTheme` from "@/providers/ThemeProvider"
       - Import `Sun` and `Moon` icons from "lucide-react"
       - Add a theme toggle Button (variant="ghost", size="icon") to the LEFT of the user dropdown menu (right side of header, before the DropdownMenu)
       - The button should:
         - Show Sun icon when in dark mode (clicking will switch to light)
         - Show Moon icon when in light mode (clicking will switch to dark)
         - OnClick: cycle through light -> dark -> light (simple toggle, not three-way)
         - Use `resolvedTheme` to determine which icon to show
         - Use `setTheme(resolvedTheme === "dark" ? "light" : "dark")` to toggle
       - Add sr-only text "Toggle theme" for accessibility
       - Replace `bg-white` on the <header> element with `bg-background` so it respects dark mode

    2. Update `frontend/src/components/layout/Sidebar.tsx`:
       - Replace `bg-white` in the aside className with `bg-background`
       - This is the only change needed -- all other sidebar colors already use CSS variable classes (text-primary, bg-primary/10, text-muted-foreground, etc.)

    3. ALSO fix the two hardcoded color instances:
       - In `frontend/src/components/ui/button.tsx`: The `bg-white` in outline/secondary variants should become `bg-background` (lines 23 and 29). Also change `text-white` in those hover states to `text-primary-foreground`.
       - NOTE: Only change the `bg-white` occurrences. Leave `text-white` in hover states as-is since those are intentional contrast colors for filled button states.

    Actually, re-reading button.tsx more carefully: the pattern `bg-white text-primary hover:bg-primary hover:text-white` is an intentional design for outlined buttons. In dark mode, `bg-white` would look wrong. Change `bg-white` to `bg-background` in both variants. The `hover:text-white` can stay as it provides contrast against the primary hover background.
  </action>
  <verify>
    Run `cd /home/matkukla/projects/DonorCRM/frontend && npx tsc --noEmit` -- should compile without errors.
    Grep for "bg-white" in `frontend/src/components/layout/` -- should return zero results.
    Grep for "useTheme" in Header.tsx -- should find the import and usage.
    Run `cd /home/matkukla/projects/DonorCRM/frontend && npm run build` -- full build should succeed.
  </verify>
  <done>
    Theme toggle button visible in header with Sun/Moon icons. All hardcoded bg-white replaced with bg-background in layout components and button variants. Full build passes. Dark mode visually applies to sidebar, header, and all shadcn components.
  </done>
</task>

</tasks>

<verification>
1. `cd /home/matkukla/projects/DonorCRM/frontend && npm run build` passes with no errors
2. No remaining `bg-white` in layout components: `grep -r "bg-white" src/components/layout/` returns nothing
3. ThemeProvider exports useTheme hook with theme/setTheme/resolvedTheme
4. globals.css has both `:root` (light) and `.dark` (dark) variable blocks
5. index.html has inline FOUC prevention script referencing "donorcrm-theme"
6. Header.tsx imports and uses useTheme, renders Sun/Moon toggle button
</verification>

<success_criteria>
- Clicking the theme toggle in the header switches between light and dark mode instantly
- Refreshing the page preserves the selected theme (no flash of wrong theme)
- First-time visitors get their OS preference (light or dark)
- All pages render correctly in both modes: backgrounds, text, cards, borders, buttons all adapt
- The sidebar, header, and all shadcn/ui components respect the dark class
</success_criteria>

<output>
After completion, create `.planning/quick/7-implement-light-and-dark-mode-toggle/7-SUMMARY.md`
</output>
