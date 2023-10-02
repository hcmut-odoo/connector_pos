# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
from collections import defaultdict

import datetime

from ....pospyt.pospyt import PosWebServiceDict

from odoo import api, fields, models

from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if
from odoo.addons.queue_job.job import identity_exact

from ...components.backend_adapter import retryable_error

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    pos_bind_ids = fields.One2many(
        comodel_name="pos.product.template",
        inverse_name="odoo_id",
        copy=False,
        string="Pos Bindings",
    )
    pos_default_category_id = fields.Many2one(
        comodel_name="product.category",
        string="Pos Default Category",
        ondelete="restrict",
    )
    default_image_id = fields.Integer(string="Pos Default Image ID")

    @api.depends(
        "product_variant_ids",
        "product_variant_ids.stock_quant_ids",
    )
    def _compute_quantities(self):
        return super()._compute_quantities()

    def update_pos_quantities(self):
        for template in self:
            # Recompute product template Pos qty
            template.mapped("pos_bind_ids").recompute_pos_qty()
            # Recompute variant Pos qty
            template.mapped(
                "product_variant_ids.pos_variants_bind_ids"
            ).recompute_pos_qty()
        return True


class ProductQtyMixin(models.AbstractModel):
    _name = "pos.product.qty.mixin"
    _description = "Pos mixin shared between product and template"

    def recompute_pos_qty(self):
        # group products by backend
        backends = defaultdict(set)
        for product in self:
            backends[product.backend_id].add(product.id)

        for backend, product_ids in backends.items():
            products = self.browse(product_ids)
            products._recompute_pos_qty_backend(backend)
        return True

    def _recompute_pos_qty_backend(self, backend):
        locations = backend._get_locations_for_stock_quantities()
        self_loc = self.with_context(location=locations.ids, compute_child=False)
        for product_binding in self_loc:
            new_qty = product_binding._pos_qty(backend)
            if product_binding.quantity != new_qty:
                product_binding.quantity = new_qty
        return True

    def _pos_qty(self, backend):
        qty = self[backend.product_qty_field]
        if qty < 0:
            # make sure we never send negative qty to POS
            # because the overall qty computed at template level
            # is going to be wrong.
            qty = 0.0
        return qty


class PosProductTemplate(models.Model):
    _name = "pos.product.template"
    _inherit = [
        "pos.binding.odoo",
        "pos.product.qty.mixin",
    ]
    _inherits = {"product.template": "odoo_id"}
    _description = "Product template pos bindings"

    odoo_id = fields.Many2one(
        comodel_name="product.template",
        required=True,
        ondelete="cascade",
        string="Template",
    )
    always_available = fields.Boolean(
        string="Active Pos",
        default=True,
        help="If checked, this product is considered always available",
    )
    quantity = fields.Float(
        string="Computed Quantity", help="Last computed quantity to send to Pos."
    )
    description = fields.Char(
        string="Description HTML",
        translate=True,
        help="HTML description from Pos",
    )
    description_short = fields.Char(
        string="Short Description",
        translate=True,
    )
    date_add = fields.Datetime(string="Created at (in Pos)", readonly=True)
    date_upd = fields.Datetime(string="Updated at (in Pos)", readonly=True)
    available_for_order = fields.Boolean(
        string="Available for Order Taking",
        default=True,
    )
    show_price = fields.Boolean(string="Display Price", default=True)
    pos_barcode = fields.Char(string="Pos barcode")
    variants_ids = fields.One2many(
        comodel_name="pos.product.variant",
        inverse_name="main_template_id",
        string="Combinations",
    )
    reference = fields.Char(string="Original reference")
    on_sale = fields.Boolean(string="Show on sale icon")
    wholesale_price = fields.Float(
        string="Cost Price",
        digits="Product Price",
    )
    out_of_stock = fields.Selection(
        [("0", "Refuse order"), ("1", "Accept order"), ("2", "Default pos")],
        string="If stock shortage",
    )
    low_stock_threshold = fields.Integer(string="Low Stock Threshold")
    low_stock_alert = fields.Boolean(string="Low Stock Alert")
    visibility = fields.Selection(
        string="Visibility",
        selection=[
            ("both", "All shop"),
            ("catalog", "Only Catalog"),
            ("search", "Only search results"),
            ("none", "Hidden"),
        ],
        default="both",
    )

    def import_products(self, backend, since_date=None, **kwargs):
        now_fmt = datetime.datetime.now()

        if since_date:
            date = {'start': since_date}
        else:
            date = {'end': now_fmt}

        self.env["pos.product.template"].import_batch(
            backend, filters={'date': date}, priority=15, **kwargs
        )

        backend.import_products_since = now_fmt

        return True

    def import_inventory(self, backend):
        with backend.work_on("pos._import_stock_available") as work:
            importer = work.component(usage="batch.importer")
            return importer.run(priority=60)

    def export_inventory(self, fields=None):
        """Export the inventory configuration and quantity of a product."""
        backend = self.backend_id
        with backend.work_on("pos.product.template") as work:
            exporter = work.component(usage="inventory.exporter")
            return exporter.run(self, fields)

    def export_product_quantities(self, backend=None):
        self.search([("backend_id", "=", backend.id)]).recompute_pos_qty()


class TemplateAdapter(Component):
    _name = "pos.product.template.adapter"
    _inherit = "pos.adapter"
    _apply_on = "pos.product.template"
    _pos_model = "product"
    _export_node_name = "product"


class ProductInventoryAdapter(Component):
    _name = "pos._import_stock_available.adapter"
    _inherit = "pos.adapter"
    _apply_on = "pos._import_stock_available"
    _pos_model = "product_variant"
    _export_node_name = "product_variant"

    def get(self, options=None):
        return self.client.get(self._pos_model, options=options)

    def export_quantity(self, backend, barcode, new_qty):
        with backend.work_on("pos.product.variant") as work:
            exporter = work.component(usage="product.quantity.exporter")
            exporter.run(barcode, new_qty)

class PosProductQuantityListener(Component):
    _name = "pos.product.quantity.listener"
    _inherit = "base.connector.listener"
    _apply_on = ["pos.product.variant", "pos.product.template"]

    def _get_inventory_fields(self):
        # fields which should not trigger an export of the products
        # but an export of their inventory
        return ("quantity", "out_of_stock")

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_write(self, record, fields=None):
        inventory_fields = list(set(fields).intersection(self._get_inventory_fields()))
        if inventory_fields:
            record.with_delay(
                priority=20,
                identity_key=identity_exact,
            ).export_inventory(fields=inventory_fields)
