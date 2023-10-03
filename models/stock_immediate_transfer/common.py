# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import models

class StockImmediateTransfer(models.TransientModel):
    _inherit = 'stock.immediate.transfer'

    def process(self):
        stock_picking_ids = self.pick_ids
        for stock_picking in stock_picking_ids:
            sale_order = stock_picking.sale_id

            order_lines = sale_order.order_line
            for line in order_lines:
                product_id = line.product_id
                variant_barcode = product_id.barcode
                new_qty = product_id.qty_available - line.product_uom_qty
                self.with_delay(priority=300).export_pos_quantity(barcode=variant_barcode, new_qty=new_qty)
        
        result = super().process()
        return result

    def export_pos_quantity(self, barcode, new_qty):
        backend_records = self.env["pos.backend"].search([])
        for backend in backend_records:
            backend.backend_export_quantity(barcode=barcode, new_qty=new_qty)