# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.component.core import AbstractComponent
from odoo.addons.connector.components.mapper import mapping


class PosImportMapper(AbstractComponent):
    """
    Mapper component for importing data into the Point of Sale (POS) module.

    This component is responsible for mapping external records to the corresponding 
    internal records in the POS module during the import process. It inherits 
    from `base.pos.connector` and `base.import.mapper`.

    :ivar _name: Name of the component.
    :vartype _name: str
    :ivar _inherit: Inherited components.
    :vartype _inherit: list[str]
    :ivar _usage: Usage of the component.
    :vartype _usage: str
    """

    _name = "pos.import.mapper"
    _inherit = ["base.pos.connector", "base.import.mapper"]
    _usage = "import.mapper"

    @mapping
    def backend_id(self, record):
        """
        Map the backend ID.

        This method maps the backend ID of the record to be imported.

        :param record: External record to be imported.
        :type record: any
        :return: Mapped backend ID.
        :rtype: dict
        """
        return {"backend_id": self.backend_record.id}

class PosExportMapper(AbstractComponent):
    """
    Mapper component for exporting data from the Point of Sale (POS) module.

    This component is responsible for mapping internal records in the POS module 
    to their corresponding external representation during the export process. 
    It inherits from `base.pos.connector` and `base.export.mapper`.

    :ivar _name: Name of the component.
    :vartype _name: str
    :ivar _inherit: Inherited components.
    :vartype _inherit: list[str]
    :ivar _usage: Usage of the component.
    :vartype _usage: str
    """

    _name = "pos.export.mapper"
    _inherit = ["base.pos.connector", "base.export.mapper"]
    _usage = "export.mapper"

    def _map_direct(self, record, from_attr, to_attr):
        """
        Map the attribute directly.

        This method maps the attribute directly from the internal record to the 
        external record during export.

        :param record: Internal record to be exported.
        :type record: any
        :param from_attr: Name of the attribute in the internal record.
        :type from_attr: str
        :param to_attr: Name of the attribute in the external record.
        :type to_attr: str
        :return: Mapped value for the attribute.
        :rtype: any
        """
        res = super()._map_direct(record, from_attr, to_attr) or ""
        if not isinstance(from_attr, str):
            return res
        column = self.model.fields_get()[from_attr]
        if column["type"] == "boolean":
            return res and 1 or 0
        elif column["type"] == "float":
            set_precision = False
            # We've got column so from_attr is already in self.model._fields
            if isinstance(res, (float, int)):
                # force float precision:
                digits = column["digits"]
                if digits and isinstance(digits[1], int):
                    # Any reason we need more than 12 decimals?
                    fmt = "{:." + str(max(digits[1], 12)) + "f}"
                    res = fmt.format(res)
                    set_precision = True
            if not set_precision:
                res = str(res)
        return res