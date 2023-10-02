# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo.addons.component.core import Component
from ...components.backend_adapter import retryable_error
from ....pospyt.pospyt import (
    PosWebservice,
    PosWebServiceDict,
    PosWebServiceError
)

class ProductQuantityExporter(Component):
    _name = "pos.product.variant.exporter"
    _inherit = "pos.exporter"
    _apply_on = ["pos.product.variant"]
    _usage = "product.quantity.exporter"

    def run(self, barcode, new_qty, **kwargs):
        try:
            response = self.backend_adapter.update_new_quantity(barcode=barcode, new_qty=new_qty)
            sussess = response.get("success")
            data = response.get("data")
            if not sussess:
                message = data.get("variant_barcode")
                if message[0] == "The selected variant barcode is invalid.":
                    backend = kwargs.get("backend")
                    pos_product_variant = self.env["pos.product.product"].search([("variant_barcode", "=", barcode)])
                    warehouse_record = self.env["stock.warehouse"].search([("id", "=", backend.warehouse_id.id)])
                    stock_record = self.env["stock.quant"].search([
                        ("product_id", "=", pos_product_variant.odoo_id.id),
                        ("location_id","=", warehouse_record.lot_stock_id.id)]
                    )
                    data = {
                        "product_id": pos_product_variant.main_template_id.id,
                        "variant_barcode": barcode,
                        "size": pos_product_variant.size,
                        "extend_price": pos_product_variant.odoo_id.impact_price,
                        "stock_qty": stock_record.quantity
                    }

                    self.export_variant(data=data, backend=backend)
        
        except Exception as e:
            print("Response: ", e)

    def export_variant(self, data, **kwargs):
        try:
            backend = kwargs.get("backend")
            response = self.backend_adapter.export_new_variant(data=data, backend=backend)
            sussess = response.get("success")
            data = response.get("data")
            if not sussess:
                message = data.get("product_id")
                if message[0] == "The selected product id is invalid.":
                    pos_product_template_id = data["product_id"]
                    pos_product_template = self.env["pos.product.template"].search([
                        ("pos_id", "=", pos_product_template_id),
                        ("backend_id", "=", backend.id)
                    ])

                    odoo_category_id = pos_product_template.odoo_id.categ_id
                    pos_product_category =  self.env["pos.product.category"].search([
                        ("odoo_id", "=", odoo_category_id),
                        ("backend_id", "=", backend.id)
                    ])
        
                    if pos_product_template:
                        template_data = {
                            "name": pos_product_template.odoo_id.name,
                            "price": pos_product_template.odoo_id.list_price,
                            "description": pos_product_template.description,
                            "image_url": pos_product_template.image_url,
                            "category_id": pos_product_category.pos_id
                        }

                        self.env["pos.product.template"].with_delay(priority=50).export_product_template(backend=backend, data=template_data)

        except Exception as e:
            print("Response: ", e) 