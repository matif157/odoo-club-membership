# Odoo Club Membership

**Memberships, recurring billing and renewals for clubs, gyms and academies — built as a real Odoo 19 module.**

[![Odoo](https://img.shields.io/badge/Odoo-19.0-875A7B)](https://www.odoo.com)
[![License](https://img.shields.io/badge/license-LGPL--3-blue)](LICENSE)
[![Tests](https://github.com/matif157/odoo-club-membership/actions/workflows/ci.yml/badge.svg)](https://github.com/matif157/odoo-club-membership/actions)

---

## Why this exists

A snooker club in Faisalabad runs on a PHP/MySQL system I built. Every month the staff
write the same invoices by hand, chase the same defaulters, and mark the same memberships
as expired. Gym owners and coaching academies do exactly the same thing.

Odoo has sales, invoicing and contacts. What it does not have is the **membership period**:
a start date, an end date, a renewal that keeps history, and a rule that stops the same
person being billed twice for the same month.

This module adds that missing piece.

---

## What it does

| Feature | Detail |
|---|---|
| Membership plans | Monthly / quarterly / yearly, each with its own price and optional product |
| Automatic period | `date_end` is computed from the plan (31 Jan + 1 month = 28/29 Feb) |
| One-click invoicing | Creates a real `account.move` invoice linked to the membership |
| Renewals with history | A renewal creates a **new** membership linked to the previous one — nothing is overwritten |
| Overlap protection | A member cannot hold two overlapping active memberships |
| Expiry cron | A daily job expires finished memberships and logs it in the chatter |
| Security | `User` and `Manager` groups with proper access rights |
| Tests | 17 unit tests covering computes, constraints, invoicing, renewal and cron |

---

## Install

### Docker (recommended)

```bash
git clone https://github.com/matif157/odoo-club-membership.git
cd odoo-club-membership
docker compose up -d
```

Open <http://localhost:8069>, create a database, then **Apps → Update Apps List → Club Membership Management → Install**.

### Manual

```bash
# Odoo 19 source with this repo on the addons path
./odoo-bin --addons-path=addons,../odoo-club-membership -d club -i club_membership
```

### Run the tests

```bash
docker compose run --rm odoo \
  odoo -d testdb -i club_membership --test-tags /club_membership --stop-after-init
```

---

## How it works

```
res.partner ──< club.membership >── club.membership.plan
                     │
                     └──< account.move (out_invoice)
```

- `club.membership.plan` — the product you sell: name, period, price.
- `club.membership` — one member, one period, one state machine
  (`draft → active → expired`, or `cancelled`).
- `account.move` — extended with `club_membership_id` so every invoice knows
  which membership produced it.

### Design decisions

1. **Renewal creates a new record, not a new date.** Overwriting `date_start` would
   destroy the history a club needs when a member disputes a charge.
2. **`date_end` is stored and editable.** Computed fields that cannot be overridden are
   useless in the real world — a member who joins on the 15th needs a manual end date.
3. **The invoice is a normal `account.move`.** No parallel invoice table, no custom PDF
   engine. It appears in Accounting, in the partner ledger, in reports — because it *is*
   an invoice.
4. **Overlap is a Python constraint, not a UI warning.** Business rules belong in the
   model, where the API, the import and the cron all obey them.

---

## Roadmap

- [x] v1.0 — plans, memberships, invoicing, renewal, expiry cron, tests
- [ ] v1.1 — membership freeze / pause with automatic end-date extension
- [ ] v1.2 — family and corporate plans (one payer, many members)
- [ ] v1.3 — portal: member sees their invoices and renewal date
- [ ] v1.4 — attendance check-in and usage limits
- [ ] v1.5 — WhatsApp / SMS renewal reminders (n8n integration)
- [ ] v2.0 — multi-branch support with per-branch revenue reporting

---

## Compatibility

- Odoo 19.0 Community and Enterprise
- PostgreSQL 16
- Python 3.12

---

## Author

**Muhammad Atif** — Odoo implementation and business automation, Faisalabad, Pakistan.

- GitHub: [github.com/matif157](https://github.com/matif157)
- Portfolio: [matif157.github.io](https://matif157.github.io)
- Email: matifzahoor1577@gmail.com

Available for Odoo implementation work and junior/mid Odoo developer roles.

---

## License

LGPL-3.0. See [LICENSE](LICENSE).
