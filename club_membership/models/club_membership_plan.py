# Part of Club Membership Management. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ClubMembershipPlan(models.Model):
    _name = "club.membership.plan"
    _description = "Club Membership Plan"
    _order = "price, name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, copy=False)
    price = fields.Monetary(
        currency_field="currency_id",
        required=True,
        help="Amount invoiced for one full period of this plan.",
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    billing_period = fields.Selection(
        selection=[
            ("month", "Monthly"),
            ("quarter", "Quarterly"),
            ("year", "Yearly"),
        ],
        default="month",
        required=True,
    )
    period_months = fields.Integer(
        compute="_compute_period_months",
        store=True,
        readonly=True,
        help="Number of months covered by one billing period.",
    )
    product_id = fields.Many2one(
        "product.product",
        domain=[("type", "=", "service")],
        help="Optional product used on the generated invoice line.",
    )
    description = fields.Text()
    active = fields.Boolean(default=True)
    membership_count = fields.Integer(compute="_compute_membership_count")

    @api.depends("billing_period")
    def _compute_period_months(self):
        mapping = {"month": 1, "quarter": 3, "year": 12}
        for plan in self:
            plan.period_months = mapping.get(plan.billing_period, 1)

    def _compute_membership_count(self):
        Membership = self.env["club.membership"]
        for plan in self:
            plan.membership_count = Membership.search_count(
                [("plan_id", "=", plan.id)]
            )
