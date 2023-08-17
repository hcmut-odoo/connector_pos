# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from datetime import timedelta

from pospyt import PosWebServiceDict

from odoo import api, fields, models

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    pos_bind_ids = fields.One2many(
        comodel_name="pos.sale.order",
        inverse_name="odoo_id",
        string="Pos Bindings",
    )


class PosSaleOrder(models.Model):
    _name = "pos.sale.order"
    _inherit = "pos.binding.odoo"
    _inherits = {"sale.order": "odoo_id"}
    _description = "Sale order pos bindings"

    odoo_id = fields.Many2one(
        comodel_name="sale.order",
        string="Sale Order",
        required=True,
        ondelete="cascade",
    )
    pos_order_line_ids = fields.One2many(
        comodel_name="pos.sale.order.line",
        inverse_name="pos_order_id",
        string="Pos Order Lines",
    )
    pos_discount_line_ids = fields.One2many(
        comodel_name="pos.sale.order.line.discount",
        inverse_name="pos_order_id",
        string="Pos Discount Lines",
    )
    pos_invoice_number = fields.Char("Pos Invoice Number")
    pos_delivery_number = fields.Char("Pos Delivery Number")
    total_amount = fields.Float(
        string="Total amount in Pos",
        digits="Account",
        readonly=True,
    )
    total_amount_tax = fields.Float(
        string="Total tax in Pos",
        digits="Account",
        readonly=True,
    )
    total_shipping_tax_included = fields.Float(
        string="Total shipping with tax in Pos",
        digits="Account",
        readonly=True,
    )
    total_shipping_tax_excluded = fields.Float(
        string="Total shipping without tax in Pos",
        digits="Account",
        readonly=True,
    )

    def import_orders_since(self, backend, since_date=None, **kwargs):
        """Prepare the import of orders modified on Pos"""
        now_fmt = fields.Datetime.now()

        if since_date:
            date = {"start": since_date}
        else:
            date = {"end": now_fmt}

        self.env["pos.sale.order"].import_batch(
            backend, filters={'data': date, 'action': 'list'}, priority=5, max_retries=0
        )

        # if since_date:
        #     filters = {"date": "1", "filter[date_add]": ">[%s]" % since_date}

        # self.env["pos.mail.message"].import_batch(backend, filters)

        # substract a 10 second margin to avoid to miss an order if it is
        # created in pos at the exact same time odoo is checking.

        next_check_datetime = now_fmt - timedelta(seconds=10)
        backend.import_orders_since = next_check_datetime

        return True

    def export_tracking_number(self):
        """Export the tracking number of a delivery order."""
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            exporter = work.component(usage="tracking.exporter")
            return exporter.run(self)

    def find_pos_state(self):
        self.ensure_one()
        state_list_model = self.env["sale.order.state.list"]
        state_lists = state_list_model.search([("name", "=", self.state)])
        for state_list in state_lists:
            if state_list.pos_state_id.backend_id == self.backend_id:
                return state_list.pos_state_id.pos_id
        return None

    def export_sale_state(self):
        for sale in self:
            new_state = sale.find_pos_state()
            if not new_state:
                continue
            with sale.backend_id.work_on(self._name) as work:
                exporter = work.component(usage="sale.order.state.exporter")
                return exporter.run(self, new_state)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    pos_bind_ids = fields.One2many(
        comodel_name="pos.sale.order.line",
        inverse_name="odoo_id",
        string="Pos Bindings",
    )
    pos_discount_bind_ids = fields.One2many(
        comodel_name="pos.sale.order.line.discount",
        inverse_name="odoo_id",
        string="Pos Discount Bindings",
    )


class PosSaleOrderLine(models.Model):
    _name = "pos.sale.order.line"
    _inherit = "pos.binding.odoo"
    _inherits = {"sale.order.line": "odoo_id"}
    _description = "Sale order line pos bindings"

    odoo_id = fields.Many2one(
        comodel_name="sale.order.line",
        string="Sale Order line",
        required=True,
        ondelete="cascade",
    )
    pos_order_id = fields.Many2one(
        comodel_name="pos.sale.order",
        string="Pos Sale Order",
        required=True,
        ondelete="cascade",
        index=True,
    )

    @api.model
    def create(self, vals):
        ps_sale_order = self.env["pos.sale.order"].search(
            [("id", "=", vals["pos_order_id"])], limit=1
        )
        vals["order_id"] = ps_sale_order.odoo_id.id
        return super().create(vals)


class PosSaleOrderLineDiscount(models.Model):
    _name = "pos.sale.order.line.discount"
    _inherit = "pos.binding.odoo"
    _inherits = {"sale.order.line": "odoo_id"}
    _description = "Sale order line discount pos bindings"

    odoo_id = fields.Many2one(
        comodel_name="sale.order.line",
        string="Sale Order line",
        required=True,
        ondelete="cascade",
    )
    pos_order_id = fields.Many2one(
        comodel_name="pos.sale.order",
        string="Pos Sale Order",
        required=True,
        ondelete="cascade",
        index=True,
    )

    @api.model
    def create(self, vals):
        ps_sale_order = self.env["pos.sale.order"].search(
            [("id", "=", vals["pos_order_id"])], limit=1
        )
        vals["order_id"] = ps_sale_order.odoo_id.id
        return super().create(vals)


class OrderPaymentModel(models.TransientModel):
    # In actual connector version is mandatory use a model
    _name = "__not_exist_pos.payment"
    _description = "Dummy Transient model for Order Payment"


class OrderCarrierModel(models.TransientModel):
    # In actual connector version is mandatory use a model
    _name = "__not_exit_pos.order_carrier"
    _description = "Dummy Transient model for Order Carrier"


class SaleOrderAdapter(Component):
    _name = "pos.sale.order.adapter"
    _inherit = "pos.adapter"
    _apply_on = "pos.sale.order"
    _pos_model = "order"
    _export_node_name = "order"

    def update_sale_state(self, pos_id, datas):
        return self.client.add("order_histories", datas)

    def search(self, filters=None):
        result = super().search(filters=filters)
        shop = self.env["pos.backend"].search(
            [("backend_id", "=", self.backend_record.id)]
        )

        api = PosWebServiceDict(
            shop.default_url, self.pos.webservice_key
        )
        result += api.search(self._pos_model, filters)

        return result


class SaleOrderLineAdapter(Component):
    _name = "pos.sale.order.line.adapter"
    _inherit = "pos.adapter"
    _apply_on = "pos.sale.order.line"
    _pos_model = "order_details"


class OrderPaymentAdapter(Component):
    _name = "__not_exist_pos.payment.adapter"
    _inherit = "pos.adapter"
    _apply_on = "__not_exist_pos.payment"
    _pos_model = "order_payments"


# class OrderDiscountAdapter(Component):
#     _name = "pos.sale.order.line.discount.adapter"
#     _inherit = "pos.adapter"
#     _apply_on = "pos.sale.order.line.discount"

#     @property
#     def _pos_model(self):
#         return self.backend_record.get_version_ps_key("order_discounts")


class PosSaleOrderListener(Component):
    _name = "pos.sale.order.listener"
    _inherit = "base.event.listener"
    _apply_on = ["sale.order"]

    def on_record_write(self, record, fields=None):
        if "state" in fields:
            if not record.pos_bind_ids:
                return
            # a quick test to see if it is worth trying to export sale state
            states = self.env["sale.order.state.list"].search(
                [("name", "=", record.state)]
            )
            if states:
                for binding in record.pos_bind_ids:
                    binding.with_delay(priority=20).export_sale_state()
