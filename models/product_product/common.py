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

    def export_inventory(self, fields=None):
        """Export the inventory configuration and quantity of a product."""
        backend = self.backend_id
        with backend.work_on("pos.product.variant") as work:
            exporter = work.component(usage="inventory.exporter")
            return exporter.run(self, fields)

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
    _pos_model = "product_variants"
    _export_node_name = "product_variants"


# class ProductCombinationOptionAdapter(Component):
#     _name = "pos.product.variant.option.adapter"
#     _inherit = "pos.adapter"
#     _apply_on = "pos.product.variant.option"

#     _pos_model = "product_options"
#     _export_node_name = "product_options"


# class ProductCombinationOptionValueAdapter(Component):
#     _name = "pos.product.variant.option.value.adapter"
#     _inherit = "pos.adapter"
#     _apply_on = "pos.product.variant.option.value"

#     _pos_model = "product_option_values"
#     _export_node_name = "product_option_value"
