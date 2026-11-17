# Part of Club Membership Management. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ClubMembership(models.Model):
    _name = "club.membership"
    _description = "Club Membership"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_start desc, id desc"

    name = fields.Char(
        default=lambda self: _("New"),
        copy=False,
        readonly=True,
        index=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Member",
        required=True,
        index=True,
        tracking=True,
    )
    plan_id = fields.Many2one(
        "club.membership.plan",
        string="Plan",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    date_start = fields.Date(
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    date_end = fields.Date(
        compute="_compute_date_end",
        store=True,
        readonly=False,
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("active", "Active"),
            ("expired", "Expired"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        copy=False,
        index=True,
        tracking=True,
    )
    price = fields.Monetary(
        compute="_compute_price",
        store=True,
        readonly=False,
        currency_field="currency_id",
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="plan_id.currency_id",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )
    previous_membership_id = fields.Many2one(
        "club.membership",
        string="Renewed From",
        readonly=True,
        copy=False,
        index=True,
    )
    invoice_ids = fields.One2many(
        "account.move",
        "club_membership_id",
        string="Invoices",
        readonly=True,
    )
    invoice_count = fields.Integer(compute="_compute_invoice_count")
    notes = fields.Html()

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.depends("date_start", "plan_id.period_months")
    def _compute_date_end(self):
        for membership in self:
            if membership.date_start and membership.plan_id.period_months:
                membership.date_end = (
                    membership.date_start
                    + relativedelta(months=membership.plan_id.period_months)
                    - relativedelta(days=1)
                )
            else:
                membership.date_end = membership.date_start

    @api.depends("plan_id")
    def _compute_price(self):
        for membership in self:
            membership.price = membership.plan_id.price

    def _compute_invoice_count(self):
        for membership in self:
            membership.invoice_count = len(membership.invoice_ids)

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for membership in self:
            if (
                membership.date_start
                and membership.date_end
                and membership.date_end < membership.date_start
            ):
                raise ValidationError(
                    _("The end date must be on or after the start date.")
                )

    @api.constrains("partner_id", "date_start", "date_end", "state")
    def _check_overlapping_memberships(self):
        for membership in self:
            if membership.state in ("cancelled", "expired"):
                continue
            if not (membership.date_start and membership.date_end):
                continue
            domain = [
                ("id", "!=", membership.id),
                ("partner_id", "=", membership.partner_id.id),
                ("state", "not in", ("cancelled", "expired")),
                ("date_start", "<=", membership.date_end),
                ("date_end", ">=", membership.date_start),
            ]
            if self.search_count(domain):
                raise ValidationError(
                    _(
                        "%(member)s already has a membership covering "
                        "%(start)s to %(end)s.",
                        member=membership.partner_id.display_name,
                        start=membership.date_start,
                        end=membership.date_end,
                    )
                )

    # ------------------------------------------------------------------
    # ORM
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("club.membership")
                    or _("New")
                )
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Business actions
    # ------------------------------------------------------------------
    def action_activate(self):
        for membership in self:
            if membership.state == "draft":
                membership.state = "active"
                membership.message_post(body=_("Membership activated."))
        return True

    def action_cancel(self):
        for membership in self:
            if membership.state != "cancelled":
                membership.state = "cancelled"
                membership.message_post(body=_("Membership cancelled."))
        return True

    def action_set_draft(self):
        for membership in self:
            if membership.state == "cancelled":
                membership.state = "draft"
        return True

    def _get_sale_journal(self):
        self.ensure_one()
        journal = self.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", self.company_id.id)],
            limit=1,
        )
        if not journal:
            raise UserError(
                _(
                    "No sales journal found for this company. "
                    "Install a chart of accounts before invoicing."
                )
            )
        return journal

    def _get_income_account(self):
        self.ensure_one()
        product = self.plan_id.product_id
        if product:
            account = (
                product.property_account_income_id
                or product.categ_id.property_account_income_categ_id
            )
            if account:
                return account
        account = self.env["account.account"].search(
            [("account_type", "=", "income")], limit=1
        )
        if not account:
            raise UserError(
                _(
                    "No income account found. Install a chart of accounts "
                    "before invoicing."
                )
            )
        return account

    def _prepare_invoice_vals(self):
        self.ensure_one()
        line = {
            "name": "%s (%s - %s)"
            % (self.plan_id.name, self.date_start, self.date_end),
            "quantity": 1.0,
            "price_unit": self.price,
            "account_id": self._get_income_account().id,
        }
        if self.plan_id.product_id:
            line["product_id"] = self.plan_id.product_id.id
        return {
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "invoice_date": fields.Date.context_today(self),
            "journal_id": self._get_sale_journal().id,
            "currency_id": self.currency_id.id,
            "club_membership_id": self.id,
            "invoice_line_ids": [(0, 0, line)],
        }

    def action_create_invoice(self):
        self.ensure_one()
        if self.state == "cancelled":
            raise UserError(_("You cannot invoice a cancelled membership."))
        existing = self.invoice_ids.filtered(lambda m: m.state != "cancel")
        if existing:
            raise UserError(
                _("This membership already has an invoice: %s", existing[0].name)
            )
        move = self.env["account.move"].create(self._prepare_invoice_vals())
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": move.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_renew(self):
        """Create the next period as a new membership, keeping history."""
        self.ensure_one()
        if self.state != "active":
            raise UserError(_("Only active memberships can be renewed."))
        new_start = self.date_end + relativedelta(days=1)
        new_membership = self.create(
            {
                "partner_id": self.partner_id.id,
                "plan_id": self.plan_id.id,
                "date_start": new_start,
                "price": self.plan_id.price,
                "previous_membership_id": self.id,
            }
        )
        new_membership.action_activate()
        new_membership.action_create_invoice()
        return {
            "type": "ir.actions.act_window",
            "res_model": "club.membership",
            "res_id": new_membership.id,
            "view_mode": "form",
            "target": "current",
        }

    # ------------------------------------------------------------------
    # Cron
    # ------------------------------------------------------------------
    @api.model
    def _cron_expire_memberships(self):
        today = fields.Date.context_today(self)
        expired = self.search(
            [("state", "=", "active"), ("date_end", "<", today)]
        )
        if expired:
            expired.write({"state": "expired"})
            for membership in expired:
                membership.message_post(
                    body=_("Membership expired automatically.")
                )
        return len(expired)

    def action_view_invoices(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Invoices"),
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("club_membership_id", "=", self.id)],
            "context": {
                "default_move_type": "out_invoice",
                "default_club_membership_id": self.id,
            },
        }
