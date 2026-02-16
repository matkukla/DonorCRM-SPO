---
phase: quick-6
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/layout/Sidebar.tsx
  - frontend/src/pages/journals/JournalList.tsx
  - frontend/src/pages/journals/JournalDetail.tsx
  - frontend/src/pages/journals/components/AddContactsDialog.tsx
  - frontend/src/pages/journals/components/CreateJournalDialog.tsx
  - frontend/src/pages/journals/components/index.ts
  - frontend/src/api/journals.ts
  - frontend/src/hooks/useJournals.ts
autonomous: true

must_haves:
  truths:
    - "Journals appears as its own top-level sidebar item (not nested under Insights)"
    - "Insights dropdown no longer contains Journals"
    - "JournalList page has a 'New Journal' button that opens a creation dialog"
    - "JournalDetail page has an 'Add Contacts' button that opens a contact picker dialog"
    - "Creating a journal via the dialog adds it to the list"
    - "Adding contacts via the dialog adds them to the journal grid"
  artifacts:
    - path: "frontend/src/components/layout/Sidebar.tsx"
      provides: "Journals as top-level nav item between Groups and Insights"
    - path: "frontend/src/pages/journals/JournalList.tsx"
      provides: "New Journal button + CreateJournalDialog integration"
    - path: "frontend/src/pages/journals/JournalDetail.tsx"
      provides: "Add Contacts button + AddContactsDialog integration"
    - path: "frontend/src/pages/journals/components/CreateJournalDialog.tsx"
      provides: "Dialog for creating a new journal (name, goal_amount, deadline)"
    - path: "frontend/src/pages/journals/components/AddContactsDialog.tsx"
      provides: "Dialog for adding contacts to a journal with search"
    - path: "frontend/src/api/journals.ts"
      provides: "addContactToJournal API function"
    - path: "frontend/src/hooks/useJournals.ts"
      provides: "useAddContactToJournal mutation hook"
  key_links:
    - from: "Sidebar.tsx"
      to: "/journals"
      via: "NavLink in navItems array"
      pattern: "href.*journals"
    - from: "CreateJournalDialog.tsx"
      to: "useCreateJournal"
      via: "mutation hook"
      pattern: "useCreateJournal"
    - from: "AddContactsDialog.tsx"
      to: "/journals/journal-members/"
      via: "useAddContactToJournal hook"
      pattern: "addContactToJournal"
---

<objective>
Move Journals from the Insights dropdown to its own top-level sidebar tab. Add a "New Journal" button on the JournalList page and an "Add Contacts" button on the JournalDetail page, each opening a dialog for the respective action.

Purpose: Journals are a primary feature deserving top-level navigation, not buried in a dropdown. The action buttons enable users to create journals and add contacts without navigating away.
Output: Updated sidebar, two new dialog components, updated list and detail pages.
</objective>

<execution_context>
@/home/matkukla/.claude/get-shit-done/workflows/execute-plan.md
@/home/matkukla/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/components/layout/Sidebar.tsx
@frontend/src/pages/journals/JournalList.tsx
@frontend/src/pages/journals/JournalDetail.tsx
@frontend/src/pages/journals/components/index.ts
@frontend/src/pages/journals/components/JournalHeader.tsx
@frontend/src/pages/journals/components/LogEventDialog.tsx (dialog pattern reference)
@frontend/src/api/journals.ts
@frontend/src/hooks/useJournals.ts
@frontend/src/hooks/useContacts.ts (useSearchContacts for contact picker)
@frontend/src/types/journals.ts
</context>

<tasks>

<task type="auto">
  <name>Task 1: Move Journals to top-level sidebar + remove from Insights</name>
  <files>frontend/src/components/layout/Sidebar.tsx</files>
  <action>
    In Sidebar.tsx:
    1. Add Journals to the `navItems` array, positioned after Groups (last item). Use `{ label: "Journals", href: "/journals", icon: <BookOpen className="h-5 w-5" /> }`. The BookOpen icon is already imported.
    2. Remove the Journals entry from the `insightsItems` array (the first item: `{ label: "Journals", href: "/journals", icon: <BookOpen className="h-4 w-4" /> }`).
    3. Update the `isInsightsActive` check on line 71 to remove the `|| location.pathname === "/journals"` condition, since Journals is no longer under Insights. It should just be `location.pathname.startsWith("/insights")`.
  </action>
  <verify>
    Run `cd /home/matkukla/projects/DonorCRM/frontend && npx tsc --noEmit` to verify no type errors.
    Visually confirm in the Sidebar.tsx source that:
    - navItems has 7 items (Dashboard, Contacts, Donations, Pledges, Tasks, Groups, Journals)
    - insightsItems has 6 items (no Journals)
    - isInsightsActive no longer checks for /journals
  </verify>
  <done>Journals appears as a top-level sidebar item after Groups; Insights dropdown no longer contains Journals; Insights dropdown no longer auto-expands when navigating to /journals.</done>
</task>

<task type="auto">
  <name>Task 2: Add "New Journal" dialog to JournalList + "Add Contacts" dialog to JournalDetail</name>
  <files>
    frontend/src/pages/journals/components/CreateJournalDialog.tsx
    frontend/src/pages/journals/components/AddContactsDialog.tsx
    frontend/src/pages/journals/components/index.ts
    frontend/src/pages/journals/JournalList.tsx
    frontend/src/pages/journals/JournalDetail.tsx
    frontend/src/api/journals.ts
    frontend/src/hooks/useJournals.ts
  </files>
  <action>
    **Step 1: Add API function for adding a contact to a journal.**

    In `frontend/src/api/journals.ts`, add:
    ```ts
    /** Add a contact to a journal */
    export async function addContactToJournal(journalId: string, contactId: string): Promise<JournalMember> {
      const response = await apiClient.post<JournalMember>('/journals/journal-members/', {
        journal: journalId,
        contact: contactId,
      })
      return response.data
    }
    ```
    Import JournalMember type at the top (it's already imported).

    **Step 2: Add mutation hook.**

    In `frontend/src/hooks/useJournals.ts`, add import for `addContactToJournal` from the API, then add:
    ```ts
    /** Hook for adding a contact to a journal */
    export function useAddContactToJournal(journalId: string) {
      const queryClient = useQueryClient()
      return useMutation({
        mutationFn: (contactId: string) => addContactToJournal(journalId, contactId),
        onSuccess: () => {
          toast.success("Contact added to journal")
          queryClient.invalidateQueries({ queryKey: ["journals", journalId, "members"] })
        },
        onError: () => {
          toast.error("Failed to add contact")
        },
      })
    }
    ```

    **Step 3: Create CreateJournalDialog component.**

    Create `frontend/src/pages/journals/components/CreateJournalDialog.tsx`:
    - Props: `{ open: boolean; onOpenChange: (open: boolean) => void }`
    - Uses Dialog from `@/components/ui/dialog` (follow LogEventDialog.tsx pattern)
    - Form fields: name (required Input), goal_amount (required Input type="number"), deadline (optional Input type="date")
    - Uses `useCreateJournal` hook from `@/hooks/useJournals`
    - On success: toast "Journal created", call onOpenChange(false), navigate to the new journal via `useNavigate` to `/journals/${result.id}`
    - On error: toast "Failed to create journal"
    - Submit button labeled "Create Journal"
    - Reset form fields when dialog closes

    **Step 4: Create AddContactsDialog component.**

    Create `frontend/src/pages/journals/components/AddContactsDialog.tsx`:
    - Props: `{ open: boolean; onOpenChange: (open: boolean) => void; journalId: string; existingContactIds: string[] }`
    - Uses Dialog from `@/components/ui/dialog`
    - Contains a search Input at top that uses `useContacts` with a search filter (debounced with 300ms delay using a local state + useEffect pattern)
    - Shows a list of matching contacts with their name and email
    - Contacts already in the journal (matching existingContactIds) show "Already added" badge and are disabled
    - Each non-existing contact has an "Add" button that calls `useAddContactToJournal` mutation
    - Shows loading state while searching
    - No multi-select needed - just individual "Add" buttons per contact row (simple approach)

    **Step 5: Update barrel export.**

    In `frontend/src/pages/journals/components/index.ts`, add:
    ```ts
    export { CreateJournalDialog } from "./CreateJournalDialog"
    export { AddContactsDialog } from "./AddContactsDialog"
    ```

    **Step 6: Integrate "New Journal" button into JournalList.**

    In `frontend/src/pages/journals/JournalList.tsx`:
    - Import `{ Plus } from "lucide-react"`, `{ useState } from "react"`, and `{ CreateJournalDialog } from "./components"`
    - Add `const [showCreateDialog, setShowCreateDialog] = useState(false)` state
    - Add a "New Journal" button (variant="default", with Plus icon) in the header div, next to the h1/description, aligned right using `flex items-center justify-between` on the header container
    - Render `<CreateJournalDialog open={showCreateDialog} onOpenChange={setShowCreateDialog} />` at the bottom of the component

    **Step 7: Integrate "Add Contacts" button into JournalDetail.**

    In `frontend/src/pages/journals/JournalDetail.tsx`:
    - Import `{ UserPlus } from "lucide-react"`, `{ useState }` (already imported as `* as React`), and `{ AddContactsDialog } from "./components"`
    - Add state: `const [showAddContacts, setShowAddContacts] = React.useState(false)`
    - Derive existingContactIds: `const existingContactIds = members.map(m => m.contact)`
    - Add an "Add Contacts" button (variant="outline", with UserPlus icon) in the header area, next to the back button on line 103-109 area. Place it to the right using flex justify-between.
    - Render `<AddContactsDialog open={showAddContacts} onOpenChange={setShowAddContacts} journalId={id ?? ""} existingContactIds={existingContactIds} />` before the closing div

    **Important:** Use the existing Dialog component from `@/components/ui/dialog`. Follow the same import pattern as LogEventDialog.tsx. Use Input from `@/components/ui/input` and Label from `@/components/ui/label` for form fields.
  </action>
  <verify>
    Run `cd /home/matkukla/projects/DonorCRM/frontend && npx tsc --noEmit` to verify no type errors.
    Verify the new files exist:
    - `ls frontend/src/pages/journals/components/CreateJournalDialog.tsx`
    - `ls frontend/src/pages/journals/components/AddContactsDialog.tsx`
    Verify the barrel export includes both new components.
  </verify>
  <done>
    JournalList page shows a "New Journal" button that opens a dialog with name/goal/deadline fields and creates a journal via API.
    JournalDetail page shows an "Add Contacts" button that opens a searchable contact picker dialog, allows adding individual contacts to the journal via API, and marks already-added contacts.
    Both dialogs follow existing project patterns (Dialog component, mutation hooks, toast notifications).
  </done>
</task>

</tasks>

<verification>
1. `cd /home/matkukla/projects/DonorCRM/frontend && npx tsc --noEmit` -- no TypeScript errors
2. Sidebar shows Journals as standalone top-level item (after Groups, before Insights)
3. Insights dropdown does NOT contain Journals
4. JournalList page header has "New Journal" button
5. JournalDetail page has "Add Contacts" button
6. Both dialogs use existing UI component patterns (Dialog, Input, Label, Button)
</verification>

<success_criteria>
- Journals is a top-level sidebar nav item, not nested under Insights
- "New Journal" button exists on /journals page and opens a creation dialog
- "Add Contacts" button exists on /journals/:id page and opens a contact picker dialog
- TypeScript compiles without errors
- All functionality uses existing API endpoints (no backend changes needed)
</success_criteria>

<output>
After completion, create `.planning/quick/6-move-journal-tab-to-own-sidebar-tab-add-/6-SUMMARY.md`
</output>
