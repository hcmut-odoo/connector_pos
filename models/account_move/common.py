# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

from odoo.addons.component.core import Component



class AccountMove(models.Model):
    _inherit = "account.move"

    pos_bind_ids = fields.One2many(
        comodel_name="pos.refund",
        inverse_name="odoo_id",
        string="Pos Bindings",
    )

    def action_post(self):
        so_obj = self.env["pos.sale.order"]
        line_replacement = {}
        for move in self:
            if move.move_type != "out_invoice":
                continue
            sale_order = so_obj.search([("name", "=", move.invoice_origin)])
            if not sale_order:
                continue
            sale_order = sale_order[0]
            discount_product_id = sale_order.backend_id.discount_product_id.id
            for invoice_line in move.invoice_line_ids:
                if invoice_line.product_id.id != discount_product_id:
                    continue
                amount = invoice_line.price_subtotal
                partner = move.partner_id.commercial_partner_id
                refund = self._find_refund(-1 * amount, partner)
                if refund:
                    invoice_line.unlink()
                    line_replacement[move] = refund

            pos_order_record = so_obj.search([("name", "=", move.invoice_origin)])
            if pos_order_record:
                backend_id = pos_order_record.backend_id
                self.env["pos.sale.order"].export_sale_state(backend_id, pos_order_record, "accept")

        result = super().action_post()        
        return result
    
    def button_draft(self):
        result = super().button_draft()        
        return result
    
    def button_cancel(self):
        so_obj = self.env["pos.sale.order"]
        line_replacement = {}
        for move in self:
            if move.move_type != "out_invoice":
                continue
            sale_order = so_obj.search([("name", "=", move.invoice_origin)])
            if not sale_order:
                continue
            sale_order = sale_order[0]
            discount_product_id = sale_order.backend_id.discount_product_id.id
            for invoice_line in move.invoice_line_ids:
                if invoice_line.product_id.id != discount_product_id:
                    continue
                amount = invoice_line.price_subtotal
                partner = move.partner_id.commercial_partner_id
                refund = self._find_refund(-1 * amount, partner)
                if refund:
                    invoice_line.unlink()
                    line_replacement[move] = refund

            pos_order_record = so_obj.search([("name", "=", move.invoice_origin)])
            if pos_order_record:
                backend_id = pos_order_record.backend_id
                self.env["pos.sale.order"].export_sale_state(backend_id, pos_order_record, "reject")

        result = super().button_cancel()        
        return result


class PosRefund(models.Model):
    _name = "pos.refund"
    _inherit = "pos.binding.odoo"
    _inherits = {"account.move": "odoo_id"}
    _description = "Refund Prestshop Bindings"

    odoo_id = fields.Many2one(
        comodel_name="account.move",
        required=True,
        ondelete="cascade",
        string="Invoice",
    )    


class RefundAdapter(Component):
    _name = "pos.refund.adapter"
    _inherit = "pos.adapter"
    _apply_on = "pos.refund"
   