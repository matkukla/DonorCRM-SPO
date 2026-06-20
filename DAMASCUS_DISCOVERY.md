# Damascus — Discovery Questions for Customizing DonorCRM

**Purpose:** We're standing up a customized fork of DonorCRM (originally built for Saint Paul's Outreach) for **Damascus Inc**. The answers below let us rebrand it, adapt the data model to how Damascus operates, and wire it into Virtuous correctly.

---

## What we already know (no need to re-ask)

- **Org:** Damascus Inc · damascus.net · serves the Midwest. Summer camps, year-round retreats, missionary formation, worship music + seminars.
- **Model:** Individual missionaries raise their **own personal support**. This app is each missionary's personal fundraising/development tool — they manage their own donors and see their own numbers (the **DonorElf** pattern).
- **Architecture:** The app **runs alongside Virtuous**. Virtuous stays the org's system of record; DonorCRM is the per-missionary dashboard/workflow layer on top of it. Its selling point is **better dashboards**.
- **Scope:** Donor development only — **not** camp registration/attendance (that stays in whatever camp system Damascus uses).

The questions below fill in the operational details we still need.

---

## ⭐ Highest-leverage — answer these first

These four unblock the most work. Everything else is refinement.

1. **Attribution:** In Virtuous, how is a gift or donor tied to a specific Damascus missionary? Is it a *solicitor* on the gift, a *contact owner*, an *originating source/segment/tag*, the gift's *project/designation*, or something else? **This is the single field we sync on** — it's how each missionary's dashboard knows which gifts are theirs.
2. **Virtuous access:** Can you provide **API access** to your Virtuous instance (API key / OAuth)? Should data flow **one-way** (Virtuous → DonorCRM, read-only) or should things missionaries do here (notes, pledges, statuses) **write back** to Virtuous? How fresh must the data be — real-time, hourly, nightly?
3. **Support goals:** Does Damascus set a formal **support goal / "fully funded" standard** per missionary (a target monthly or annual amount)? Is there a minimum/standard level and/or a "what I still need to raise" number you track today? Or is it just "raise what you can"?
4. **Sample export:** Can you share an **anonymized sample export from Virtuous** — a few contact rows and a few gift rows with their column headers? This lets us map fields precisely instead of guessing.

---

## 1. Branding & identity

5. Public-facing name and any short code/abbreviation to use in the app (the "SPO" equivalent)?
6. Can you provide **logo files** (full wordmark + square icon/favicon, ideally vector or high-res PNG, light and dark versions)?
7. **Brand colors** (primary, secondary, accent — hex values) and any brand **font**(s)?
8. Is there a public **donate page** whose look-and-feel we should echo? (The current app mirrors the SPO donate page's styling.)
9. A one-line tagline / description of Damascus for headers and the login screen?
10. ~~What **email domain** do staff accounts use?~~ **✅ Answered: `@damascus.net`** — we auto-generate missionary login accounts from this.

## 2. People, roles & hierarchy

11. Roughly **how many missionaries** raise support? Expected growth?
12. Besides individual missionaries, who else needs logins?
    - **Leadership/development staff** who can see *everyone's* numbers?
    - **Supervisors** who oversee a team/region/cohort and see just their group?
    - **Read-only mentors/coaches** who can see a missionary's relationships but **not** their financial totals?
13. Is there a **supervisory hierarchy** (who reports to whom — by region, ministry, camp, cohort)? How is a missionary assigned to a supervisor?
14. ~~Should a missionary see only their own donors, or is data shared?~~ **✅ Answered: each missionary sees only their own donors.**
15. Who **provisions new user accounts** and deactivates departing missionaries — a central admin, or self-signup restricted to your email domain?

## 3. Support goals & financial model

16. (If goals exist — see Q3) Are goals expressed **monthly, annual, or per-season**? Is there a "**roll-forward balance**" or surplus/deficit carried between periods?
17. What is your **fiscal year start month**? (Drives every year-to-date rollup; SPO uses June 1.)
18. How do you define a missionary as **fully funded** / on-track / behind? Any formula or thresholds we should reproduce on the dashboard?
19. USD only, or any other currencies?
20. How should **one-time vs. recurring** gifts count toward a goal? (e.g., recurring counts at its monthly rate; one-time amortized over 12 months — that's SPO's logic. Does that fit?)

## 4. Donors & contacts

21. What donor types do you track — individuals, families, churches/parishes, businesses, foundations, donor-advised funds?
22. What **lifecycle stages** do you use for a donor relationship? (Current app: prospect → asked → donor → lapsed → declined. Does that match, or do you use different labels?)
23. How long with no gift before a donor is considered **lapsed / at-risk**? (Drives automatic alerts.)
24. How do you **segment** donors today (tags, lists, mailing groups)? A few real examples?
25. Do missionaries track **prayer requests / spiritual notes** per donor? (The app has a "Prayer Intentions" feature — keep, adapt, or remove?)

## 5. Gifts & giving

26. What **payment methods** do you receive (check, cash, card, ACH, online, stock, DAF)?
27. What **recurring** frequencies do you support (monthly, quarterly, annual)?
28. Can one gift be **split/credited across multiple missionaries**, or is it always one missionary per gift?
29. What **funds / designations / projects** do gifts go to in Virtuous, and which of those are relevant to an individual missionary's support? Can you list them?
30. Do you need **tax receipts / acknowledgment letters** generated from this app, or is that handled in Virtuous?

## 6. Cultivation workflow / pipeline

31. Walk us through how a missionary moves someone from prospect to committed supporter. Does this pipeline fit?
    *contact → schedule → meet → ask → decision → thank → next steps*
32. Do you record **pledges/commitments** (a promise to give a set amount on a cadence), and do you track whether they're fulfilled?
33. Should the app **auto-create follow-up reminders/tasks** — e.g., when a pledge isn't fulfilled by its date, or when a donor lapses?

## 7. Communications & notifications

34. Should the app **send email** (reminders, summaries, alerts)? From what address, and may we wire up a provider (SendGrid/Postmark/etc.)?
35. Do you want a **weekly summary email** to each missionary (and/or supervisors)? What should it contain?
36. Do you want **at-risk/lapsed-donor alerts** and **thank-you reminders**? Same triggers as described above, or different?

## 8. Dashboards & reporting (your stated differentiator)

37. What are the **top things a missionary** should see the moment they log in? (e.g., % to goal, monthly support trend, new donors, who lapsed, who needs a thank-you, upcoming tasks.)
38. What do **supervisors/leadership** need to see across their team? (e.g., each missionary's % funded, who's behind, team totals.)
39. What reports do you produce today (in Virtuous or spreadsheets) that this should replace or improve on?

## 9. Virtuous integration — details

40. Besides contacts and gifts, do you want us to pull **recurring-gift commitments**, **tags/segments**, and **project/designation** data from Virtuous?
41. Is there a stable **unique ID** per contact and per gift in Virtuous we can key on (for clean, repeat syncing without duplicates)?
42. Do you also use a separate **accounting** system (QuickBooks, Aplos, etc.) or an **online giving** platform (RaiseDonors, Fundraise Up, Pushpay, etc.) that feeds Virtuous — anything we should be aware of for reconciliation?
43. Roughly **how many contact and gift records** are in Virtuous today (sizing the sync)?

## 10. Security, hosting & timeline

44. Do you want **single sign-on** (Google Workspace / Microsoft 365)? What's your staff identity provider?
45. Any **data-protection / confidentiality / retention** requirements for donor data we should honor?
46. Should we **host** it (e.g., Render) or do you need it on Damascus infrastructure? Desired **URL/subdomain**?
47. **Target go-live date** and any hard deadlines (camp season, fiscal year, fall fundraising push)?
48. For launch, what's **must-have vs. nice-to-have**? (Helps us phase: rebrand + Virtuous sync + dashboards first, deeper workflow later.)

---

## Open product decisions for *us* (Matthew), not Damascus

- Keep the **"coach" read-only mentor** role, or drop it until Damascus confirms a need? (Tied to Q12.)
- Keep the **Prayer Intentions** feature on by default? (Tied to Q25 — likely yes given the ministry context.)
- Default the **fiscal year** to calendar-year (Jan 1) until Q17 is answered, rather than leaving SPO's June 1.
