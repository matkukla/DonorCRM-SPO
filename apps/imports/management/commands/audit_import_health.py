"""
Management command to audit import pipeline data quality.

Read-only diagnostic tool that checks solicitor linking, contact ownership,
gift credit integrity, recurring gift credit integrity, and dashboard impact.

Usage:
    python manage.py audit_import_health
    python manage.py audit_import_health --verbose
    python manage.py audit_import_health --json
"""

import difflib
import json
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Count, Q, Sum

from apps.contacts.models import Contact
from apps.gifts.models import Gift, GiftCredit, RecurringGift, RecurringGiftCredit, Solicitor
from apps.imports.models import MissionaryAlias
from apps.users.models import User


class Command(BaseCommand):
    help = "Audit import pipeline data quality across 5 diagnostic sections"

    def add_arguments(self, parser):
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show per-record detail lists",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Output machine-readable JSON instead of text",
        )

    def handle(self, *args, **options):
        verbose = options["verbose"]
        json_output = options["json_output"]

        # Edge case: no solicitors
        if Solicitor.objects.count() == 0:
            if json_output:
                self.stdout.write(
                    json.dumps(
                        {"message": "No solicitors found. Import solicitors first."},
                        indent=2,
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING("No solicitors found. Import solicitors first.")
                )
            return

        # Collect all report data
        report = {}
        issue_count = 0

        # --- Section 1: Solicitor Linking ---
        section1 = self._section1_solicitor_linking()
        report["solicitor_linking"] = section1
        issue_count += section1["unlinked"]

        # --- Section 2: Contact Ownership ---
        section2 = self._section2_contact_ownership()
        report["contact_ownership"] = section2
        issue_count += len(section2["misattributions"])

        # --- Section 3: Gift Credit Integrity ---
        section3 = self._section3_gift_credit_integrity()
        report["gift_credit_integrity"] = section3
        issue_count += section3["orphaned_count"]

        # --- Section 4: Recurring Gift Credit Integrity ---
        section4 = self._section4_recurring_gift_credit_integrity()
        report["recurring_gift_credit_integrity"] = section4
        issue_count += section4["orphaned_count"]

        # --- Section 5: Dashboard Impact Estimate ---
        section5 = self._section5_dashboard_impact()
        report["dashboard_impact"] = section5
        issue_count += len(section5["flagged"])

        # --- Verdict ---
        if issue_count == 0:
            verdict = "HEALTHY -- All import data is clean."
        else:
            verdict = f"NEEDS ATTENTION -- {issue_count} issue(s) detected."
        report["verdict"] = {
            "status": "HEALTHY" if issue_count == 0 else "NEEDS ATTENTION",
            "issue_count": issue_count,
            "message": verdict,
        }

        # Output
        if json_output:
            self.stdout.write(json.dumps(report, indent=2, default=str))
        else:
            self._print_text(report, verbose)

    # -----------------------------------------------------------------
    # Section 1: Solicitor Linking
    # -----------------------------------------------------------------

    def _section1_solicitor_linking(self):
        total = Solicitor.objects.count()
        linked = Solicitor.objects.filter(user__isnull=False).count()
        unlinked = total - linked
        linked_pct = round(linked / total * 100, 1) if total else 0
        unlinked_pct = round(unlinked / total * 100, 1) if total else 0

        # Unlinked solicitor details for verbose output
        unlinked_solicitors = list(
            Solicitor.objects.filter(user__isnull=True).values(
                "id", "normalized_name", "external_solicitor_id"
            )
        )

        # Near-miss detection
        near_misses = []
        if unlinked_solicitors:
            # Build candidate list: "First Last", "Last, First", and aliases
            candidates = []
            for fn, ln in User.objects.values_list("first_name", "last_name"):
                candidates.append({"name": f"{fn} {ln}", "format": "first_last"})
                candidates.append({"name": f"{ln}, {fn}", "format": "last_first"})
            for alias in MissionaryAlias.objects.filter(user__isnull=False).values_list(
                "source_name", flat=True
            ):
                candidates.append({"name": alias, "format": "alias"})

            for sol in unlinked_solicitors:
                for c in candidates:
                    ratio = difflib.SequenceMatcher(
                        None, sol["normalized_name"].lower(), c["name"].lower()
                    ).ratio()
                    if ratio >= 0.8:
                        near_misses.append(
                            {
                                "solicitor_name": sol["normalized_name"],
                                "candidate": c["name"],
                                "format": c["format"],
                                "score": round(ratio, 3),
                            }
                        )

        return {
            "total": total,
            "linked": linked,
            "unlinked": unlinked,
            "linked_pct": linked_pct,
            "unlinked_pct": unlinked_pct,
            "unlinked_solicitors": unlinked_solicitors,
            "near_misses": near_misses,
        }

    # -----------------------------------------------------------------
    # Section 2: Contact Ownership
    # -----------------------------------------------------------------

    def _section2_contact_ownership(self):
        # Group contacts by owner role
        role_counts = list(
            Contact.objects.values("owner__role")
            .annotate(count=Count("id"))
            .order_by("owner__role")
        )

        # Misattribution detection: admin/supervisor-owned contacts with
        # gift credits OR recurring gift credits pointing to a missionary
        misattributed_contacts = (
            Contact.objects.filter(
                owner__role__in=["admin", "supervisor"],
            )
            .filter(
                Q(gifts__credits__solicitor__user__role="missionary")
                | Q(recurring_gifts__credits__solicitor__user__role="missionary")
            )
            .distinct()
            .select_related("owner")
        )

        misattributions = []
        for contact in misattributed_contacts:
            # Find missionary user(s) credited via solicitor (gifts + recurring)
            missionary_solicitors = (
                Solicitor.objects.filter(
                    Q(gift_credits__gift__donor_contact=contact)
                    | Q(recurring_gift_credits__recurring_gift__donor_contact=contact),
                    user__role="missionary",
                )
                .distinct()
                .select_related("user")
            )
            misattributions.append(
                {
                    "contact_id": contact.id,
                    "contact_name": f"{contact.first_name} {contact.last_name}",
                    "external_constituent_id": contact.external_constituent_id,
                    "owner_email": contact.owner.email,
                    "owner_role": contact.owner.role,
                    "missionary_emails": [s.user.email for s in missionary_solicitors],
                }
            )

        return {
            "role_counts": role_counts,
            "misattributions": misattributions,
        }

    # -----------------------------------------------------------------
    # Section 3: Gift Credit Integrity
    # -----------------------------------------------------------------

    def _section3_gift_credit_integrity(self):
        total_gifts = Gift.objects.count()
        total_credits = GiftCredit.objects.count()
        linked_credits = GiftCredit.objects.filter(solicitor__user__isnull=False).count()
        unlinked_credits = total_credits - linked_credits

        orphaned_gifts = Gift.objects.annotate(credit_count=Count("credits")).filter(credit_count=0)
        orphaned_count = orphaned_gifts.count()

        # Dollar value of orphaned gifts (no credits — cannot route to any missionary)
        orphaned_value = orphaned_gifts.aggregate(total=Sum("amount_cents"))["total"] or 0
        unlinked_dollars = Decimal(orphaned_value) / Decimal(100)

        # Orphaned gift details for verbose
        orphaned_details = list(
            orphaned_gifts.values_list(
                "id",
                "donor_contact__first_name",
                "donor_contact__last_name",
                "amount_cents",
                "gift_date",
            )[:20]
        )

        return {
            "total_gifts": total_gifts,
            "total_credits": total_credits,
            "linked_credits": linked_credits,
            "unlinked_credits": unlinked_credits,
            "orphaned_count": orphaned_count,
            "unlinked_dollars": f"{unlinked_dollars:.2f}",
            "orphaned_details": orphaned_details,
        }

    # -----------------------------------------------------------------
    # Section 4: Recurring Gift Credit Integrity
    # -----------------------------------------------------------------

    def _section4_recurring_gift_credit_integrity(self):
        active_recurring = RecurringGift.objects.filter(status="active")
        total_active = active_recurring.count()
        total_credits = RecurringGiftCredit.objects.filter(recurring_gift__status="active").count()
        linked_credits = RecurringGiftCredit.objects.filter(
            recurring_gift__status="active",
            solicitor__user__isnull=False,
        ).count()
        unlinked_credits = total_credits - linked_credits

        orphaned = active_recurring.annotate(credit_count=Count("credits")).filter(credit_count=0)
        orphaned_count = orphaned.count()

        # Dollar value of orphaned active recurring gifts (no credits)
        orphaned_value = orphaned.aggregate(total=Sum("amount_cents"))["total"] or 0
        unlinked_dollars = Decimal(orphaned_value) / Decimal(100)

        # Orphaned details for verbose
        orphaned_details = list(
            orphaned.values_list(
                "id",
                "donor_contact__first_name",
                "donor_contact__last_name",
                "amount_cents",
                "frequency",
            )[:20]
        )

        return {
            "total_active": total_active,
            "total_credits": total_credits,
            "linked_credits": linked_credits,
            "unlinked_credits": unlinked_credits,
            "orphaned_count": orphaned_count,
            "unlinked_dollars": f"{unlinked_dollars:.2f}",
            "orphaned_details": orphaned_details,
        }

    # -----------------------------------------------------------------
    # Section 5: Dashboard Impact Estimate
    # -----------------------------------------------------------------

    def _section5_dashboard_impact(self):
        missionaries = User.objects.filter(role="missionary")
        rows = []
        flagged = []

        for user in missionaries:
            contacts_count = Contact.objects.filter(owner=user).count()
            gift_sum = (
                Gift.objects.filter(donor_contact__owner=user).aggregate(total=Sum("amount_cents"))[
                    "total"
                ]
                or 0
            )
            active_recurring_qs = RecurringGift.objects.filter(
                donor_contact__owner=user, status="active"
            )
            recurring_count = active_recurring_qs.count()
            recurring_sum = active_recurring_qs.aggregate(total=Sum("amount_cents"))["total"] or 0
            credit_count = GiftCredit.objects.filter(solicitor__user=user).count()

            row = {
                "user_name": user.full_name,
                "user_email": user.email,
                "contacts": contacts_count,
                "gift_dollars": str(Decimal(gift_sum) / Decimal(100)),
                "active_recurring_count": recurring_count,
                "recurring_dollars": str(Decimal(recurring_sum) / Decimal(100)),
                "credit_count": credit_count,
                "flagged": False,
                "flag_reasons": [],
            }

            flag_reasons = []
            if contacts_count == 0:
                flag_reasons.append("0 contacts — will see empty dashboard")
            if contacts_count == 0 and credit_count > 0:
                flag_reasons.append(
                    "0 contacts but has gift credits via solicitor — "
                    "suggests contact ownership not reassigned"
                )
            if gift_sum == 0 and credit_count > 0:
                flag_reasons.append(
                    "0 gifts (by ownership) but has gift credits via solicitor — "
                    "suggests contact ownership not reassigned"
                )

            if flag_reasons:
                row["flagged"] = True
                row["flag_reasons"] = flag_reasons
                flagged.append(row)

            rows.append(row)

        return {
            "missionaries": rows,
            "flagged": flagged,
        }

    # -----------------------------------------------------------------
    # Text output formatting
    # -----------------------------------------------------------------

    def _print_text(self, report, verbose):
        # Section 1
        s1 = report["solicitor_linking"]
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Section 1: Solicitor Linking ==="))
        self.stdout.write(f'  Total: {s1["total"]}')
        self.stdout.write(f'  Linked: {s1["linked"]} ({s1["linked_pct"]}%)')
        self.stdout.write(f'  Unlinked: {s1["unlinked"]} ({s1["unlinked_pct"]}%)')

        if s1["near_misses"]:
            self.stdout.write(self.style.WARNING(f'  Near-misses found: {len(s1["near_misses"])}'))
            if verbose:
                for nm in s1["near_misses"]:
                    self.stdout.write(
                        f'    - "{nm["solicitor_name"]}" ~ '
                        f'"{nm["candidate"]}" ({nm["format"]}, score: {nm["score"]})'
                    )

        if verbose and s1["unlinked_solicitors"]:
            self.stdout.write("  Unlinked solicitors:")
            for sol in s1["unlinked_solicitors"]:
                ext_id = sol["external_solicitor_id"]
                id_str = f", ext_id={ext_id}" if ext_id else ""
                self.stdout.write(f'    - #{sol["id"]} {sol["normalized_name"]}{id_str}')

        # Section 2
        s2 = report["contact_ownership"]
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Section 2: Contact Ownership ==="))
        for rc in s2["role_counts"]:
            self.stdout.write(f'  {rc["owner__role"]}: {rc["count"]} contacts')

        if s2["misattributions"]:
            self.stdout.write(
                self.style.WARNING(f'  Misattributions found: {len(s2["misattributions"])}')
            )
            if verbose:
                for ma in s2["misattributions"]:
                    self.stdout.write(
                        f'    - {ma["contact_name"]} '
                        f'(ext: {ma["external_constituent_id"] or "N/A"}) '
                        f'owned by {ma["owner_email"]} ({ma["owner_role"]}) '
                        f'but credited to {", ".join(ma["missionary_emails"])}'
                    )
        else:
            self.stdout.write(self.style.SUCCESS("  No misattributions detected."))

        # Section 3
        s3 = report["gift_credit_integrity"]
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Section 3: Gift Credit Integrity ==="))
        self.stdout.write(f'  Total gifts: {s3["total_gifts"]}')
        self.stdout.write(f'  Total credits: {s3["total_credits"]}')
        self.stdout.write(f'  Credits linked: {s3["linked_credits"]}')
        self.stdout.write(f'  Credits unlinked: {s3["unlinked_credits"]}')
        self.stdout.write(f'  Orphaned gifts (no credits): {s3["orphaned_count"]}')
        self.stdout.write(f'  Unlinked credit dollar value: ${s3["unlinked_dollars"]}')

        if verbose and s3["orphaned_details"]:
            self.stdout.write("  Orphaned gift details:")
            for gid, fn, ln, cents, gdate in s3["orphaned_details"]:
                dollars = Decimal(cents) / Decimal(100)
                self.stdout.write(f"    - Gift #{gid}: {fn} {ln}, ${dollars:.2f} on {gdate}")

        # Section 4
        s4 = report["recurring_gift_credit_integrity"]
        self.stdout.write(
            self.style.MIGRATE_HEADING("\n=== Section 4: Recurring Gift Credit Integrity ===")
        )
        self.stdout.write(f'  Active recurring gifts: {s4["total_active"]}')
        self.stdout.write(f'  Active recurring credits: {s4["total_credits"]}')
        self.stdout.write(f'  Credits linked: {s4["linked_credits"]}')
        self.stdout.write(f'  Credits unlinked: {s4["unlinked_credits"]}')
        self.stdout.write(f'  Orphaned active recurring gifts: {s4["orphaned_count"]}')
        self.stdout.write(f'  Unlinked credit dollar value: ${s4["unlinked_dollars"]}')

        if verbose and s4["orphaned_details"]:
            self.stdout.write("  Orphaned recurring gift details:")
            for rgid, fn, ln, cents, freq in s4["orphaned_details"]:
                dollars = Decimal(cents) / Decimal(100)
                self.stdout.write(f"    - RecurringGift #{rgid}: {fn} {ln}, ${dollars:.2f}/{freq}")

        # Section 5
        s5 = report["dashboard_impact"]
        self.stdout.write(
            self.style.MIGRATE_HEADING("\n=== Section 5: Dashboard Impact Estimate ===")
        )
        self.stdout.write(f'  Missionaries: {len(s5["missionaries"])}')
        if s5["flagged"]:
            self.stdout.write(self.style.WARNING(f'  Flagged missionaries: {len(s5["flagged"])}'))
            if verbose:
                for f in s5["flagged"]:
                    self.stdout.write(
                        f'    - {f["user_name"]} ({f["user_email"]}): '
                        f'{", ".join(f["flag_reasons"])}'
                    )
        else:
            self.stdout.write(self.style.SUCCESS("  No flagged missionaries."))

        if verbose:
            self.stdout.write("  Per-missionary breakdown:")
            for m in s5["missionaries"]:
                flag_marker = " [FLAGGED]" if m["flagged"] else ""
                self.stdout.write(
                    f'    - {m["user_name"]} ({m["user_email"]}): '
                    f'{m["contacts"]} contacts, '
                    f'${m["gift_dollars"]} gifts, '
                    f'{m["active_recurring_count"]} active recurring (${m["recurring_dollars"]}), '
                    f'{m["credit_count"]} credits{flag_marker}'
                )

        # Verdict
        v = report["verdict"]
        self.stdout.write("")
        if v["status"] == "HEALTHY":
            self.stdout.write(self.style.SUCCESS(v["message"]))
        else:
            self.stdout.write(self.style.ERROR(v["message"]))
