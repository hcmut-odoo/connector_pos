# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import datetime
import logging

from odoo import _

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import (
    external_to_m2o,
    mapping,
    only_create,
)

from ...utils.datetime import (
    format_date_string,
    parse_date_string
)

_logger = logging.getLogger(__name__)


class PaymentModeImportMapper(Component):
    _name = "pos.payment.mode.mapper"
    _inherit = "pos.import.mapper"
    _apply_on = "pos.payment.mode"

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


class PaymentModeImporter(Component):
    _name = "pos.payment.mode.importer"
    _inherit = "pos.importer"
    _apply_on = "payment.mode"


class PaymentModeBatchImporter(Component):
    _name = "pos.payment.mode.batch.importer"
    _inherit = "pos.delayed.batch.importer"
    _apply_on = "pos.payment.mode"

    _model_name = "pos.payment.mode"

    direct = [
        ('name', 'name'),
    ]

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}