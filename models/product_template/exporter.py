# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component


class ProductInventoryExporter(Component):
    _name = "pos.product.template.inventory.exporter"
    _inherit = "pos.exporter"
    _apply_on = "pos.product.template"
    _usage = "inventory.exporter"

    def get_filter(self, template):
        binder = self.binder_for()
        pos_id = binder.to_external(template)
        return {"product_id": pos_id, "id": 0}

    def get_quantity_vals(self, template):
        vals = {
            "quantity": int(template.quantity),
        }
        return vals

    def run(self, template, fields):
        """Export the product inventory to Pos"""
        adapter = self.component(
            usage="backend.adapter", model_name="_import_stock_available"
        )
        filters = self.get_filter(template)
        quantity_vals = self.get_quantity_vals(template)
        adapter.export_quantity(filters, quantity_vals)
