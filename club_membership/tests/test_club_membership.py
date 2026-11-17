# Part of Club Membership Management. See LICENSE file for full copyright and licensing details.

from datetime import date

from dateutil.relativedelta import relativedelta

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestClubMembership(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.company
        cls.income_account = cls.env["account.account"].search(
            [("account_type", "=", "income")], limit=1
        )
        if not cls.income_account:
            cls.income_account = cls.env["account.account"].create(
                {
                    "name": "Test Income",
                    "code": "999999",
                    "account_type": "income",
                }
            )
        cls.sale_journal = cls.env["account.journal"].search(
            [("type", "=", "sale")], limit=1
        )
        if not cls.sale_journal:
            cls.sale_journal = cls.env["account.journal"].create(
                {
                    "name": "Test Sales",
                    "code": "TSAL",
                    "type": "sale",
                    "default_account_id": cls.income_account.id,
                }
            )
        cls.partner = cls.env["res.partner"].create({"name": "Test Member"})
        cls.other_partner = cls.env["res.partner"].create({"name": "Second Member"})
        cls.plan = cls.env["club.membership.plan"].create(
            {
                "name": "Monthly Gym",
                "code": "GYM-M",
                "price": 5000.0,
                "billing_period": "month",
            }
        )
        cls.plan_quarter = cls.env["club.membership.plan"].create(
            {
                "name": "Quarterly Gym",
                "code": "GYM-Q",
                "price": 13500.0,
                "billing_period": "quarter",
            }
        )

    def _make_membership(self, partner=None, plan=None, start=None, **kwargs):
        vals = {
            "partner_id": (partner or self.partner).id,
            "plan_id": (plan or self.plan).id,
            "date_start": start or date(2026, 1, 1),
        }
        vals.update(kwargs)
        return self.env["club.membership"].create(vals)

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    def test_period_months(self):
        self.assertEqual(self.plan.period_months, 1)
        self.assertEqual(self.plan_quarter.period_months, 3)

    def test_date_end_monthly(self):
        membership = self._make_membership()
        self.assertEqual(membership.date_end, date(2026, 1, 31))

    def test_date_end_quarterly(self):
        membership = self._make_membership(plan=self.plan_quarter)
        self.assertEqual(membership.date_end, date(2026, 3, 31))

    def test_date_end_leap_year(self):
        membership = self._make_membership(start=date(2028, 1, 31))
        self.assertEqual(membership.date_end, date(2028, 2, 28))

    def test_price_defaults_from_plan(self):
        membership = self._make_membership()
        self.assertEqual(membership.price, 5000.0)

    # ------------------------------------------------------------------
    # Sequence
    # ------------------------------------------------------------------
    def test_name_from_sequence(self):
        membership = self._make_membership()
        self.assertNotEqual(membership.name, "New")
        self.assertTrue(membership.name.startswith("MEM/"))

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------
    def test_activate(self):
        membership = self._make_membership()
        self.assertEqual(membership.state, "draft")
        membership.action_activate()
        self.assertEqual(membership.state, "active")

    def test_cancel(self):
        membership = self._make_membership()
        membership.action_activate()
        membership.action_cancel()
        self.assertEqual(membership.state, "cancelled")

    # ------------------------------------------------------------------
    # Invoicing
    # ------------------------------------------------------------------
    def test_invoice_created(self):
        membership = self._make_membership()
        membership.action_activate()
        membership.action_create_invoice()
        self.assertEqual(len(membership.invoice_ids), 1)
        invoice = membership.invoice_ids
        self.assertEqual(invoice.move_type, "out_invoice")
        self.assertEqual(invoice.amount_total, 5000.0)
        self.assertEqual(invoice.club_membership_id, membership)

    def test_second_invoice_blocked(self):
        membership = self._make_membership()
        membership.action_activate()
        membership.action_create_invoice()
        with self.assertRaises(UserError):
            membership.action_create_invoice()

    def test_cancelled_membership_cannot_be_invoiced(self):
        membership = self._make_membership()
        membership.action_cancel()
        with self.assertRaises(UserError):
            membership.action_create_invoice()

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    def test_end_before_start_rejected(self):
        with self.assertRaises(ValidationError):
            self._make_membership(
                start=date(2026, 1, 1),
                date_end=date(2025, 12, 1),
            )

    def test_overlap_rejected(self):
        first = self._make_membership()
        first.action_activate()
        with self.assertRaises(ValidationError):
            self._make_membership(start=date(2026, 1, 15))

    def test_no_overlap_for_other_member(self):
        first = self._make_membership()
        first.action_activate()
        second = self._make_membership(
            partner=self.other_partner, start=date(2026, 1, 15)
        )
        self.assertEqual(second.state, "draft")

    # ------------------------------------------------------------------
    # Renewal
    # ------------------------------------------------------------------
    def test_renewal_creates_new_membership(self):
        membership = self._make_membership()
        membership.action_activate()
        action = membership.action_renew()
        new_membership = self.env["club.membership"].browse(action["res_id"])
        self.assertNotEqual(new_membership, membership)
        self.assertEqual(new_membership.date_start, date(2026, 2, 1))
        self.assertEqual(new_membership.previous_membership_id, membership)
        self.assertEqual(new_membership.state, "active")

    def test_renewal_requires_active(self):
        membership = self._make_membership()
        with self.assertRaises(UserError):
            membership.action_renew()

    # ------------------------------------------------------------------
    # Cron
    # ------------------------------------------------------------------
    def test_cron_expires_finished_memberships(self):
        membership = self._make_membership(start=date(2020, 1, 1))
        membership.action_activate()
        count = self.env["club.membership"]._cron_expire_memberships()
        self.assertGreaterEqual(count, 1)
        self.assertEqual(membership.state, "expired")
