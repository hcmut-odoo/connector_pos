# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

from odoo.addons.component.core import Component


class ProductProduct(models.Model):
    _name = "product.product"
    _inherit = [_name, "base_multi_image.owner"]

    pos_variants_bind_ids = fields.One2many(
        comodel_name="pos.product.variant",
        inverse_name="odoo_id",
        string="Pos Bindings (variants)",
    )
    default_on = fields.Boolean(string="Default On")
    impact_price = fields.Float(string="Price Impact", digits="Product Price")

    def update_pos_qty(self):
        for product in self:
            product_template = product.product_tmpl_id
            has_variants = len(product_template.attribute_line_ids) > 0
            if has_variants:
                # Recompute qty in variant binding
                for variant_binding in product.pos_variants_bind_ids:
                    variant_binding.recompute_pos_qty()
            # Recompute qty in product template binding if any variant
            # if modified
            for pos_product in product.product_tmpl_id.pos_bind_ids:
                pos_product.recompute_pos_qty()

    def update_pos_quantities(self):
        for product in self:
            product_template = product.product_tmpl_id
            pos_variants = (
                len(product_template.attribute_line_ids) > 0
                and product_template.product_variant_ids
            ) or []
            if not pos_variants:
                for pos_product in product_template.pos_bind_ids:
                    pos_product.recompute_pos_qty()
            else:
                for pos_variant in pos_variants:
                    for (
                        variant_binding
                    ) in pos_variant.pos_bind_ids:
                        variant_binding.recompute_pos_qty()
        return True

    @api.depends("impact_price")
    def _compute_product_price_extra(self):
        for product in self:
            if product.impact_price:
                product.price_extra = product.impact_price
            else:
                product.price_extra = sum(
                    product.mapped("product_template_attribute_value_ids.price_extra")
                )

    def _set_variants_default_on(self, default_on_list=None):
        if self.env.context.get("skip_check_default_variant", False):
            return True
        templates = self.mapped("product_tmpl_id")
        for template in templates:
            variants = template.with_context(
                skip_check_default_variant=True
            ).product_variant_ids.filtered("default_on")
            if not variants:
                active_variants = template.with_context(
                    skip_check_default_variant=True
                ).product_variant_ids.filtered("active")
                active_variants[:1].write({"default_on": True})
            elif len(variants) > 1:
                if default_on_list:
                    variants.filtered(lambda x: x.id not in default_on_list).write(
                        {"default_on": False}
                    )
                else:
                    variants[1:].write({"default_on": False})

    @api.model
    def create(self, vals):
        res = super().create(vals)
        res._set_variants_default_on()
        return res

    def write(self, vals):
        if not vals.get("active", True):
            vals["default_on"] = False
        res = super().write(vals)
        default_on_list = vals.get("default_on", False) and self.ids or []
        self._set_variants_default_on(default_on_list)
        return res

    def unlink(self):
        self.write({"default_on": False, "active": False})
        res = super().unlink()
        return res

    def open_product_template(self):
        """
        Utility method used to add an "Open Product Template"
        button in product.product views
        """
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "product.template",
            "view_mode": "form",
            "res_id": self.product_tmpl_id.id,
            "target": "new",
            "flags": {"form": {"action_buttons": True}},
        }


class PosProductCombination(models.Model):
    _name = "pos.product.variant"
    _inherit = [
        "pos.binding.odoo",
        "pos.product.qty.mixin",
    ]
    _inherits = {"product.product": "odoo_id"}
    _description = "Product product pos bindings"

    odoo_id = fields.Many2one(
        comodel_name="product.product",
        string="Odoo Product",
        required=True,
        ondelete="cascade",
    )
    main_template_id = fields.Many2one(
        comodel_name="pos.product.template",
        string="Main Template",
        required=True,
        ondelete="cascade",
    )
    quantity = fields.Float(
        string="Computed Quantity", help="Last computed quantity to send on Pos."
    )
    reference = fields.Char(string="Original reference")
    variant_barcode = fields.Char(string="Pos variant barcode")
    size = fields.Char(string="Pos variant size")

    @api.model
    def export_product_quantities(self, backend):
        self.search(
            [
                ("backend_id", "=", backend.id),
            ]
        ).recompute_pos_qty()

    # def set_product_image_variant(self, backend, variant_ids, **kwargs):
    #     with backend.work_on(self._name) as work:
    #         importer = work.component(usage="record.importer")
    #         return importer.set_variant_images(variant_ids, **kwargs)

    def _update_variant_qty(self, binding, extend_qty):
        # print("_update_variant_qty binding", binding)

        vals = {
            "product_id": binding.id,
            "product_tmpl_id": binding.product_tmpl_id.id,
            "new_quantity": extend_qty,
        }

        template_qty = self.env["stock.change.product.qty"].create(vals)

        template_qty.with_context(
            active_id=binding.id,
            connector_no_export=True,
        ).change_product_qty()
    
    def export_quantity(self, backend, barcode, new_qty):
        print("export_quantity",  barcode, new_qty)
        with backend.work_on(self._name) as work:
            exporter = work.component(usage="product.quantity.exporter")
            exporter.run(barcode, new_qty)

    def export_product_stock_qty(self, backend):
        print("export_product_stock_qty", backend)
        # NEED HELP
        # Must have condition for list_variant
        # still list all variants from ODOO
        variant_records = self.search([])
        print("variant_records", variant_records)
        for variant_record in variant_records:
            # product has found at many locations
            # the necessary "lot_stock_id" is found by chain below
            # pos.backend -> stock.warehouse -> stock.location
            warehouse_record = self.env["stock.warehouse"].search([("id", "=", backend.warehouse_id.id)])
            stock_location_id = warehouse_record.lot_stock_id.id
            print(warehouse_record, stock_location_id)
            stock_record = self.env["stock.quant"].search([
                ("product_id", "=", variant_record.odoo_id.id),
                ("location_id","=", stock_location_id)]
            )

            print(stock_record)

            new_qty = stock_record["quantity"]

            backend.env["pos.product.variant"].with_delay().export_quantity(
                backend=backend,
                barcode=variant_record.variant_barcode,
                new_qty=new_qty
            )
    
    def export_product_variant(self, backend, data):
        """Export the inventory configuration and quantity of a product."""
        print("export_product_variant",  backend)
        with backend.work_on(self._name) as work:
                exporter = work.component(usage="product.quantity.exporter")
                exporter.with_delay(priority=40).export_variant(data=data)

class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    pos_bind_ids = fields.One2many(
        comodel_name="pos.product.variant.option",
        inverse_name="odoo_id",
        string="Pos Bindings (variants)",
    )


class PosProductCombinationOption(models.Model):
    _name = "pos.product.variant.option"
    _inherit = "pos.binding.odoo"
    _inherits = {"product.attribute": "odoo_id"}
    _description = "Product variant option pos bindings"

    odoo_id = fields.Many2one(
        comodel_name="product.attribute",
        string="Odoo Attribute",
        required=True,
        ondelete="cascade",
    )
    pos_position = fields.Integer("Pos Position")
    public_name = fields.Char(string="Public Name", translate=True)
    group_type = fields.Selection(
        [("color", "Color"), ("radio", "Radio"), ("select", "Select")],
        string="Type",
        default="select",
    )


class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"

    pos_bind_ids = fields.One2many(
        comodel_name="pos.product.variant.option.value",
        inverse_name="odoo_id",
        string="Pos Bindings",
    )


class PosProductCombinationOptionValue(models.Model):
    _name = "pos.product.variant.option.value"
    _inherit = "pos.binding"
    _inherits = {"product.attribute.value": "odoo_id"}
    _description = "Product variant option valuepos bindings"

    odoo_id = fields.Many2one(
        comodel_name="product.attribute.value",
        string="Odoo Option",
        required=True,
        ondelete="cascade",
    )
    pos_position = fields.Integer(
        string="Pos Position",
        default=1,
    )
    id_attribute_group = fields.Many2one(
        comodel_name="pos.product.variant.option"
    )


class ProductCombinationAdapter(Component):
    _name = "pos.product.variant.adapter"
    _inherit = "pos.adapter"
    _apply_on = "pos.product.variant"
    _pos_model = "product_variant"
    _export_node_name = "product_variant"

    def update_new_quantity(self, barcode, new_qty):
        result = self.client.edit(
            "product_variant", 
            content={"stock_qty": new_qty},
            options={"variant_barcode": barcode}
        )

        return result

    def export_new_variant(self, data):
        content = {
            "product_id": data["product_id"],
            "variant_barcode": data["variant_barcode"],
            "size": data["size"],
            "extend_price": int(data["extend_price"]),
            "stock_qty": int(data["stock_qty"]),
        }

        try:
            response = self.client.add(self._pos_model, content=content, options={})
            return response
        except Exception as e:
            print("Response:", e)

class ProductCombinationOptionAdapter(Component):
    _name = "pos.product.variant.option.adapter"
    _inherit = "pos.adapter"
    _apply_on = "pos.product.variant.option"

    _pos_model = "product_variant"
    _export_node_name = "product_variant"


class ProductCombinationOptionValueAdapter(Component):
    _name = "pos.product.variant.option.value.adapter"
    _inherit = "pos.adapter"
    _apply_on = "pos.product.variant.option.value"

    _pos_model = "product_variant"
    _export_node_name = "product_variant"
