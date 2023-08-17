# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models

from odoo.addons.component.core import Component


class SaleOrderState(models.Model):
    _name = "sale.order.state"
    _description = "Sale Order States"

    name = fields.Char("Name", translate=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
    )
    pos_bind_ids = fields.One2many(
        comodel_name="pos.sale.order.state",
        inverse_name="odoo_id",
        string="Pos Bindings",
    )


class PosSaleOrderState(models.Model):
    _name = "pos.sale.order.state"
    _inherit = "pos.binding.odoo"
    _inherits = {"sale.order.state": "odoo_id"}
    _description = "Sale order state pos bindings"

    openerp_state_ids = fields.One2many(
        comodel_name="sale.order.state.list",
        inverse_name="pos_state_id",
        string="Odoo States",
    )
    odoo_id = fields.Many2one(
        comodel_name="sale.order.state",
        required=True,
        ondelete="cascade",
        string="Sale Order State",
    )


class SaleOrderStateList(models.Model):
    _name = "sale.order.state.list"
    _description = "Sale Order State List"

    name = fields.Selection(
        selection=[
            ("draft", "Quotation"),
            ("sent", "Quotation Sent"),
            ("sale", "Sales Order"),
            ("done", "Locked"),
            ("cancel", "Cancelled"),
        ],
        string="Odoo State",
        required=True,
    )
    pos_state_id = fields.Many2one(
        comodel_name="pos.sale.order.state",
        string="Pos State",
    )
    pos_id = fields.Integer(
        related="pos_state_id.pos_id",
        readonly=True,
        store=True,
        string="Pos ID",
    )


class SaleOrderStateAdapter(Component):
    _name = "pos.sale.order.state.adapter"
    _inherit = "pos.adapter"
    _apply_on = "pos.sale.order.state"
    _pos_model = "order"
