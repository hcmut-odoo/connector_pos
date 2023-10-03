from odoo.addons.component.core import Component
from ...components.backend_adapter import retryable_error
from ....pospyt.pospyt import (
    PosWebservice,
    PosWebServiceDict,
    PosWebServiceError
)

class ProductCategoryExporter(Component):
    _name = "pos.product.category.exporter"
    _inherit = "pos.exporter"
    _apply_on = ["pos.product.category"]
    _usage = "product.category.exporter"   

    def export_category(self, data, *kwargs):
        try:
            response = self.backend_adapter.update_new_category(data=data)
        except Exception as e:
            print("Response:", e)