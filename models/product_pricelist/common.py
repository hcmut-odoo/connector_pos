# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models

from odoo.addons.component.core import Component


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    pos_groupos_bind_ids = fields.One2many(
        comodel_name="pos.groups.pricelist",
        inverse_name="odoo_id",
        string="Pos user groups",
    )


class PosGroupsPricelist(models.Model):
    _name = "pos.groups.pricelist"
    _inherit = "pos.binding.odoo"
    _inherits = {"product.pricelist": "odoo_id"}
    _description = "Group pricelist pos bindings"

    odoo_id = fields.Many2one(
        comodel_name="product.pricelist",
        required=True,
        ondelete="cascade",
        string="Odoo Pricelist",
    )


class PricelistAdapter(Component):
    _name = "pos.groups.pricelist.adapter"
    _inherit = "pos.adapter"
    _apply_on = "pos.groups.pricelist"
    _pos_model = "product"
