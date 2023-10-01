# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component


class VariantInventoryExporter(Component):
    _name = "pos.product.variant.inventory.exporter"
    _inherit = "pos.product.template.inventory.exporter"
    _apply_on = "pos.product.variant"

    def get_filter(self, product):
        return {
            "product_id": product.main_template_id.pos_id,
            "id": product.pos_id,
        }

    def get_quantity_vals(self, product):
        vals = {
            "quantity": int(product.quantity),
        }
        return vals
