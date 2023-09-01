# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
import logging
from datetime import datetime, timedelta
from decimal import Decimal

import pytz

from odoo import _, fields

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.connector_ecommerce.components.sale_order_onchange import (
    SaleOrderOnChange,
)
from odoo.addons.queue_job.exception import FailedJobError, NothingToDoJob

from ...components.exception import OrderImportRuleRetry
from ...utils.datetime import DATE_FORMAT

_logger = logging.getLogger(__name__)

try:
    from ....pospyt.pospyt import PosWebServiceError
except ImportError:
    _logger.debug("Cannot import from `pospyt`")


class PosSaleOrderOnChange(SaleOrderOnChange):
    _model_name = "pos.sale.order"


class SaleImportRule(Component):
    _name = "pos.sale.import.rule"
    _inherit = ["pos.adapter", "base.pos.connector"]
    # _inherit = ["base.pos.connector"]
    _apply_on = "pos.sale.order"
    _usage = "sale.import.rule"

    def _rule_always(self, record, mode):
        print("_rule_always")
        """Always import the order"""
        return True

    def _rule_never(self, record, mode):
        """Never import the order"""
        print("_rule_never")
        raise NothingToDoJob(
            "Orders with payment modes %s "
            "are never imported." % record["payment_method"]
        )

    def _rule_paid(self, record, mode):
        """Import the order only if it has received a payment"""
        print("_rule_paid")
        if self._get_paid_amount(record) == 0.0:
            raise OrderImportRuleRetry(
                "The order has not been paid.\nThe import will be retried later."
            )

    _rules = {
        "always": _rule_always,
        "paid": _rule_paid,
        "authorized": _rule_paid,
        "never": _rule_never,
    }

    def check(self, record):
        """Check whether the current sale order should be imported
        or not. It will actually use the payment mode configuration
        and see if the chosen rule is fullfilled.

        :returns: True if the sale order should be imported
        :rtype: boolean
        """
        print("check record", record)
        # pos_payment_method = record["payment_method"]
        # mode_binder = self.binder_for("account.payment.mode")
        # payment_mode = mode_binder.to_internal(pos_payment_method)
        # print("payment_mode",payment_mode)
        # if not payment_mode:
        #     raise FailedJobError(
        #         _(
        #             "The configuration is missing for the Payment Mode '%s'.\n\n"
        #             "Resolution:\n"
        #             " - Use the automatic import in 'Connectors > Pos "
        #             "Backends', button 'Import payment modes', or:\n"
        #             "\n"
        #             "- Go to 'Invoicing > Configuration > Management "
        #             "> Payment Modes'\n"
        #             "- Create a new Payment Mode with name '%s'\n"
        #             "-Eventually  link the Payment Method to an existing Workflow "
        #             "Process or create a new one."
        #         )
        #         % (pos_payment_method, pos_payment_method)
        #     )
        # self._rule_global(record)
        self._rule_state(record)
        # self._rules[payment_mode.import_rule](self, record, payment_mode)
    
    
        
    def _mapping_state(self, state):
        state_mappings = {
            'processing': 'Quotation/Draft',
            'done': 'Confirmed',
            'cancel': 'Canceled'
        }

        return state_mappings.get(state, state)



        
    def _mapping_state(self, state):
        state_mappings = {
            'processing': 'Quotation/Draft',
            'done': 'Confirmed',
            'cancel': 'Canceled'
        }

        return state_mappings.get(state, state)


    def _rule_state(self, record):
        """Check if order is importable by its state.

        If `backend_record.importable_order_state_ids` is valued
        we check if current order is in the list.
        If not, the job fails gracefully.
        """
        # if self.backend_record.importable_order_state_ids:
        #     pos_state_id = record["id"]
        #     state = self.binder_for("pos.sale.order.state").to_internal(
        #         pos_state_id, unwrap=1
        #     )
        #     if not state:
        #         raise FailedJobError(
        #             _(
        #                 "The configuration is missing "
        #                 "for sale order state with POS ID=%s.\n\n"
        #                 "Resolution:\n"
        #                 " - Use the automatic import in 'Connectors > Pos "
        #                 "Backends', button 'Synchronize base data'."
        #             )
        #             % (pos_state_id,)
        #         )
        state = record["status"]
        if state == "processing" or state == "cancel":
        # if state not in self.backend_record.importable_order_state_ids:
            raise NothingToDoJob(
                _(
                    "Import of the order with POS ID=%s canceled "
                    "because its state is not importable"
                )
                % record["id"]
            )


class SaleOrderImportMapper(Component):
    _name = "pos.sale.order.mapper"
    # _inherit = ["pos.adapter", "pos.import.mapper"]
    _inherit = ["pos.import.mapper","pos.adapter"]
    _apply_on = "pos.sale.order"

    direct = [
        ("id", "pos_invoice_number"),
        ("delivery_phone", "pos_delivery_number"),
        # ("total_paid", "total_amount"),
    ]

    def _get_sale_order_lines(self, record):
        print("_get_sale_order_lines", record)
        # orders = self.client.get("order_item", record["id"], {'action': 'find'})["data"]
        # print("_get_sale_order_lines orders", orders)
        orders = record.get("order_rows")
        if isinstance(orders, dict):
            return [orders]
        return orders

    # def _get_discounts_lines(self, record):
    #     print("_get_discounts_lines")
    #     if record["total_discounts"] == "0.00":
    #         return []
    #     adapter = self.component(
    #         usage="backend.adapter", model_name="pos.sale.order.line.discount"
    #     )
    #     discount_ids = adapter.search({"filter[id_order]": record["id"]})
    #     discount_mappers = []
    #     for discount_id in discount_ids:
    #         discount_mappers.append({"id": discount_id})
    #     return discount_mappers

    children = [
        (
            _get_sale_order_lines,
            "pos_order_line_ids",
            "pos.sale.order.line",
        ),
        # (
        #     _get_discounts_lines,
        #     "pos_discount_line_ids",
        #     "pos.sale.order.line.discount",
        # ),
    ]

    def _map_child(self, map_record, from_attr, to_attr, model_name):
        print("_map_child")
        source = map_record.source
        # TODO patch ImportMapper in connector to support callable
        if callable(from_attr):
            child_records = from_attr(self, source)
        else:
            child_records = source[from_attr]

        children = []
        print("child_records", child_records)
        for child_record in child_records:
            # adapter = self.component(usage="backend.adapter", model_name=model_name)
            # child is enounh, not need to change
            # print("child_records adapter", adapter)
            # detail_record = adapter.read(child_record["order_id"],{'action': 'find'})
            # print("child_records detail_record",detail_record)

            mapper = self._get_map_child_component(model_name)
            items = mapper.get_items(
                [child_record], map_record, to_attr, options=self.options
            )
            children.extend(items)
        return children

    def _sale_order_exists(self, name):
        sale_order = self.env["sale.order"].search(
            [
                ("name", "=", name),
                ("company_id", "=", self.backend_record.company_id.id),
            ],
            limit=1,
        )
        return len(sale_order) == 1

    direct = [
        # ("order_id", "order_id"),
        # ("delivery_number", "pos_delivery_number"),
        # ("total", "total"),
        # ("total_shipping_tax_incl", "total_shipping_tax_included"),
        # ("total_shipping_tax_excl", "total_shipping_tax_excluded"),
    ]



    @mapping
    def invoice_number(self, record):
        print("invoice_number",record)
        pos_order_id = record["id"]
        pos_invoice_ids = self.client.search('invoice', options={
            'filter': {
                'order_id': { 
                    'operator': 'eq', 
                    'value': pos_order_id
                }
            }
        })
        
        # Assign to class scope
        if pos_invoice_ids[0]:
            self.pos_invoice_id = pos_invoice_ids[0]
        print("self.pos_invoice_id",self.pos_invoice_id)
        return {"pos_invoice_number":self.pos_invoice_id}
    
    # @mapping
    # def order_id(self, record):        
    #     return {"order_id":record["id"]}

    @mapping
    def total_paid(self, record):
        print("total_paid",record)
        pos_order_id = record["id"]
        pos_invoice_ids = self.client.search('invoice', options={
            'filter': {
                'order_id': { 
                    'operator': 'eq', 
                    'value': pos_order_id
                }
            }
        })

        # pos_invoice_record = self.client.get("invoice", pos_invoice_ids[0], {'action': 'find'})
        pos_invoice_record = self.client.find("invoice", pos_invoice_ids[0])["data"]
        self.pos_invoice_record = pos_invoice_record
        print("pos_invoice_record",pos_invoice_record)
        return {"total_amount":pos_invoice_record["total"]}

    @mapping
    def state(self, record):
        return {"state": "sale"}

    @mapping
    def name(self, record):
        basename = record["order_transaction"]
        if not self._sale_order_exists(basename):
            return {"name": basename}
        i = 1
        name = basename + "_%d" % (i)
        while self._sale_order_exists(name):
            i += 1
            name = basename + "_%d" % (i)
        return {"name": name}

    @mapping
    def partner_id(self, record):
        binder = self.binder_for("pos.res.partner")
        partner = binder.to_internal(record["user_id"], unwrap=True)
        return {"partner_id": partner.id}

    # @mapping
    # def partner_invoice_id(self, record):
    #     binder = self.binder_for("pos.address")

    #     pos_order_id = record["id"]
    #     pos_invoice_ids = self.client.search('invoice', options={
    #         'action': 'list', 
    #         'filter': {
    #             'order_id': { 
    #                 'operator': 'eq', 
    #                 'value': pos_order_id
    #             }
    #         }
    #     })

    #     pos_invoice_id = pos_invoice_ids[0]
    #     address = binder.to_internal(pos_invoice_id, unwrap=True)

    #     return {"partner_invoice_id": address.id}

    # @mapping
    # def partner_shipping_id(self, record):
    #     binder = self.binder_for("pos.address")
    #     pos_address_delivery_id = record["id"]
    #     shipping = binder.to_internal(pos_address_delivery_id, unwrap=True)

    #     return {"partner_shipping_id": shipping.id}

    # @mapping
    # def pricelist_id(self, record):
    #     return {"pricelist_id": self.backend_record.pricelist_id.id}

    # @mapping
    # def sale_team(self, record):
    #     if self.backend_record.sale_team_id:
    #         return {"team_id": self.backend_record.sale_team_id.id}

    @mapping
    def backend_id(self, record):
        return {"backend_id": self.backend_record.id}

    # @mapping
    # def payment(self, record):
    #     binder = self.binder_for("account.payment.mode")
    #     mode = binder.to_internal(record["payment_method"])
    #     assert mode, (
    #         "import of error fail in SaleImportRule.check "
    #         "when the payment mode is missing"
    #     )
    #     return {"payment_mode_id": mode.id}

    # @mapping
    # def carrier_id(self, record):
    #     pos_carrier_id = record["id"]
    #     if not pos_carrier_id:
    #         return {}
        
    #     binder = self.binder_for("pos.delivery.carrier")
    #     carrier = binder.to_internal(pos_carrier_id, unwrap=True)
    #     return {"carrier_id": carrier.id}

    @mapping
    def total_tax_amount(self, record):
        if self.pos_invoice_record:
            pos_invoice_record = self.pos_invoice_record
        elif self.pos_invoice_id:
            pos_invoice_record = self.client.find("invoice", self.pos_invoice_id)
        else:
            pos_order_id = record["id"]
            pos_invoice_ids = self.client.search('invoice', options={
                'filter': {
                    'order_id': { 
                        'operator': 'eq', 
                        'value': pos_order_id
                    }
                }
            })

            pos_invoice_record = self.client.find("invoice", pos_invoice_ids[0])

        # VAT 10% per total amount of invoice
        tax = float(pos_invoice_record["total"])*0.1

        return {"total_amount_tax": tax}

    @mapping
    def date_order(self, record):
        date_order = record["created_at"]
        if self.backend_record.tz:
            local = pytz.timezone(self.backend_record.tz)
            naive = fields.Datetime.from_string(date_order)
            local_dt = local.localize(naive, is_dst=None)
            date_order = fields.Datetime.to_string(local_dt.astimezone(pytz.utc))
        

    def finalize(self, map_record, values):
        sale_vals = {
            k: v
            for k, v in values.items()
            if k in self.env["sale.order"]._fields.keys()
        }
        sale_vals = self.env["sale.order"].play_onchanges(
            sale_vals,
            [
                "fiscal_position_id",
                "partner_id",
                "partner_shipping_id",
                "partner_invoice_id",
                "payment_mode_id",
                "workflow_process_id",
            ],
        )

        values.update(sale_vals)
        pos_line_list = []

        for line_vals_command in values["pos_order_line_ids"]:
            if line_vals_command[0] not in (0, 1):  # create or update values
                continue

            pos_line_vals = line_vals_command[2]

            line_vals = {
                k: v
                for k, v in pos_line_vals.items()
                if k in self.env["sale.order.line"]._fields.keys()
            }

            line_vals = self.env["sale.order.line"].play_onchanges(
                line_vals, ["product_id"]
            )

            pos_line_vals.update(line_vals)
            pos_line_list.append(
                (line_vals_command[0], line_vals_command[1], pos_line_vals)
            )

        values["pos_order_line_ids"] = pos_line_list

        return values


class SaleOrderImporter(Component):
    _name = "pos.sale.order.importer"
    _inherit = ["pos.importer", "pos.adapter", "base.pos.connector"]
    # _inherit = ["pos.importer"]
    _apply_on = "pos.sale.order"

    def __init__(self, environment):
        """
        :param environment: current environment (backend, session, ...)
        :type environment: :py:class:`connector.connector.ConnectorEnvironment`
        """
        super().__init__(environment)
        self.line_template_errors = []

    def _import_dependencies(self):        
        record = self.pos_record
        print("_import_dependencies", record)
        pos_customer_id = record["user_id"]
        pos_order_id = record["id"]
        
        # Assign to order Id
        # pos_address_invoice_id = record["id"]
        # pos_address_delivery_id = record["id"]
        # pos_carrier_id = record["id"]

        self._import_dependency(
            pos_customer_id,
            "pos.res.partner",
            address_type="contact",
        )

        # if pos_address_invoice_id != pos_address_delivery_id:
        #     self._import_dependency(
        #         pos_address_invoice_id,
        #         "pos.address",
        #         address_type="invoice",
        #     )

        # self._import_dependency(
        #     pos_address_delivery_id,
        #     "pos.address",
        #     # it is important to be sure that delivery address is updated
        #     # else there is a chance to send it to an old address
        #     # it is not rare that the customer changes an existing address
        #     # at the same time he orders.
        #     always=True,
        #     address_type="delivery",
        # )

        # if pos_carrier_id != "0":
        #     self._import_dependency(pos_carrier_id, "pos.delivery.carrier")

        # Order item ids
        # pos_order_item_ids = self.client.search('order_item', options={
        #     'action': 'list', 
        #     'filter': {
        #         'order_id': { 
        #             'operator': 'eq', 
        #             'value': pos_order_id
        #         }
        #     }
        # })

        # Get cart item id and add to list
        # pos_cart_item_ids = []
        # print("pos_order_item_ids",pos_order_item_ids)
        # for pos_order_item_id in pos_order_item_ids:
        #     pos_order_item_record = self.client.get("order_item", pos_order_item_id, {'action': 'find'})["data"][0]
        #     # pos_order_item_record -> pos_order_item_record["data"]
        #     print("pos_order_item_record", pos_order_item_record)
        #     pos_cart_item_id = pos_order_item_record["cart_item_id"]

        #     pos_cart_item_ids.append(pos_cart_item_id)

        # Get cart product and variant id and add to list
        # print("pos_cart_item_ids",pos_cart_item_ids)
        pos_product_and_variant_tuples = []
        # for pos_cart_item_id in pos_cart_item_ids:
        # for pos_cart_item_id in pos_order_item_ids:
        #     # fine -> find
        #     # pos_cart_item_record = self.client.get("cart_item", pos_cart_item_id, {'action': 'find'})
        #     pos_cart_item_record = self.client.get("order_item", pos_cart_item_id, {'action': 'find'})["data"][0]
        #     print("pos_cart_item_record",pos_cart_item_record)
        #     pos_product_id = pos_cart_item_record["product_id"]
        #     pos_product_variant_id = pos_cart_item_record["product_variant_id"]

        #     pos_product_and_variant_tuples.append((pos_product_id, pos_product_variant_id))
        
        order_rows = record.get("order_rows")
        for order_row in order_rows:
            pos_product_template_id = order_row.get("product")["id"]
            pos_product_variant_id = order_row.get("product")["variant_id"]

            pos_product_and_variant_tuples.append((pos_product_template_id, pos_product_variant_id))

        for pos_product_and_variant_tuple in pos_product_and_variant_tuples:
            pos_product_template_id = pos_product_and_variant_tuple[0]
            pos_product_variant_id = pos_product_and_variant_tuple[1]

            try:
                self._import_dependency(
                    pos_product_template_id, "pos.product.template"
                )
            except PosWebServiceError as err:
                # we ignore it, the order line will be imported without product
                _logger.error(
                    "Pos product %s could not be imported, error: %s",
                    pos_product_template_id,
                    err,
                )
                self.line_template_errors.append(pos_product_and_variant_tuple)
            if pos_product_variant_id != "0":
                try:
                    self._import_dependency(
                        pos_product_variant_id, "pos.product.variant"
                    )
                except PosWebServiceError as err:
                    # we ignore it, the order line will be imported without
                    # product
                    _logger.error(
                        "Pos variant %s could not be imported, error: %s",
                        pos_product_variant_id,
                        err,
                    )

    def _add_shipping_line(self, binding):
        shipping_total = (
            binding.total_shipping_tax_included
            if self.backend_record.taxes_included
            else binding.total_shipping_tax_excluded
        )
        # when we have a carrier_id, even with a 0.0 price,
        # Odoo will adda a shipping line in the SO when the picking
        # is done, so we better add the line directly even when the
        # price is 0.0
        if binding.odoo_id.carrier_id:
            binding.odoo_id._create_delivery_line(
                binding.odoo_id.carrier_id, shipping_total
            )
        binding.odoo_id.recompute()

    def _create(self, data):
        print("sale_order _create", data)
        # pos_data_should_be = {
        #     "order_id": 1,
        #     "total": "129000.00",
        #     "backend_id": 1,
        #     "invoice_number": 1,
        #     "name": "Dien Ha",
        #     "partner_id": 67,
        #     "total_paid": "129000.00",
        #     "total_amount_tax": 12900,
        #     "pos_order_line_ids": [],
        #     "partner_invoice_id": 67,
        #     "partner_shipping_id": 67,
        #     "pricelist_id": 1,
        #     "fiscal_position_id": "",
        #     "workflow_process_id": ""
        #     }
        # pos_data_current = {
        #     "pos_invoice_number": data["invoice_number"],
        #     "total_amount": data["total_paid"],
        #     "backend_id": data["backend_id"],
        #     "name": data["name"],
        #     "partner_id": data["partner_id"],
        #     "partner_invoice_id": data["partner_invoice_id"],
        #     "partner_shipping_id": data["partner_shipping_id"],
        #     "pos_order_line_ids": data["pos_order_line_ids"],
        #     "fiscal_position_id": data["fiscal_position_id"],
        #     "workflow_process_id": data["workflow_process_id"]
        # }

        binding = super()._create(data)
        if binding.fiscal_position_id:
            binding.odoo_id._compute_tax_id()
        return binding

    def _after_import(self, binding):
        super()._after_import(binding)
        self._add_shipping_line(binding)
        self.warning_line_without_template(binding)

    def warning_line_without_template(self, binding):
        if not self.line_template_errors:
            return
        # TODO create activity + post message on sale

    def _has_to_skip(self, binding=False):
        """Return True if the import can be skipped"""
        if binding:
            return True
        rules = self.component(usage="sale.import.rule")
        try:
            return rules.check(self.pos_record)
        except NothingToDoJob as err:
            # we don't let the NothingToDoJob exception let go out, because if
            # we are in a cascaded import, it would stop the whole
            # synchronization and set the whole job to done
            return str(err)


class SaleOrderBatchImporter(Component):
    _name = "pos.sale.order.batch.importer"
    _inherit = "pos.delayed.batch.importer"
    _apply_on = "pos.sale.order"


class SaleOrderLineMapper(Component):
    _name = "pos.sale.order.line.mapper"
    _inherit = "pos.import.mapper"
    _apply_on = "pos.sale.order.line"

    direct = [
        # ("name", "name"),
        ("id", "sequence"),
        ("quantity", "product_uom_qty"),
        # ("reduction_percent", "discount"),
    ]

    @mapping
    def name(self, record):
        return {"name":record["product"]["name"]}

    @mapping
    def pos_id(self, record):
        print("pos_id record", record)
        return {"pos_id": record["id"]}

    @mapping
    def price_unit(self, record):
        print("price_unit record", record)
        product = record.get("product")
        variant = product.get("variant")    
        return {"price_unit": variant["extend_price"]}

    @mapping
    def product_id(self, record):
        print("sale_order product_id", record)
        binder = self.binder_for("pos.product.template")
        template = binder.to_internal(record["product"]["id"], unwrap=True)
        product = self.env["product.product"].search(
            [
                ("product_tmpl_id", "=", template.id),
                # "|",
                # ("company_id", "=", self.backend_record.company_id.id),
                # ("company_id", "=", False),
            ],
            limit=1,
        )
        if not product:
            return {}
        return {"product_id": product.id}

    def _find_tax(self, pos_tax_id):
        binder = self.binder_for("pos.account.tax")
        return binder.to_internal(pos_tax_id, unwrap=True)

    @mapping
    def tax_id(self, record):
        # Assign tax to order id
        taxes = record["id"]

        if not isinstance(taxes, list):
            taxes = [taxes]
        result = self.env["account.tax"].browse()
        for pos_tax in taxes:
            print("tax_id pos_tax", pos_tax)
            result |= self._find_tax(pos_tax)
        return {"tax_id": [(6, 0, result.ids)]}

    @mapping
    def backend_id(self, record):
        return {"backend_id": self.backend_record.id}


class SaleOrderLineDiscountMapper(Component):
    _name = "pos.sale.order.discount.importer"
    _inherit = ["pos.import.mapper", "pos.adapter"]
    _apply_on = "pos.sale.order.line.discount"

    direct = []

    @mapping
    def discount(self, record):
        return {
            "name": record["product"]["name"],
            "product_uom_qty": 1,
        }

    @mapping
    def price_unit(self, record):
        # Pos order id
        pos_order_id = record["id"]
        
        # Order item ids
        pos_order_item_ids = self.client.search('order_item', options={
            'filter': {
                'order_id': { 
                    'operator': 'eq', 
                    'value': pos_order_id
                }
            }
        })

        # Order item record
        self.pos_order_item_record = self.client.find("order_item", pos_order_item_ids[0])
        
        # Cart item id
        self.pos_cart_item_id = self.pos_order_item_record["cart_item_id"]

        # Cart item record
        self.pos_cart_item_record = self.client.find("cart_item", self.pos_cart_item_id)

        # Product and variant id
        self.pos_product_id = self.pos_cart_item_record["product_id"]
        self.pos_product_variant_id = self.pos_cart_item_record["product_variant_id"]
        
        self.pos_product_variant_record = self.client.find("product_variant", self.pos_product_variant_id)

        price_unit = self.pos_product_variant_record["extend_price"]

        return {"price_unit": price_unit}

    @mapping
    def product_id(self, record):
        if self.backend_record.discount_product_id:
            return {"product_id": self.backend_record.discount_product_id.id}
        product_discount = self.env.ref("connector_ecommerce.product_product_discount")
        return {"product_id": product_discount.id}

    @mapping
    def tax_id(self, record):
        return {
            "tax_id": [(6, 0, self.backend_record.discount_product_id.taxes_id.ids)]
        }

    @mapping
    def backend_id(self, record):
        return {"backend_id": self.backend_record.id}

    @mapping
    def pos_id(self, record):
        return {"pos_id": record["id"]}
