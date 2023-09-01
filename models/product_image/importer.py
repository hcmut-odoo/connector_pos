# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


import logging
import mimetypes

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping

_logger = logging.getLogger(__name__)
try:
    from pospyt import PosWebServiceError
except ImportError:
    _logger.debug("Cannot import from `pospyt`")


class ProductImageMapper(Component):
    _name = "pos.product.image.import.mapper"
    _inherit = "pos.import.mapper"
    _apply_on = "pos.product.image"

    _model_name = "pos.product.image"


    @mapping
    def from_template(self, record):
        binder = self.binder_for("pos.product.template")
        template = binder.to_internal(record["id_product"], unwrap=True)
        name = "{}_{}".format(template.name, record["id_image"])
        return {"owner_id": template.id, "name": name}

    @mapping
    def backend_id(self, record):
        return {"backend_id": self.backend_record.id}

    @mapping
    def extension(self, record):
        return {"extension": mimetypes.guess_extension(record["type"])}

    @mapping
    def image_url(self, record):
        return {"url": record["full_public_url"]}

    @mapping
    def filename(self, record):
        return {"filename": "%s.jpg" % record["id_image"]}

    @mapping
    def storage(self, record):
        return {"storage": "url"}

    @mapping
    def owner_model(self, record):
        return {"owner_model": "product.template"}


class ProductImageImporter(Component):
    _name = "pos.product.image.importer"
    _inherit = "pos.importer"
    _apply_on = "pos.product.image"

    def _get_pos_data(self):
        """Return the raw Pos data for ``self.pos_id``"""
        adapter = self.component(usage="backend.adapter", model_name=self.model._name)
        return adapter.read(self.template_id, self.image_id)

    def run(self, template_id, image_id, **kwargs):
        self.template_id = template_id
        self.image_id = image_id
        binder = self.binder_for("pos.product.template")
        product_tmpl = binder.to_internal(template_id, unwrap=True)

        try:
            super().run(image_id, **kwargs)
        except PosWebServiceError:
            # TODO add activity to warn about he failure
            if product_tmpl:
                pass

        if str(product_tmpl.default_image_id) != str(image_id):
            return
        self.binder_for("pos.product.image")
        image = binder.to_internal(image_id, unwrap=True)
        product_tmpl.image_1920 = image.image_main
