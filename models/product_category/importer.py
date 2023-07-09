import datetime
import logging

from odoo import _

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import external_to_m2o, mapping

_logger = logging.getLogger(__name__)
try:
    from ....pospyt.pospyt import PosWebServiceError
except ImportError:
    _logger.debug("Cannot import from `pospyt`")


class ProductCategoryMapper(Component):
    """
    This class represents the mapper for importing POS product categories.
    It extends the base `pos.import.mapper` component.

    :param _model_name: The name of the model associated with the mapper 
    (`pos.product.category`).
    :type _model_name: str
    :param direct: The list of direct mappings between fields of the POS 
    category and the Odoo model.
    :type direct: list[tuple]
    """

    _name = "pos.product.category.import.mapper"
    _inherit = "pos.import.mapper"
    _apply_on = "pos.product.category"
    _model_name = "pos.product.category"

    direct = [
        ("description", "description"),
        ("link_rewrite", "link_rewrite"),
        ("meta_description", "meta_description"),
        ("meta_keywords", "meta_keywords"),
        ("meta_title", "meta_title"),
        (external_to_m2o("id_shop_default"), "default_shop_id"),
        ("active", "active"),
        ("position", "position"),
    ]

    @mapping
    def name(self, record):
        """
        Mapping function for the "name" field of the POS category.

        :param record: The record from the POS category data.
        :type record: dict
        :return: The mapped value for the "name" field in the Odoo model.
        :rtype: dict
        """
        if record["name"] is None:
            return {"name": ""}
        return {"name": record["name"]}

    @mapping
    def parent_id(self, record):
        """
        Mapping function for the "parent_id" field of the POS category.

        :param record: The record from the POS category data.
        :type record: dict
        :return: The mapped value for the "parent_id" field in the Odoo model.
        :rtype: dict
        """
        if record["id_parent"] == "0":
            return {}
        category = self.binder_for("pos.product.category").to_internal(
            record["id_parent"], unwrap=True
        )
        return {
            "parent_id": category.id,
        }

    @mapping
    def data_add(self, record):
        """
        Mapping function for the "date_add" field of the POS category.

        :param record: The record from the POS category data.
        :type record: dict
        :return: The mapped value for the "date_add" field in the Odoo model.
        :rtype: dict
        """
        if record["date_add"] == "0000-00-00 00:00:00":
            return {"date_add": datetime.datetime.now()}
        return {"date_add": record["date_add"]}

    @mapping
    def data_upd(self, record):
        """
        Mapping function for the "date_upd" field of the POS category.

        :param record: The record from the POS category data.
        :type record: dict
        :return: The mapped value for the "date_upd" field in the Odoo model.
        :rtype: dict
        """
        if record["date_upd"] == "0000-00-00 00:00:00":
            return {"date_upd": datetime.datetime.now()}
        return {"date_upd": record["date_upd"]}


class ProductCategoryImporter(Component):
    """
    This class represents the importer for POS product categories.
    It extends the base `pos.direct.batch.importer` component.

    :param _model_name: The name of the model associated with the importer 
    (`pos.product.category`).
    :type _model_name: str
    :param _translatable_fields: The dictionary specifying the translatable 
    fields and their corresponding models.
    :type _translatable_fields: dict
    """

    _name = "pos.product.category.importer"
    _inherit = "pos.direct.batch.importer"
    _apply_on = "pos.product.category"
    _model_name = "pos.product.category"

    _translatable_fields = {
        "pos.product.category": [
            "name",
            "description",
            "link_rewrite",
            "meta_description",
            "meta_keywords",
            "meta_title",
        ],
    }

    def _import_dependencies(self):
        """
        Internal method for importing dependencies of the POS category.

        This method imports the parent category if it exists.

        :raises PosWebServiceError: If there is an error while importing 
        the parent category.
        """
        pass
    

class ProductCategoryBatchImporter(Component):
    _name = "pos.product.category.delayed.batch.importer"
    _inherit = "pos.delayed.batch.importer"
    _apply_on = "pos.product.category"

    _model_name = "pos.product.category"

    direct = [
        ('description', 'description'),
    ]

    @mapping
    def name(self, record):
        if record['name']:
            return {'name': record['name']}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}