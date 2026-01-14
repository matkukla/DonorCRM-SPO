# DonorCRM - Lean Missionary Support Management System

A purpose-built CRM for missionaries and nonprofit staff who raise personal support, designed to be simple, motivating, and actually used.

## Overview

DonorCRM is a minimalist donor relationship management system focused on helping individual fundraisers track gifts, manage pledges, and maintain strong donor relationships with minimal friction. Built from research into missionary support-raising workflows, it delivers essential CRM functionality without the complexity that drives low adoption.

### Why DonorCRM?

Traditional donor CRMs suffer from low adoption because they:
- Overwhelm users with too many features and data points
- Feel like administrative work rather than helpful assistance
- Lack clear, actionable guidance on what to do next
- Don't provide motivating feedback on completed work

DonorCRM solves these problems by:
- **Clarity First**: Clean dashboard answering "What changed? What needs attention? What's at risk?"
- **Actionable Insights**: Automatic alerts that tell you exactly who to contact and why
- **Positive Reinforcement**: Visible progress tracking and completion indicators
- **Minimal Friction**: Essential features only, with intuitive navigation

## Core Features

### Dashboard Intelligence
- **What Changed**: Summary of new gifts, donors, and updates since last login
- **Needs Attention**: Prioritized list of follow-up actions (late donors, pledge expirations)
- **Trend Snapshot**: Visual progress toward support goals
- **At-Risk Donors**: Early warning for donors who might stop giving
- **Thank-You Queue**: Track acknowledgments sent and pending

### Donor Management
- Contact database with search and tagging
- Giving history and trends for each donor
- Pledge/recurring commitment tracking
- Automated alerts (new donor, late gift, stopped giving, pledge changes)

### Task Management
- Reminder system with due dates (defaults to prevent forgetting)
- Link tasks to specific donors
- Dashboard integration for upcoming/overdue items

### Reporting
- Monthly donation summaries
- Support level vs. goal tracking
- Basic exports for external use (mailings, backups)

### Data Import/Export
- CSV import for donations and contacts
- Export donor lists and giving records
- Built-in duplicate prevention

## Key Workflows

1. **Monitoring Updates**: Log in → See dashboard summary → Identify what needs attention
2. **Following Up**: Review alert → Click donor → Take action (call/email) → Mark complete
3. **Managing Pledges**: Add/update recurring commitments → System tracks fulfillment → Alerts on issues
4. **Thanking Donors**: New gift arrives → Notification appears → Send thank-you → Track completion
5. **Reviewing Status**: Check dashboard trends → Identify lapsed donors → Reach out proactively

## Technology Stack

*(To be determined based on implementation)*

- **Backend**: Django (Python)
- **Database**: PostgreSQL (recommended for data integrity)
- **Frontend**: React
- **Authentication**: Role-based access control

## Data Model

### Core Entities
- **Users**: Fundraisers, admins, finance staff, read-only viewers
- **Contacts**: Donor and prospect information with ownership
- **Donations**: Individual gift records
- **Pledges**: Recurring giving commitments
- **Tasks**: Reminders and action items
- **Events**: Change log and notification feed
- **Groups**: Contact tags/segments

See full schema documentation in `/docs/data-model.md`

## User Roles

- **Fundraiser**: Manages their own donors, pledges, and tasks
- **Admin**: Full system access, user management, data imports
- **Finance**: Import donations, view giving across organization
- **Read-Only**: View-only access for coaches/supervisors

## Getting Started

### Prerequisites
- [Database system]
- [Runtime environment]
- [Other dependencies]

### Installation
```bash
# Clone repository
git clone https://github.com/yourorg/donorcrm.git
cd donorcrm

# Install dependencies
[installation commands]

# Configure database
[database setup]

# Initialize application
[initialization steps]

# Start development server
[run command]
```

### Initial Setup

1. Create admin account
2. Configure organization settings
3. Import historical donor data (CSV)
4. Create user accounts for fundraisers
5. Assign donors to users

## Usage

### For Fundraisers

**Daily Workflow:**
1. Log in to see dashboard summary
2. Review "Needs Attention" list
3. Follow up with flagged donors
4. Mark tasks complete
5. Check progress toward goals

**Weekly Tasks:**
- Review giving trends
- Update pledges for changes
- Process thank-you queue
- Add any new prospects

### For Admins

**Regular Tasks:**
- Import donation data (weekly/monthly)
- Review/clean duplicate contacts
- Assist users with data questions
- Monitor system health

**Occasional Tasks:**
- Add/remove user accounts
- Export data for leadership
- Update organization settings

## Design Principles

1. **Every feature must justify its existence** - If it doesn't serve a daily workflow, it doesn't ship
2. **Clarity over completeness** - Better to do 5 things excellently than 50 things poorly
3. **Feedback loops matter** - Users need to see their actions acknowledged
4. **Reduce cognitive load** - Present minimum information needed to make decisions
5. **Progressive disclosure** - Hide complexity behind clear paths

## What We Explicitly DON'T Do

To maintain focus and simplicity:
- ❌ Process online donations (integrate with existing platforms)
- ❌ Manage fundraising events or campaigns
- ❌ Track grants or institutional giving
- ❌ Handle volunteer or membership management
- ❌ Replicate accounting functions
- ❌ Send bulk emails (export for MailChimp instead)

## Roadmap

### MVP (Phase 1)
- [x] Contact management
- [x] Donation tracking
- [x] Pledge management
- [x] Automated alerts
- [x] Task system
- [x] Dashboard
- [x] CSV import/export
- [x] User roles

### Future Enhancements
- [ ] Email integration (MailChimp sync)
- [ ] Mobile-responsive design
- [ ] Advanced filtering/search
- [ ] Coaching dashboards
- [ ] Custom fields
- [ ] Multi-currency support
- [ ] Direct accounting integrations

## Contributing

We welcome contributions that align with our lean, user-focused philosophy. Before adding features:

1. Validate the need with actual users
2. Ensure it serves a daily workflow
3. Keep the UI simple and clear
4. Include tests for reliability

See `CONTRIBUTING.md` for detailed guidelines.

## Support

- **Documentation**: [Link to docs]
- **Issues**: [GitHub Issues]
- **Email**: support@yourorg.org

## Research & Background

This project is based on extensive research into missionary fundraising workflows, particularly studying the DonorElf platform and identifying what drives (or prevents) CRM adoption. Key insights:

- Users need actionable prompts, not just data dumps
- Pledge tracking is critical for proactive donor care
- Weekly email summaries drive consistent engagement
- Simple beats comprehensive for adoption rates
- Trust depends on data accuracy and simplicity

Full research document available in `/docs/research.md`

## License

[Your chosen license]

## Acknowledgments

- Research informed by DonorElf usage patterns and missionary support-raising best practices
- Built to serve [Your Organization]'s 100+ fundraising staff
- Designed with feedback from frontline missionaries

---

**Philosophy**: *"A CRM should feel like a helpful assistant who knows exactly what you need to do today, not a database you have to maintain."*
