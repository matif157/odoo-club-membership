{
    "name": "Club Membership Management",
    "version": "19.0.1.0.0",
    "category": "Services",
    "summary": "Memberships, recurring billing and renewals for clubs, gyms and academies",
    "description": """
Club Membership Management
==========================

A real, installable Odoo 19 module for membership businesses: gyms, snooker clubs,
coaching academies, physiotherapy clinics and co-working spaces.

Features
--------
* Membership plans with monthly / quarterly / yearly billing periods
* Automatic end-date calculation
* One-click invoice creation (account.move, out_invoice)
* Renewal that keeps history (new membership linked to the previous one)
* Overlap protection: a member cannot hold two active memberships at once
* Daily cron that expires finished memberships
* Chatter tracking on every membership
* User and Manager security groups with record-level access
""",
    "author": "Muhammad Atif",
    "website": "https://github.com/matif157/odoo-club-membership",
    "license": "LGPL-3",
    "depends": [
        "base",
        "account",
        "mail",
    ],
    "data": [
        "security/club_security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "data/ir_cron.xml",
        "views/club_membership_plan_views.xml",
        "views/club_membership_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
