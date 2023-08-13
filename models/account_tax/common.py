# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models

from odoo.addons.component.core import Component


class PosAccountTax(models.Model):
    _name = "pos.account.tax"
    # Do not inherit from `pos.binding.odoo`
    # because we do not want the constraint `pos_erp_uniq`.
    # This allows us to create duplicated taxes.
    _inherit = "pos.binding"
    _inherits = {"account.tax": "odoo_id"}
    _description = "Acccount Tax Pos Bindings"

    odoo_id = fields.Many2one(
        comodel_name="account.tax",
        string="Tax",
        required=True,
        ondelete="cascade",
    )


class AccountTax(models.Model):
    _inherit = "account.tax"

    pos_bind_ids = fields.One2many(
        comodel_name="pos.account.tax",
        inverse_name="odoo_id",
        string="pos Bindings",
        readonly=True,
    )


class AccountTaxAdapter(Component):
    _name = "pos.account.tax.adapter"
    _inherit = "pos.adapter"
    _apply_on = "pos.account.tax"

    _model_name = "pos.account.tax"
    _pos_model = "taxes"
