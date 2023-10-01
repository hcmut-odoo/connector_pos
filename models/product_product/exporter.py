# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo.addons.component.core import Component


class ProductQuantityExporter(Component):
    _name = "pos.product.variant.exporter"
    _inherit = "pos.exporter"
    _apply_on = ["pos.product.variant"]
    _usage = "product.quantity.exporter"

    def run(self, barcode, new_qty, **kwargs):
        datas = {
            'barcode': barcode,
            'new_qty': new_qty
        }

        self.backend_adapter.update_new_quantity(datas)
