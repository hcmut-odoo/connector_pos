# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

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


class PartnerImportMapper(Component):
    _name = "pos.res.partner.mapper"
    _inherit = "pos.import.mapper"
    _apply_on = "pos.res.partner"

    direct = [
        ("address", "city"),
        ("email", "email"),
        ("company", "company"),
        ("active", "active"),
        ("note", "comment"),
    ]

    @mapping
    def is_company(self, record):
        if record.get("company"):
            return {"is_company": True}
        return {"is_company": False}

    @mapping
    def name(self, record):
        if record["name"] is None:
            return {"name": ""}
        return {"name": record["name"]}

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

    @mapping
    def company_id(self, record):
        return {"company_id": self.backend_record.company_id.id}
    
    @mapping
    def phone(self, record):
        if record["phone_number"] is None:
            return {"phone": ""}
        return {"phone": record["phone_number"]}


class ResPartnerImporter(Component):
    _name = "pos.res.partner.importer"
    _inherit = "pos.importer"
    _apply_on = "pos.res.partner"

    def _import_dependencies(self):
        pass

    def _after_import(self, binding):
        pass

    def _has_to_skip (self, binding):
        pos_user_record = self.pos_record
        rp_obj = self.env["res.partner"]

        # Search for a partner by email or phone
        email = pos_user_record["email"]
        phone = pos_user_record["phone_number"]
        partner_mapped = rp_obj.search(['|', ("email", "=", email), ("phone", "=", phone)])

        
        if partner_mapped:
            return True
        
        return False


class PartnerBatchImporter(Component):
    _name = "pos.res.partner.batch.importer"
    _inherit = "pos.delayed.batch.importer"
    _apply_on = "pos.res.partner"

    _model_name = "pos.res.partner"

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


class AddressImportMapper(Component):
    _name = "pos.address.mappper"
    _inherit = "pos.import.mapper"
    _apply_on = "pos.address"

    direct = [
        ("address", "street")
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
    
    @mapping
    def phone(self, record):
        if record["phone_number"] is None:
            return {"phone": ""}
        return {"phone": record["phone_number"]}
    
    @mapping
    def backend_id(self, record):
        return {"backend_id": self.backend_record.id}


class AddressImporter(Component):
    _name = "pos.address.importer"
    _inherit = "pos.importer"
    _apply_on = "pos.address"

    def run(self, pos_id, **kwargs):
        if "address_type" in kwargs:
            self._address_type = kwargs.pop("address_type")
        # else: let mapper to set default value
        super().run(pos_id, **kwargs)

    def _map_data(self):
        map_record = super()._map_data()
        try:
            map_record.source["address_type"] = self._address_type
        except AttributeError:  # pragma: no cover
            pass  # let mapper to set default value
        return map_record

    def _check_vat(self, vat_number, partner_country):
        vat_country, vat_number_ = self.env["res.partner"]._split_vat(vat_number)
        if not self.env["res.partner"].simple_vat_check(vat_country, vat_number_):
            # if fails, check with country code from country
            country_code = partner_country.code
            if country_code:
                if not self.env["res.partner"].simple_vat_check(
                    country_code.lower(), vat_number
                ):
                    return False
        return True

    def _after_import(self, binding):
        record = self.pos_record
        vat_number = None
        if record["vat_number"]:
            vat_number = record["vat_number"].replace(".", "").replace(" ", "")
        # TODO move to custom localization module
        elif not record["vat_number"] and record.get("dni"):
            vat_number = (
                record["dni"].replace(".", "").replace(" ", "").replace("-", "")
            )
        if vat_number:
            if self._check_vat(vat_number, binding.odoo_id.country_id):
                binding.parent_id.write({"vat": vat_number})
            else:
                msg = _("Please, check the VAT number: %s") % vat_number
                # TODO create activity to warn the vat is incorrect ?
                _logger.warn(msg)


class AddressBatchImporter(Component):
    _name = "pos.address.batch.importer"
    _inherit = "pos.delayed.batch.importer"
    _apply_on = "pos.address"

