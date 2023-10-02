# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models, api    

from odoo.addons.component.core import Component
from odoo.tests import Form

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def create(self, vals):
        product_id = vals['product_id']
        inventory_quantity = vals['inventory_quantity']

        product = self.env["product.product"].browse(product_id)
        variant_barcode = product.barcode

        print("StockQuant create", product_id, inventory_quantity, variant_barcode)
        self.with_delay(priority=300).export_pos_quantity(barcode=variant_barcode, new_qty=inventory_quantity)
        return super().create(vals)

    def write(self, vals):
        product_id = vals['product_id']
        inventory_quantity = vals['inventory_quantity']

        product = self.env["product.product"].browse(product_id)
        variant_barcode = product.barcode

        print("StockQuant write", product_id, inventory_quantity, variant_barcode)
        self.with_delay(priority=300).export_pos_quantity(barcode=variant_barcode, new_qty=inventory_quantity)
        return super().write(vals)

    def export_pos_quantity(self, barcode, new_qty):
        print("export_pos_quantity")
        backend_records = self.env["pos.backend"].search([])
        print("backend_records", backend_records)
        for backend in backend_records:
            backend.backend_export_quantity(barcode=barcode, new_qty=new_qty)