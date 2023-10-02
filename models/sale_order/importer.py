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
from ...utils.datetime import (
    format_date_string,
    parse_date_string
)

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
        """Always import the order"""
        return True

    def _rule_never(self, record, mode):
        """Never import the order"""
        raise NothingToDoJob(
            "Orders with payment modes %s "
            "are never imported." % record["payment_method"]
        )

    def _rule_paid(self, record, mode):
        """Import the order only if it has received a payment"""
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

        self._rule_state(record)
    
    
        
    def _mapping_state(self, state):
        state_mappings = {
            'processing': 'Confirmed',
        }

        return state_mappings.get(state, state)


    def _rule_state(self, record):
        """Check if order is importable by its state.

        If `backend_record.importable_order_state_ids` is valued
        we check if current order is in the list.
        If not, the job fails gracefully.
        """

        state = record["status"]
        if state == "cancel":
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
    _inherit = ["pos.import.mapper","pos.adapter"]
    _apply_on = "pos.sale.order"

    direct = [
        ("id", "pos_invoice_number"),
        ("delivery_phone", "pos_delivery_number"),
    ]

    def _get_sale_order_lines(self, record):
        orders = record.get("order_rows")
        if isinstance(orders, dict):
            return [orders]
        return orders

    children = [
        (
            _get_sale_order_lines,
            "pos_order_line_ids",
            "pos.sale.order.line",
        )
    ]

    def _map_child(self, map_record, from_attr, to_attr, model_name):
        # print("_map_child map_record", map_record)
        # print("_map_child from_attr", from_attr)
        # print("_map_child to_attr", to_attr)
        # print("_map_child model_name", model_name)
        source = map_record.source
        # print("_map_child source", source)
        # TODO patch ImportMapper in connector to support callable
        if callable(from_attr):
            child_records = from_attr(self, source)
        else:
            child_records = source[from_attr]


        # print("_map_child child_records", child_records)
        children = []
        for child_record in child_records:
            mapper = self._get_map_child_component(model_name)
            items = mapper.get_items(
                [child_record], map_record, to_attr, options=self.options
            )
            children.extend(items)

        # print("_map_child children",children)
        if not self.validate_children(children=children):
            children = self.rebuild_children(children=children, order_rows=child_records)
            # print("build_child_done", children)
        return children

    def validate_children(self, children):
        for _, _, sale_order_line in children:
            if "product_id" not in sale_order_line:
                return False
        return True
    
    def rebuild_children(self, children, order_rows):
        # print("rebuild_children", children, order_rows)
        product_ids = []
        for order_row in order_rows:
            product = order_row.get("product", {})
            variant = product.get("variant", {})
            variant_barcode = variant.get("variant_barcode", None)
            product = self.find_product(barcode=variant_barcode)
            # print("rebuild_children product", variant_barcode, product)
            product_ids.append(product.id)

        for i, (_, _, sale_order_line) in enumerate(children):
            sale_order_line["product_id"] = product_ids[i]
        
        return children


    def find_product(self, barcode):
        pv_obj = self.env["product.product"]
        product_variant_mapped = pv_obj.search([("barcode", "=", barcode)])

        return product_variant_mapped

    def _sale_order_exists(self, name):
        sale_order = self.env["sale.order"].search(
            [
                ("name", "=", name),
                ("company_id", "=", self.backend_record.company_id.id),
            ],
            limit=1,
        )
        return len(sale_order) == 1
    

    @mapping
    def total_paid(self, record):
        return {"total_amount":record["total"]}

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
        email = record["email"]
        phone = record["phone_number"]

        odoo_partner_mapped = self.found_partner(phone, email)
        return {"partner_id": odoo_partner_mapped.id}

    @mapping
    def backend_id(self, record):
        return {"backend_id": self.backend_record.id}

    @mapping
    def date_order(self, record):
        if record["created_at"] is None or record["created_at"] == "0000-00-00 00:00:00":
            date_cred = datetime.datetime.now()
        else:
            date_cred = parse_date_string(record["created_at"])

        return {"date_order": format_date_string(date_cred)}

    def found_partner(self, phone, email):
        rp_obj = self.env["res.partner"]

        # Search for a partner by email or phone
        partner_mapped = rp_obj.search([("email", "=", email), ("phone", "=", phone)])
        if partner_mapped:
            return partner_mapped
        return None

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
        pos_customer_id = record["user_id"]

        self._import_dependency(
            pos_customer_id,
            "pos.res.partner",
            address_type="contact",
        )

        pos_product_and_variant_tuples = []
        order_rows = record.get("order_rows")
        if not order_rows:
            pos_sale_order_record = self.client.find("order", record["id"])
            order_rows = pos_sale_order_record.get("order_rows")
    
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
        # print("pos.sale.order.importer _create", data)
        binding = super()._create(data)
        if binding.fiscal_position_id:
            binding.odoo_id._compute_tax_id()
        return binding

    def _after_import(self, binding):
        super()._after_import(binding)
        self._add_shipping_line(binding)
        self.warning_line_without_template(binding)
        self._create_invoice(binding)

    def _create_invoice(self, binding):
        pso_obj = self.env["pos.sale.order"]
        pos_record = self.pos_record
        
        # Check status of pos order
        if pos_record["status"] == "done":
            pos_sale_order = pso_obj.search([("id", "=", binding.id)])
            sale_order = pos_sale_order.odoo_id
            sale_order.action_confirm()
                        
            # Create invoice
            try:
                wiz = self.env["sale.advance.payment.inv"].with_context(active_ids=sale_order.ids).create({"advance_payment_method": "delivered",})
                wiz.create_invoices()
            except Exception as e:
                print("Can not create invoice", e)

            # Post action -> confirm invoice
            try:
                invoice = sale_order.invoice_ids[0]
                if invoice.state == "draft":
                    invoice.with_delay(priority=200).auto_do_post_action()
            except Exception as e:
                print("Can not confirm invoice", e)

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
        ("id", "sequence"),
        ("quantity", "product_uom_qty"),
    ]

    @mapping
    def name(self, record):
        return {"name":record["product"]["name"]}

    @mapping
    def pos_id(self, record):
        return {"pos_id": record["id"]}

    @mapping
    def price_unit(self, record):
        product = record.get("product")
        variant = product.get("variant")  
  
        return {"price_unit": variant["extend_price"]}

    @mapping
    def product_id(self, record):
        pos_product_record = record["product"]
        pos_variant_record = pos_product_record["variant"]
        variant_barcode = pos_variant_record["variant_barcode"]
        product = self.env["product.product"].search(
            [
                ("barcode", "=", variant_barcode)
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
