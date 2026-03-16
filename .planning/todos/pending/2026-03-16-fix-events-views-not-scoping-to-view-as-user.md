# Fix events views not scoping to view_as_user in View As mode

**Added:** 2026-03-16
**Priority:** High
**Phase:** 53 (or add to Phase 52 cleanup if re-executing)

## Problem

`EventListView` and `EventDetailView` in `apps/events/views.py` call `get_visible_user_ids(user, request=self.request)` but then filter by `user=self.request.user` (the viewer), not `request.view_as_user`. In View As mode, events shown belong to the admin/supervisor, not the target missionary.

- `EventListView.get_queryset()` (line 34): `Event.objects.filter(user=user)` where `user = self.request.user`
- `EventDetailView.get_queryset()` (line 49): same — filters by viewer
- `UnreadEventCountView.get()` (line 93): hardcoded `user=request.user` — would show viewer's unread count, not missionary's

## Fix

Resolve the effective user from `request.view_as_user` when present:

```python
effective_user = getattr(self.request, 'view_as_user', None) or self.request.user
return Event.objects.filter(user=effective_user).select_related('contact')
```

Apply the same pattern in `EventDetailView` and `UnreadEventCountView`.

## Notes

- Discovered during Phase 53 context discussion
- The `request=self.request` threading added in Phase 52 is mechanically correct but the view bodies don't use the result for scoping
- The middleware already blocks mutations (mark-read POST), so the mutation safety is fine — only GET data scoping is wrong
