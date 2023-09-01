# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping


class SaleOrderStateMapper(Component):
    _name = "pos.sale.order.state.mapper"
    _inherit = "pos.import.mapper"
    _apply_on = "pos.sale.order.state"

    direct = [
        ("name", "name"),
    ]

    @mapping
    def company_id(self, record):
        return {"company_id": self.backend_record.company_id.id}


class SaleOrderStateImporter(Component):
    """Import one translatable record"""

    _name = "pos.sale.order.state.importer"
    _inherit = "pos.importer"
    _apply_on = "pos.sale.order.state"

    _translatable_fields = {
        "pos.sale.order.state": [
            "name",
        ],
    }


class SaleOrderStateBatchImporter(Component):
    _name = "pos.sale.order.state.batch.importer"
    _inherit = "pos.direct.batch.importer"
    _apply_on = "pos.sale.order.state"
