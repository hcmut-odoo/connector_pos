# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from datetime import timedelta

from ....pospyt.pospyt import PosWebServiceDict

from odoo import api, fields, models

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class AccountPaymentMode(models.Model):
    _inherit = "account.payment.mode"

    pos_bind_ids = fields.One2many(
        comodel_name="pos.payment.mode",
        inverse_name="odoo_id",
        string="Pos Bindings",
    )


class PosPaymentMode(models.Model):
    _name = "pos.payment.mode"
    _inherit = "pos.binding.odoo"
    _inherits = {"payment.mode": "odoo_id"}
    _description = "Payment mode pos bindings"

    odoo_id = fields.Many2one(
        comodel_name="sale.order",
        string="Sale Order",
        required=True,
        ondelete="cascade",
    )
    
    def import_payment_modes_since(self, backend_record, since_date=None, **kwargs):
        """Prepare the import of payment modes on Pos"""
        now_fmt = fields.Datetime.now()
        since_date = backend_record.import_payment_mode_since
        if since_date:
            filters={'date': {'start': since_date}, 'action': 'list'}
        else:
            filters={'date': {'end': now_fmt}, 'action': 'list'}

        self.env["pos.payment.mode"].import_batch(
            backend=backend_record, filters=filters, priority=15, **kwargs
        )

        backend_record.import_payment_mode_since = now_fmt
        return True


class PaymentModeAdapter(Component):
    _name = "payment.mode.adapter"
    _inherit = "pos.adapter"
    _apply_on = "payment.mode"

    _model_name = "payment.mode"
    _pos_model = "payment"
    _export_node_name = "payment"