import datetime
import logging

from odoo import _

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import external_to_m2o, mapping

from ...utils.datetime import (
    format_date_string,
    parse_date_string
)

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
        ("name", "name")
    ]

    @mapping
    def data_add(self, record):
        """
        Mapping function for the "date_add" field of the POS category.

        :param record: The record from the POS category data.
        :type record: dict
        :return: The mapped value for the "date_add" field in the Odoo model.
        :rtype: dict
        """
        if record["created_at"] is None or record["created_at"] == "0000-00-00 00:00:00":
            date_add = datetime.datetime.now()
        else:
            date_add = parse_date_string(record["created_at"])

        return {"date_add": format_date_string(date_add)}

    @mapping
    def data_upd(self, record):
        """
        Mapping function for the "date_upd" field of the POS category.

        :param record: The record from the POS category data.
        :type record: dict
        :return: The mapped value for the "date_upd" field in the Odoo model.
        :rtype: dict
        """
        if record["updated_at"] is None or record["updated_at"] == "0000-00-00 00:00:00":
            date_upd = datetime.datetime.now()
        else:
            date_upd = parse_date_string(record["updated_at"])

        return {"date_upd": format_date_string(date_upd)}


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
    _inherit = "pos.importer"
    _apply_on = "pos.product.category"
    _model_name = "pos.product.category"

    def _import_dependencies(self):
        """
        Internal method for importing dependencies of the POS category.

        This method imports the parent category if it exists.

        :raises PosWebServiceError: If there is an error while importing 
        the parent category.
        """
        pass

    def _after_import(self, binding):
        pass
    

class ProductCategoryBatchImporter(Component):
    _name = "pos.product.category.delayed.batch.importer"
    _inherit = "pos.delayed.batch.importer"
    _apply_on = "pos.product.category"

    _model_name = "pos.product.category"