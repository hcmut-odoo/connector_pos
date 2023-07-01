# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tools.translate import _

from odoo.addons.component.core import AbstractComponent


class PosDeleter(AbstractComponent):
    """Base deleter for Pos"""

    _name = "pos.deleter"
    _inherit = "base.deleter"
    _usage = "record.exporter.deleter"

    def run(self, external_id, attributes=None):
        """Run the synchronization, delete the record on Pos

        :param external_id: identifier of the record to delete
        """
        resource = self.backend_adapter._pos_model
        self.backend_adapter.delete(resource, external_id, attributes)
        return _("Record %s deleted on Pos on resource %s") % (
            external_id,
            resource,
        )
