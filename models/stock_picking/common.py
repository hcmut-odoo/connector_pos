# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models

from odoo.addons.component.core import Component


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        sale_order = self.sale_id
        order_lines = sale_order.order_line

        super().button_validate()
        for line in order_lines:
            product_id = line.product_id
            # pos_product_variant = self.env["pos.product.variant"].search([("odoo_id", "=", product_id.id)])
            variant_barcode = product_id.barcode
            new_qty = product_id.qty_avaiable
            self.with_delay(priority=300).export_pos_quantity(barcode=variant_barcode, new_qty=new_qty)

        print("button_validate order_line", sale_order.order_line)
    
    def export_pos_quantity(self, barcode, new_qty):
        backend_records = self.env["pos.backend"].browse()
        for backend in backend_records:
            backend.with_delay(priority=30).backend_export_quantity(barcode=barcode, new_qty=new_qty)