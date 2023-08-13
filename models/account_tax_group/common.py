# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models

from odoo.addons.component.core import Component


class AccountTaxGroup(models.Model):
    _inherit = "account.tax.group"

    pos_bind_ids = fields.One2many(
        comodel_name="pos.account.tax.group",
        inverse_name="odoo_id",
        string="Pos Bindings",
        readonly=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        index=True,
        string="Company",
    )
    tax_ids = fields.One2many(
        comodel_name="account.tax",
        inverse_name="tax_group_id",
        string="Taxes",
    )


class PosAccountTaxGroup(models.Model):
    _name = "pos.account.tax.group"
    # Since the pos tax group change its ID when updated we could
    # end up with multiple tax group binding with the same backend_id/odoo_id
    # that is why we do not inherit pos.odoo.binding
    _inherit = "pos.binding"
    _inherits = {"account.tax.group": "odoo_id"}
    _description = "Account Tax Group Pos Bindings"

    odoo_id = fields.Many2one(
        comodel_name="account.tax.group",
        string="Tax Group",
        required=True,
        ondelete="cascade",
    )


class TaxGroupAdapter(Component):
    _name = "pos.account.tax.group.adapter"
    _inherit = "pos.adapter"
    _apply_on = "pos.account.tax.group"

    _model_name = "pos.account.tax.group"
    _pos_model = "tax_rule_groups"

    def search(self, filters=None):
        if filters is None:
            filters = {}
        filters["filter[deleted]"] = 0
        return super().search(filters)
