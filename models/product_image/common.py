# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import base64

from odoo import fields, models
from odoo.tools import config

from odoo.addons.component.core import Component

from ...components.backend_adapter import PrestaShopWebServiceImage


class ProductImage(models.Model):
    _inherit = "base_multi_image.image"

    pos_bind_ids = fields.One2many(
        comodel_name="pos.product.image",
        inverse_name="odoo_id",
        string="PrestaShop Bindings",
    )


class PosProductImage(models.Model):
    _name = "pos.product.image"
    _inherit = "pos.binding"
    _inherits = {"base_multi_image.image": "odoo_id"}
    _description = "Product image pos bindings"

    odoo_id = fields.Many2one(
        comodel_name="base_multi_image.image",
        required=True,
        ondelete="cascade",
        string="Product image",
    )

    def import_product_image(self, backend, product_tmpl_id, image_id, **kwargs):
        """Import a product image"""
        with backend.work_on(self._name) as work:
            importer = work.component(usage="record.importer")
            return importer.run(product_tmpl_id, image_id)


class ProductImageAdapter(Component):
    _name = "pos.product.image.adapter"
    _inherit = "pos.crud.adapter"
    _apply_on = "pos.product.image"
    _pos_image_model = "products"
    _pos_model = "products"

    def connect(self):
        debug = False
        if config["log_level"] == "debug":
            debug = True
        return PrestaShopWebServiceImage(
            self.pos.api_url, self.pos.webservice_key, debug=debug
        )

    def read(self, product_tmpl_id, image_id, options=None):
        api = self.connect()
        return api.get_image(
            self._pos_image_model, product_tmpl_id, image_id, options=options
        )
