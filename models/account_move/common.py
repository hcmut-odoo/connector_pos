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
        for move in self:
            if move.move_type != "out_invoice":
                continue
            sale_order = so_obj.search([("name", "=", move.invoice_origin)])
            if not sale_order:
                continue
            sale_order = sale_order[0]
            
            if sale_order.order_state == "exported":
                sale_order.with_delay().write({'order_state': 'delivering'})
            else:
                sale_order.with_delay().write({'order_state': 'confirmed'})

            pos_order_record = so_obj.search([("name", "=", move.invoice_origin)])
            if pos_order_record:
                backend_id = pos_order_record.backend_id
                self.env["pos.sale.order"].export_sale_state(backend_id, pos_order_record, "accept")

        # Check duplicate: posted journal entry must have an unique 
        # sequence number per company. problematic numbers
        condition = [('name', '=', self.name)]
        count = self.env['account.move'].search_count(condition)
        if count > 1 and self.name != "/":
            self.name = '/'
            self.env.cr.commit()

        result = super().action_post()        
        return result
    
    def auto_do_post_action(self):
        # Check duplicate: posted journal entry must have an unique 
        # sequence number per company. problematic numbers
        if self.state == "posted" or self.state == "cancel":
            return
        
        condition = [('name', '=', self.name)]
        count = self.env['account.move'].search_count(condition)
        if count > 1 and self.name != "/":
            self.name = '/'
            
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

            if sale_order.order_state != "canceled":
                sale_order.with_delay().write({'order_state': 'canceled'})

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
   