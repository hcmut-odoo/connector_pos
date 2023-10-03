from odoo.addons.component.core import Component
from ...components.backend_adapter import retryable_error
from ....pospyt.pospyt import (
    PosWebservice,
    PosWebServiceDict,
    PosWebServiceError
)

class ProductTemplateExporter(Component):
    _name = "pos.product.template.exporter"
    _inherit = "pos.exporter"
    _apply_on = ["pos.product.template"]
    _usage = "product.template.exporter"   

    def export_template(self, data, *kwargs):

        try:
            backend = kwargs.get("backend")
            response = self.backend_adapter.update_new_template(data=data)
            status = response.get("success")
            response = response.get("data")
            if not status:
                message = response.get("category_id")
                if message[0] == "The selected category id is invalid.":
                    pos_product_category =  self.env["pos.product.category"].search([
                        ("pos_id", "=", data["category_id"]),
                        ("backend_id", "=", backend.id)
                    ])
        
                    if pos_product_category:
                        category_data = {
                            "name": pos_product_category.odoo_id.name
                        }

                        self.env["pos.product.category"].with_delay(priority=20).export_product_category(backend=backend, data=category_data) 
        except Exception as e:
            print("Response:", e)