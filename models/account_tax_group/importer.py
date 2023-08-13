# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create


class TaxGroupMapper(Component):
    _name = "pos.account.tax.group.import.mapper"
    _inherit = "pos.import.mapper"
    _apply_on = "pos.account.tax.group"

    _model_name = "pos.account.tax.group"

    direct = [
        ("name", "name"),
    ]

    @mapping
    def backend_id(self, record):
        return {"backend_id": self.backend_record.id}

    @mapping
    def company_id(self, record):
        return {"company_id": self.backend_record.company_id.id}

    @only_create
    @mapping
    def odoo_id(self, record):
        tax_group = self.env["account.tax.group"].search(
            [("name", "=", record["name"])]
        )
        if tax_group:
            return {"odoo_id": tax_group.id}


class TaxGroupImporter(Component):
    _name = "pos.account.tax.group.importer"
    _inherit = "pos.importer"
    _apply_on = "pos.account.tax.group"


#     _model_name = 'pos.account.tax.group'


class TaxGroupBatchImporter(Component):
    _name = "pos.account.tax.group.direct.batch.importer"
    _inherit = "pos.direct.batch.importer"
    _apply_on = "pos.account.tax.group"


#     _model_name = 'pos.account.tax.group'
