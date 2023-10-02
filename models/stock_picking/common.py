# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models

from odoo.addons.component.core import Component
from odoo.tests import Form

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        sale_order = self.sale_id
        order_lines = sale_order.order_line

        
        for line in order_lines:
            product_id = line.product_id
            variant_barcode = product_id.barcode
            new_qty = product_id.qty_available - line.product_uom_qty
            self.with_delay().export_pos_quantity(barcode=variant_barcode, new_qty=new_qty)

        # stock_pickings = sale_order.picking_ids
        # for stock_picking in stock_pickings:
        #     stock_picking.immediate_transfer = True

        result = super().button_validate()
        
        # stock_picking_ids = [record.id for record in stock_pickings]
        # stock_immediate_transfer_obj = self.env["stock.immediate.transfer"]
        # stock_immediate_transfer_ids = stock_immediate_transfer_obj.search([('pick_ids', 'in', stock_picking_ids)])
        # for stock_immediate_transfer_id in stock_immediate_transfer_ids:
        #     print("stock_immediate_transfer_id", stock_immediate_transfer_id)
        #     stock_immediate_transfer_id.process()

        return result
    
    def export_pos_quantity(self, barcode, new_qty):
        print("export_pos_quantity")
        backend_records = self.env["pos.backend"].search([])
        print("backend_records", backend_records)
        for backend in backend_records:
            backend.backend_export_quantity(barcode=barcode, new_qty=new_qty)