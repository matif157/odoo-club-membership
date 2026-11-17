# Part of Club Membership Management. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    club_membership_id = fields.Many2one(
        "club.membership",
        string="Club Membership",
        ondelete="set null",
        index=True,
        copy=False,
    )
