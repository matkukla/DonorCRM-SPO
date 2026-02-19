# Phase 21: Dark Mode & UI Polish - Research

**Researched:** 2026-02-17
**Domain:** Tailwind CSS dark mode, WCAG accessibility, React error boundaries, Django signal correctness, CSV security
**Confidence:** HIGH

## Summary

Phase 21 addresses five distinct quality issues: (1) fixing 50 hardcoded color classes across 14 files that break dark mode, (2) verifying WCAG 4.5:1 contrast compliance, (3) adding a React Error Boundary at the app root, (4) fixing a bug where editing a donation does not refresh contact stats, and (5) adding CSV export formula sanitization. Each issue is well-scoped, has a clear fix pattern, and can be verified independently.

The codebase already has a solid dark mode foundation: Tailwind `darkMode: ["class"]` configuration, CSS custom properties for light/dark themes in `globals.css`, a working `ThemeProvider` with system preference detection, and shadcn/ui components that correctly use semantic color tokens. The problem is that 14 specific files use hardcoded Tailwind color classes (like `bg-green-50`, `text-red-600`, `border-gray-300`) instead of semantic tokens or paired `dark:` variants. The donation stats bug has a clear root cause: `signals.py` line 33 short-circuits with `if not created: return`, meaning `update_giving_stats()` is never called on donation edits. The CSV export sanitization is a simple 5-line utility function applied to 4 export endpoints.

**Primary recommendation:** Fix each issue independently with targeted changes. No architectural refactoring needed -- these are surgical fixes to existing code.

## Standard Stack

### Core (Already Installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| tailwindcss | ^3.4.19 | Utility-first CSS with dark mode support | Already configured with `darkMode: ["class"]` and CSS variables |
| react | ^19.2.0 | UI framework | Already in use |
| @tanstack/react-query | ^5.90.17 | Server state management | Already handles cache invalidation |

### To Install
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react-error-boundary | ^6.1.1 | Declarative error boundary components | De facto standard for React error boundaries. Provides `ErrorBoundary`, `FallbackComponent`, `onReset`, `resetKeys` props. Works with React 19. |

### Not Needed
| Problem | Why No Library | Approach |
|---------|----------------|----------|
| WCAG contrast checking | Manual verification sufficient for 13 files | Use browser DevTools + WebAIM Contrast Checker for spot checks |
| CSV sanitization | 5-line utility function | Hand-roll a `sanitize_csv_value()` function per OWASP guidance |

**Installation:**
```bash
cd frontend && npm install react-error-boundary
```

## Architecture Patterns

### Pattern 1: Semantic Color Token Replacement
**What:** Replace hardcoded Tailwind color classes with semantic tokens or paired `dark:` variants
**When to use:** For all 50 hardcoded color occurrences across 14 files

**Color mapping strategy (by context):**

```
BACKGROUNDS:
  bg-white         -> bg-background (or bg-card)
  bg-gray-*        -> bg-muted
  bg-green-50      -> bg-green-50 dark:bg-green-950/50
  bg-blue-50       -> bg-blue-50 dark:bg-blue-950/50
  bg-red-50        -> bg-red-50 dark:bg-red-950/50
  bg-yellow-50     -> bg-yellow-50 dark:bg-yellow-950/50

TEXT:
  text-gray-*      -> text-muted-foreground (or text-foreground)
  text-black        -> text-foreground
  text-green-600   -> text-green-600 dark:text-green-400
  text-green-800   -> text-green-800 dark:text-green-200
  text-blue-600    -> text-blue-600 dark:text-blue-400
  text-blue-800    -> text-blue-800 dark:text-blue-200
  text-red-600     -> text-red-600 dark:text-red-400
  text-red-800     -> text-red-800 dark:text-red-200
  text-red-900     -> text-red-900 dark:text-red-200
  text-yellow-600  -> text-yellow-600 dark:text-yellow-400
  text-yellow-800  -> text-yellow-800 dark:text-yellow-200

BORDERS:
  border-gray-300  -> border-border (or border-input)
  border-green-200 -> border-green-200 dark:border-green-800
  border-green-500 -> border-green-500 dark:border-green-400
  border-blue-100  -> border-blue-100 dark:border-blue-900/50
  border-blue-200  -> border-blue-200 dark:border-blue-800
  border-red-100   -> border-red-100 dark:border-red-900/50
  border-red-200   -> border-red-200 dark:border-red-800
  border-yellow-200 -> border-yellow-200 dark:border-yellow-800
```

**Decision logic:** Use semantic tokens (`bg-background`, `text-foreground`, `bg-muted`, etc.) when the color represents a generic surface/text. Use paired `dark:` variants when the color carries semantic meaning (success=green, error=red, warning=yellow, info=blue).

### Pattern 2: NeedsAttention Already Has Dark Mode (Reference Pattern)
**What:** `NeedsAttention.tsx` already uses the correct `dark:` variant pattern
**When to use:** As a reference for how to fix the remaining files

```tsx
// Source: frontend/src/components/dashboard/NeedsAttention.tsx (already correct)
<div className="p-4 bg-red-50 dark:bg-red-950/50 border border-red-100 dark:border-red-900/50 rounded-lg">
  <CheckSquare className="h-4 w-4 text-red-600 dark:text-red-400" />
  <span className="font-medium text-red-900 dark:text-red-200">
```

### Pattern 3: React Error Boundary at App Root
**What:** Wrap the app with an ErrorBoundary that catches unhandled rendering errors
**When to use:** Wrap inside ThemeProvider but outside BrowserRouter

```tsx
// Source: https://github.com/bvaughn/react-error-boundary
import { ErrorBoundary } from "react-error-boundary";

function ErrorFallback({ error, resetErrorBoundary }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background text-foreground">
      <div className="max-w-md mx-auto text-center p-8">
        <h1 className="text-2xl font-semibold mb-4">Something went wrong</h1>
        <p className="text-muted-foreground mb-6">
          An unexpected error occurred. Please try refreshing the page.
        </p>
        <button
          onClick={resetErrorBoundary}
          className="px-4 py-2 bg-primary text-primary-foreground rounded-lg"
        >
          Try Again
        </button>
      </div>
    </div>
  );
}

// In App.tsx, wrap inside ThemeProvider:
<ThemeProvider>
  <ErrorBoundary FallbackComponent={ErrorFallback} onReset={() => window.location.reload()}>
    <AuthProvider>
      <BrowserRouter>
        ...
      </BrowserRouter>
    </AuthProvider>
  </ErrorBoundary>
</ThemeProvider>
```

### Pattern 4: Django Signal Fix for Donation Updates
**What:** Remove `if not created: return` guard in donation post_save signal
**When to use:** Fix `apps/donations/signals.py` line 33

```python
# CURRENT (BROKEN): signals.py line 30-41
@receiver(post_save, sender=Donation)
def update_contact_stats_on_save(sender, instance, created, **kwargs):
    if not created:       # <-- THIS LINE skips updates
        return
    if _signals_disabled():
        return
    instance.contact.update_giving_stats()
    # ... rest of signal

# FIXED:
@receiver(post_save, sender=Donation)
def update_contact_stats_on_save(sender, instance, created, **kwargs):
    if _signals_disabled():
        return
    # Always update contact stats (both create and edit)
    instance.contact.update_giving_stats()
    # Only mark as needing thank-you for NEW donations
    if created and not instance.thanked:
        instance.contact.needs_thank_you = True
        instance.contact.save(update_fields=['needs_thank_you'])
    # Only create event and record pledge for NEW donations
    if created:
        if instance.pledge:
            instance.pledge.record_fulfillment(instance)
        from apps.events.models import Event, EventType, EventSeverity
        Event.objects.create(
            user=instance.contact.owner,
            event_type=EventType.DONATION_RECEIVED,
            title=f'Donation from {instance.contact.full_name}',
            message=f'${instance.amount} received',
            severity=EventSeverity.SUCCESS,
            contact=instance.contact
        )
```

Additionally, the frontend `useUpdateDonation` must invalidate the `contacts` query:
```typescript
// CURRENT (BROKEN): hooks/useDonations.ts line 40-49
export function useUpdateDonation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }) => updateDonation(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ["donations"] })
      queryClient.invalidateQueries({ queryKey: ["donations", id] })
      // MISSING: contacts and dashboard invalidation
    },
  })
}

// FIXED:
export function useUpdateDonation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }) => updateDonation(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ["donations"] })
      queryClient.invalidateQueries({ queryKey: ["donations", id] })
      queryClient.invalidateQueries({ queryKey: ["contacts"] })   // ADD
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })  // ADD
    },
  })
}
```

### Pattern 5: CSV Export Formula Sanitization
**What:** Prefix formula-triggering characters in CSV export cell values
**When to use:** All 4 CSV export functions

```python
# Source: OWASP CSV Injection guidance
FORMULA_PREFIXES = ('=', '+', '-', '@')

def sanitize_csv_value(value):
    """Prevent CSV injection by prefixing formula characters with a single quote."""
    if value and isinstance(value, str) and value.startswith(FORMULA_PREFIXES):
        return "'" + value
    return value
```

Apply to:
1. `apps/imports/services.py:export_contacts_csv()` -- sanitize first_name, last_name, email, notes
2. `apps/imports/services.py:export_donations_csv()` -- sanitize contact names, external_id, notes
3. `apps/insights/export_views.py:StalledContactsCSVView` -- sanitize full_name, email, owner_name, status
4. `apps/insights/export_views.py:TeamActivityCSVView` -- sanitize user_name, event_type, title, contact_name

### Anti-Patterns to Avoid
- **Hardcoded `dark:bg-gray-900` everywhere:** Use the existing CSS variable system (`bg-background`, `bg-card`) -- the design system already defines dark mode colors
- **Wrapping every component in its own ErrorBoundary:** One at the app root is sufficient for QAL-10. More granular boundaries are a future enhancement
- **Using `@ts-ignore` in ErrorBoundary code:** The `react-error-boundary` library has full TypeScript support
- **Sanitizing CSV on import instead of export:** The project already rejects formula characters on import. QAL-12 specifically requires export sanitization (defense in depth)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Error boundary component | Class-based ErrorBoundary component | `react-error-boundary` v6.1.1 | Handles edge cases: SSR, concurrent mode, reset logic, typed props. Maintained by React core team member (Brian Vaughn) |
| Contrast checking tool | Custom contrast ratio calculator | WebAIM Contrast Checker + browser DevTools | WCAG formulas are standardized; manual spot-checking 13 files is faster than building tooling |

**Key insight:** The dark mode fix is a search-and-replace task, not an architecture task. The design system (CSS variables in globals.css) already handles dark mode correctly -- the problem is individual files bypassing it.

## Common Pitfalls

### Pitfall 1: Missing `dark:` Variants on Status Colors
**What goes wrong:** Developer replaces `bg-green-50` with `bg-background` to "fix" dark mode, but loses the semantic meaning (green = success). In dark mode, the success card looks identical to a regular card.
**Why it happens:** Over-correcting by using only semantic tokens. Status colors (green/red/yellow/blue) need to remain colored in both modes.
**How to avoid:** Use paired variants: `bg-green-50 dark:bg-green-950/50`. Reference `NeedsAttention.tsx` which already does this correctly.
**Warning signs:** All status colors looking the same in dark mode.

### Pitfall 2: Signal Guard Removal Creates Duplicate Events
**What goes wrong:** Removing `if not created: return` in the donation signal causes Event creation and pledge fulfillment to fire on every donation edit, not just creation.
**Why it happens:** The entire signal handler was gated behind the `created` check. Only `update_giving_stats()` should run on edits; event creation and pledge fulfillment should remain creation-only.
**How to avoid:** Move the `if not created: return` guard BELOW `update_giving_stats()`, not at the top of the function. Or restructure so `update_giving_stats()` runs always and other operations are gated behind `if created:`.
**Warning signs:** Duplicate "Donation received" events appearing when editing a donation.

### Pitfall 3: CSV Sanitization Breaking Legitimate Data
**What goes wrong:** A contact named "Dr. -Smith" gets their name prefixed with `'` in the export, showing as `'-Smith` in a spreadsheet.
**Why it happens:** The sanitization function checks if the value STARTS WITH any formula prefix, and `-` is a common legitimate character (phone numbers, names with hyphens).
**How to avoid:** Only prefix with `'` -- spreadsheet applications strip the leading `'` and display the value as text. This is the OWASP-recommended approach. The `'` is a text-mode indicator, not visible content.
**Warning signs:** User reports about leading apostrophes in exported data (this is actually expected and correct behavior).

### Pitfall 4: ErrorBoundary Not Catching Async Errors
**What goes wrong:** Developer adds ErrorBoundary, tests by throwing in an event handler -- nothing happens. Concludes the boundary is broken.
**Why it happens:** React Error Boundaries only catch errors during rendering, lifecycle methods, and constructors. They do NOT catch errors in event handlers, async code, setTimeout callbacks, or errors thrown outside of React.
**How to avoid:** Understand the scope: ErrorBoundary handles rendering crashes (e.g., accessing `.property` of `undefined` in JSX). Event handler errors are handled by try/catch or mutation error callbacks. The toast system already handles API errors.
**Warning signs:** Testing only with event handler errors instead of render-time errors.

### Pitfall 5: Contrast Ratio Fails Only in Dark Mode
**What goes wrong:** Text that passes 4.5:1 contrast in light mode (dark text on white background) fails in dark mode because the dark mode background is not dark enough or the text is not light enough.
**Why it happens:** The CSS variables define specific HSL values for dark mode. Some custom components may use colors outside the design system that don't adapt.
**How to avoid:** Check contrast ratios in BOTH light and dark mode. The existing CSS variable system is designed for this -- `--foreground` in dark mode is `210 40% 98%` (near white) on `--background` at `222 47% 11%` (dark navy), which exceeds 4.5:1. Problems arise only when hardcoded colors bypass these variables.
**Warning signs:** All automated tests pass in light mode but fail in dark mode.

## Affected Files Inventory

### QAL-03: Hardcoded Dark Mode Colors (50 occurrences across 14 files)

| File | Occurrences | Color Types |
|------|-------------|-------------|
| `components/imports/ImportDialog.tsx` | 12 | green-50/600, blue-600, red-50/600/700/800, yellow-50/200 |
| `components/dashboard/NeedsAttention.tsx` | 11 | Already has dark: variants (REFERENCE PATTERN) |
| `pages/admin/analytics/components/TimePeriodComparison.tsx` | 6 | green-600, red-600, gray-400 |
| `components/imports/ImportCard.tsx` | 3 | green-50/500/600, yellow-50/200 |
| `pages/settings/Settings.tsx` | 3 | green-600 |
| `components/imports/SPOImportTile.tsx` | 3 | yellow-50/200/600/800 |
| `pages/admin/analytics/components/AlertsPanel.tsx` | 2 | red-50/100/900, blue-50/100/900 |
| `pages/admin/analytics/components/UserComparison.tsx` | 2 | green-600 |
| `pages/groups/GroupDetail.tsx` | 2 | border-gray-300 |
| `components/ui/badge.tsx` | 2 | green-100/800, blue-100/800 |
| `components/imports/ExportCard.tsx` | 1 | green-600 |
| `components/dashboard/StatCard.tsx` | 1 | green-600, red-600 |
| `components/dashboard/GivingSummaryCard.tsx` | 1 | green-600 (already has dark: variant) |
| `pages/admin/ImportCenter.tsx` | 1 | blue-50, border-blue-200 |

**Note:** `NeedsAttention.tsx` already uses correct `dark:` pairing -- use as reference. `GivingSummaryCard.tsx` also already has one dark: variant. Exclude already-correct files from work count.

### QAL-10: Error Boundary
| File | Change |
|------|--------|
| `frontend/src/App.tsx` | Wrap with ErrorBoundary inside ThemeProvider |
| `frontend/src/components/ErrorFallback.tsx` | NEW: fallback UI component |

### QAL-11: Donation Edit Stats Bug
| File | Change |
|------|--------|
| `apps/donations/signals.py` | Remove `if not created: return` at line 33, restructure signal |
| `frontend/src/hooks/useDonations.ts` | Add `contacts` and `dashboard` query invalidation to useUpdateDonation |

### QAL-12: CSV Export Sanitization
| File | Change |
|------|--------|
| `apps/imports/services.py` | Add `sanitize_csv_value()` utility, apply to `export_contacts_csv()` and `export_donations_csv()` |
| `apps/insights/export_views.py` | Apply `sanitize_csv_value()` to `StalledContactsCSVView` and `TeamActivityCSVView` |

## Code Examples

### CSV Sanitization Utility
```python
# Source: OWASP CSV Injection (https://owasp.org/www-community/attacks/CSV_Injection)
FORMULA_PREFIXES = ('=', '+', '-', '@')  # Already defined in imports/services.py line 31

def sanitize_csv_value(value):
    """
    Prevent CSV formula injection by prefixing dangerous characters.
    Spreadsheets strip the leading single-quote and display as text.
    """
    if value and isinstance(value, str) and value.startswith(FORMULA_PREFIXES):
        return "'" + value
    return value
```

### Export Function with Sanitization
```python
# Apply to export_contacts_csv (services.py line 364-402)
for contact in queryset:
    writer.writerow({
        'first_name': sanitize_csv_value(contact.first_name),
        'last_name': sanitize_csv_value(contact.last_name),
        'email': sanitize_csv_value(contact.email),
        'phone': sanitize_csv_value(contact.phone),
        'street_address': sanitize_csv_value(contact.street_address),
        'city': sanitize_csv_value(contact.city),
        'state': sanitize_csv_value(contact.state),
        'postal_code': sanitize_csv_value(contact.postal_code),
        'country': sanitize_csv_value(contact.country),
        'status': contact.status,  # enum, safe
        'total_given': str(contact.total_given),  # numeric, safe
        'gift_count': contact.gift_count,  # numeric, safe
        'last_gift_date': str(contact.last_gift_date) if contact.last_gift_date else '',
        'notes': sanitize_csv_value(contact.notes),
    })
```

### ErrorBoundary Fallback Component
```tsx
// Source: react-error-boundary v6.1.1
// (https://github.com/bvaughn/react-error-boundary)
import type { FallbackProps } from "react-error-boundary";

export function ErrorFallback({ error, resetErrorBoundary }: FallbackProps) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background text-foreground p-4">
      <div className="max-w-md w-full text-center space-y-6">
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight">
            Something went wrong
          </h1>
          <p className="text-muted-foreground">
            An unexpected error occurred. Please try refreshing the page.
          </p>
        </div>
        {process.env.NODE_ENV === "development" && (
          <pre className="text-left text-sm bg-muted p-4 rounded-lg overflow-auto max-h-40">
            {error.message}
          </pre>
        )}
        <button
          onClick={resetErrorBoundary}
          className="inline-flex items-center justify-center rounded-lg bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          Refresh Page
        </button>
      </div>
    </div>
  );
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Class-based ErrorBoundary components | `react-error-boundary` v6 with functional components | 2024+ | Simpler API, TypeScript support, reset logic built-in |
| Per-component dark: variants everywhere | CSS custom properties with Tailwind `darkMode: ["class"]` | Tailwind v3.0+ | Single source of truth for colors; components use semantic tokens |
| No CSV output sanitization | OWASP-recommended single-quote prefix | Ongoing | Defense in depth: validate on input, sanitize on output |

**Deprecated/outdated:**
- `componentDidCatch` + `getDerivedStateFromError` class components: Still work but `react-error-boundary` is the standard wrapper
- `bg-white dark:bg-gray-900` pattern: Works but is fragile; CSS variables via `bg-background` is preferred

## Open Questions

1. **Should badge.tsx use custom CSS variables for status colors?**
   - What we know: `badge.tsx` has `bg-green-100 text-green-800` and `bg-blue-100 text-blue-800` for "success" and "info" variants
   - What's unclear: Whether to add CSS variables for status colors or just use `dark:` paired variants
   - Recommendation: Use `dark:` paired variants for now. Adding CSS variables for status colors is overengineering for 2 badge variants.

2. **Should nested ErrorBoundaries be added per route?**
   - What we know: QAL-10 requires "an unhandled React error on any page shows a user-friendly fallback"
   - What's unclear: Whether one root ErrorBoundary is sufficient or each route needs its own
   - Recommendation: One root ErrorBoundary satisfies QAL-10. Per-route boundaries are a future enhancement if needed.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `frontend/src/styles/globals.css` -- CSS variable definitions for light/dark themes
- Codebase analysis: `tailwind.config.js` -- `darkMode: ["class"]` configuration
- Codebase analysis: `apps/donations/signals.py` -- line 33 `if not created: return` bug
- Codebase analysis: `hooks/useDonations.ts` -- missing contacts/dashboard invalidation in useUpdateDonation
- Codebase analysis: `apps/imports/services.py` -- export_contacts_csv and export_donations_csv without sanitization
- Codebase analysis: `apps/insights/export_views.py` -- StalledContactsCSVView and TeamActivityCSVView without sanitization
- [OWASP CSV Injection](https://owasp.org/www-community/attacks/CSV_Injection) -- formula prefix attack vectors and sanitization guidance
- `.planning/EDGE_CASE_AUDIT.md` sections 3.3 (stats not updated on edit) and 6.3 (CSV export unsanitized)

### Secondary (MEDIUM confidence)
- [react-error-boundary v6.1.1 on GitHub](https://github.com/bvaughn/react-error-boundary) -- API, version, React compatibility
- [react-error-boundary on npm](https://www.npmjs.com/package/react-error-boundary) -- latest version and usage
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/) -- WCAG 4.5:1 compliance tool
- [Tailwind CSS Dark Mode docs](https://tailwindcss.com/docs/dark-mode) -- class-based dark mode strategy
- [TestParty WCAG Contrast Guide](https://testparty.ai/blog/wcag-contrast-ratio-guide-2025) -- automated testing limitations

### Tertiary (LOW confidence)
- None -- all findings verified through codebase analysis and official sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed except react-error-boundary (well-documented, stable)
- Architecture: HIGH -- patterns derived from existing codebase (NeedsAttention.tsx, signals.py, EDGE_CASE_AUDIT.md)
- Dark mode fix: HIGH -- exact file list and occurrences counted from grep
- Signal bug: HIGH -- root cause confirmed in signals.py line 33, documented in EDGE_CASE_AUDIT.md section 3.3
- CSV sanitization: HIGH -- OWASP standard, existing FORMULA_PREFIXES constant available, 4 export endpoints identified
- Pitfalls: HIGH -- derived from actual codebase patterns and documented edge cases

**Research date:** 2026-02-17
**Valid until:** 2026-03-17 (stable domain, no fast-moving dependencies)
