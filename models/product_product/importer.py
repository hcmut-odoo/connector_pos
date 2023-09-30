# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo import models

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)
try:
    from ....pospyt.pospyt import PosWebServiceError
except ImportError:
    _logger.debug("Cannot import from `pospyt`")


class ProductCombinationImporter(Component):
    _name = "pos.product.variant.importer"
    _inherit = ["pos.importer","pos.adapter"]
    _apply_on = "pos.product.variant"

    def template_attribute_lines(self, option_values): # Not run
        record = self.pos_record
        template_binder = self.binder_for("pos.product.template")
        template = template_binder.to_internal(record["product_id"]).odoo_id
        attribute_values = {}
        option_value_binder = self.binder_for(
            "pos.product.variant.option.value"
        )
        option_binder = self.binder_for("pos.product.variant.option")
        for option_value in option_values:
            attr_id = option_binder.to_internal(
                option_value["id_attribute_group"]
            ).odoo_id.id
            value_id = option_value_binder.to_internal(option_value["id"]).odoo_id.id
            if attr_id not in attribute_values:
                attribute_values[attr_id] = []
            attribute_values[attr_id].append(value_id)
        for attr_id, value_ids in attribute_values.items():
            attr_line = template.attribute_line_ids.filtered(
                lambda l: l.attribute_id.id == attr_id
            )
            if attr_line:
                attr_line.write({"value_ids": [(6, 0, value_ids)]})
            else:
                attr_line = self.env["product.template.attribute.line"].create(
                    {
                        "attribute_id": attr_id,
                        "product_tmpl_id": template.id,
                        "value_ids": [(6, 0, value_ids)],
                    }
                )
            attr_line._update_product_template_attribute_values()

    def _after_import(self, binding):
        super()._after_import(binding)
        # self.import_supplierinfo(binding)

    # def set_variant_images(self, variants):
    #     backend_adapter = self.component(
    #         usage="backend.adapter", model_name="pos.product.variant"
    #     )
    #     for variant in variants:
    #         record = backend_adapter.read(variant["id"])
    #         associations = record.get("associations", {})
    #         try:
    #             pos_images = associations.get("images", {}).get(
    #                 self.backend_record.get_version_pos_key("image"), {}
    #             )
    #         except PosWebServiceError:
    #             # TODO: don't we track anything here? Maybe a checkpoint?
    #             continue
    #         binder = self.binder_for("pos.product.image")
    #         if not isinstance(pos_images, list):
    #             pos_images = [pos_images]
    #         if "id" in pos_images[0]:
    #             images = [
    #                 binder.to_internal(x.get("id"), unwrap=True) for x in pos_images
    #             ]
    #         else:
    #             continue
    #         product_binder = self.binder_for("pos.product.variant")
    #         product = product_binder.to_internal(variant["id"], unwrap=True)
    #         product.with_context(connector_no_export=True).write(
    #             {"image_ids": [(6, 0, [x.id for x in images])]}
    #         )

    def _import(self, binding, **kwargs):
        # We need to pass the template pos record because we need it
        # for variant mapper
        if not hasattr(self.work, "parent_pos_record"):
            tmpl_adapter = self.component(
                usage="backend.adapter", model_name="pos.product.template"
            )

            tmpl_record = tmpl_adapter.read(self.pos_record["product_id"])
            self.work.parent_pos_record = tmpl_record

            if "parent_pos_record" not in self.work._propagate_kwargs:
                self.work._propagate_kwargs.append("parent_pos_record")

        return super()._import(binding, **kwargs)


class ProductCombinationMapper(Component):
    _name = "pos.product.variant.mapper"
    _inherit = "pos.import.mapper"
    _apply_on = "pos.product.variant"

    direct = []

    from_main = []

    @mapping
    def weight(self, record):
        pos_product_tmpl_obj = self.env["pos.product.template"]
        variant_weight = float(record.get("weight", "0.0"))
        if not hasattr(self.work, "parent_pos_record"):
            pos_product_tmpl = pos_product_tmpl_obj.search(
                [("pos_id", "=", record["product_id"])]
            )
            main_weight = pos_product_tmpl.weight
        else:
            main_weight = float(self.work.parent_pos_record.get("weight", 0.0))
        weight = main_weight + variant_weight
        return {"weight": weight}

    @mapping
    def variant_default(self, record):
        return {"default_on": bool(int(record["id"] or 0))}

    @only_create
    @mapping
    def product_tmpl_id(self, record):
        template = self.get_main_template_binding(record)
        product_binder = self.binder_for("pos.product.variant")
        product = product_binder.to_internal(record["id"])
        if not product or product.product_tmpl_id.id != template.odoo_id.id:
            return {"product_tmpl_id": template.odoo_id.id}
        return {}

    @mapping
    def from_main_template(self, record):
        main_template = self.get_main_template_binding(record)
        result = {}
        for attribute in self.from_main:
            if attribute not in main_template:
                continue
            if hasattr(main_template[attribute], "id"):
                result[attribute] = main_template[attribute].id
            elif type(main_template[attribute]) is models.BaseModel:
                ids = []
                for element in main_template[attribute]:
                    ids.append(element.id)
                result[attribute] = [(6, 0, ids)]
            else:
                result[attribute] = main_template[attribute]

        return result

    def get_main_template_binding(self, record):
        template_binder = self.binder_for("pos.product.template")

        return template_binder.to_internal(record["product_id"])

    def _get_option_value(self, record):
        option_values = [{"id": record["id"]}]
        template_binding = self.get_main_template_binding(record)
        template = template_binding.odoo_id

        if type(option_values) is dict:
            option_values = [option_values]
        
        tmpl_values = template.attribute_line_ids.mapped("product_template_value_ids")
        
        for option_value in option_values:
            option_value_binder = self.binder_for(
                "pos.product.variant.option.value"
            )
            
            option_value_binding = option_value_binder.to_internal(option_value["id"])
            tmpl_value = tmpl_values.filtered(
                lambda v: v.product_attribute_value_id.id
                == option_value_binding.odoo_id.id
            )
            
            assert option_value_binding, "must have a binding for the option"
            yield tmpl_value

    @mapping
    def product_template_attribute_value_ids(self, record):
        results = []
        for tmpl_attr_value in self._get_option_value(record):
            results.append(tmpl_attr_value.id)
            
        return {"product_template_attribute_value_ids": [(6, 0, results)]}

    @mapping
    def main_template_id(self, record):
        template_binding = self.get_main_template_binding(record)
        return {"main_template_id": template_binding.id}

    def _product_code_exists(self, code):
        model = self.env["product.product"]
        variant_binder = self.binder_for("pos.product.variant")
        product = model.with_context(active_test=False).search(
            [
                ("default_code", "=", code),
                ("company_id", "=", self.backend_record.company_id.id),
            ],
            limit=1,
        )
        return product and not variant_binder.to_external(product, wrap=True)

    @mapping
    def default_code(self, record):
        code = record.get("reference")
        if not code:
            code = "{}_{}".format(record["product_id"], record["id"])
        if (
            not self._product_code_exists(code)
            or self.backend_record.matching_product_ch == "reference"
        ):
            return {"default_code": code}
        i = 1
        current_code = "{}_{}".format(code, i)
        while self._product_code_exists(current_code):
            i += 1
            current_code = "{}_{}".format(code, i)
        return {"default_code": current_code}

    @mapping
    def barcode(self, record):
        barcode = record.get("variant_barcode")
        # check_ean = self.env["barcode.nomenclature"].check_ean
        # if barcode in ["", "0"]:
        #     backend_adapter = self.component(
        #         usage="backend.adapter", model_name="pos.product.template"
        #     )
        #     template = backend_adapter.read(record["product_id"])
        #     barcode = template.get("barcode") or template.get("id")
        # if barcode and barcode != "0" and check_ean(barcode):
        #     return {"barcode": barcode}
        return {"barcode": barcode}

    def _get_tax_ids(self, record): # Make default id_tax_rules_group
        product_tmpl_adapter = self.component(
            usage="backend.adapter", model_name="pos.product.template"
        )
        tax_group = {"id_tax_rules_group": 1}
        tax_group = self.binder_for("pos.account.tax.group").to_internal(
            tax_group["id_tax_rules_group"], unwrap=True
        )

        return tax_group.tax_ids

    def _apply_taxes(self, tax, price):
        if self.backend_record.taxes_included == tax.price_include:
            return price
        factor_tax = tax.price_include and (1 + tax.amount / 100) or 1.0
        if self.backend_record.taxes_included:
            if not tax.price_include:
                return price / factor_tax
        else:
            if tax.price_include:
                return price * factor_tax

    @mapping
    def specific_price(self, record):
        product = self.binder_for("pos.product.variant").to_internal(
            record["id"], unwrap=True
        )
        product_template = self.binder_for("pos.product.template").to_internal(
            record["product_id"]
        )
        tax = product.product_tmpl_id.taxes_id[:1] or self._get_tax_ids(record)
        impact = float(self._apply_taxes(tax, float(record["extend_price"] or "0.0")))
        cost_price = float(record["extend_price"] or "0.0")
        return {
            "list_price": product_template.list_price,
            "standard_price": cost_price or product_template.wholesale_price,
            "impact_price": impact,
        }

    @only_create
    @mapping
    def odoo_id(self, record):
        """Will bind the product to an existing one with the same code"""
        if self.backend_record.matching_product_template:
            code = record.get(self.backend_record.matching_product_ch)
            if self.backend_record.matching_product_ch == "reference":
                if code:
                    product = self.env["product.product"].search(
                        [("default_code", "=", code)], limit=1
                    )
                    if product:
                        return {"odoo_id": product.id}
            if self.backend_record.matching_product_ch == "barcode":
                if code:
                    product = self.env["product.product"].search(
                        [("barcode", "=", code)], limit=1
                    )
                    if product:
                        return {"odoo_id": product.id}

        template = self.get_main_template_binding(record).odoo_id
        # if variant already exists linked it since we can't have 2 variants with
        # the exact same attributes
        option_values = [{"id" : record["id"]}]

        option_value_binder = self.binder_for(
            "pos.product.variant.option.value"
        )

        value_ids = [
            option_value_binder.to_internal(option_value["id"]).odoo_id.id
            for option_value in option_values
        ]

        for variant in template.product_variant_ids:
            if sorted(
                variant.product_template_attribute_value_ids.mapped(
                    "product_attribute_value_id"
                ).ids
            ) == sorted(value_ids):
                return {"odoo_id": variant.id}
        return {}


class ProductCombinationOptionImporter(Component):
    _name = "pos.product.variant.option.importer"
    _inherit = "pos.importer"
    _apply_on = "pos.product.variant.option"

    def _import_values(self, attribute_binding):
        option_value = self.pos_record

        self._import_dependency(
            option_value, "pos.product.variant.option.value"
        )
    
    def _has_to_skip(self, binding):
        pv_obj = self.env["product.product"]

        # Get product variant record from POS
        pos_product_variant_record = self.pos_record

        # Search for a product template by barcode
        barcode = pos_product_variant_record["variant_barcode"]
        extend_qty = pos_product_variant_record["stock_qty"]
        product_variant_mapped = pv_obj.search([("barcode", "=", barcode)])

        # If variant is exist -> only update quantity
        if product_variant_mapped:
            self._update_variant_qty(binding=product_variant_mapped, new_qty=extend_qty)
            return True

        return False

    def _update_variant_qty(self, binding, new_qty):
        scpq_obj = self.env["stock.change.product.qty"]
        current_stock_change_product_qty = scpq_obj.search([
            ("product_id", "=", binding.id),
            ("product_tmpl_id", "=", binding.product_tmpl_id.id)
        ])

        vals = {
            "product_id": binding.id,
            "product_tmpl_id": binding.product_tmpl_id.id,
            "new_quantity": current_stock_change_product_qty.new_quantity + new_qty,
        }

        template_qty = self.env["stock.change.product.qty"].create(vals)

        template_qty.with_context(
            active_id=binding.id,
            connector_no_export=True,
        ).change_product_qty()

    def _after_import(self, binding):
        super()._after_import(binding)
        self._import_values(binding)


class ProductCombinationOptionMapper(Component):
    _name = "pos.product.variant.option.mapper"
    _inherit = "pos.import.mapper"
    _apply_on = "pos.product.variant.option"

    direct = []

    @mapping
    def backend_id(self, record):
        return {"backend_id": self.backend_record.id}

    @only_create
    @mapping
    def odoo_id(self, record):
        name = self.name(record).get("name")
        binding = self.env["product.attribute"].search(
            [("name", "=", name)],
            limit=1,
        )
        if binding:
            return {"odoo_id": binding.id}

    @mapping
    def name(self, record):
        return {"name": record["size"] + "-" + str(record["product_id"])}

    @mapping
    def create_variant(self, record):
        # seems the best way. If we do it in automatic, we could have too much variants
        # compared to pos if we got more thant 1 attributes, which seems
        # totally possible. If we put no variant, and we delete one value on pos
        # product won't be inative by odoo
        # with dynamic, pos create it on product import, odoo inactive it if
        # deleted on pos...
        # We avoid "You cannot change the Variants Creation Mode of the attribute"
        # error by not changing the attribute when there is existing record
        odoo_id = self.odoo_id(record)
        if not odoo_id:
            return {"create_variant": "dynamic"}


class ProductCombinationOptionValueAdapter(Component):
    _name = "pos.product.variant.option.value.adapter"
    _inherit = "pos.adapter"
    _apply_on = "pos.product.variant.option.value"

    _pos_model = "product_variant"
    _export_node_name = "product_variant"


class ProductCombinationOptionValueImporter(Component):
    _name = "pos.product.variant.option.value.importer"
    _inherit = "pos.importer"
    _apply_on = "pos.product.variant.option.value"

    _translatable_fields = {
        "pos.product.variant.option.value": ["name"],
    }


class ProductCombinationOptionValueMapper(Component):
    _name = "pos.product.variant.option.value.mapper"
    _inherit = "pos.import.mapper"
    _apply_on = "pos.product.variant.option.value"


    @mapping
    def name(self, record):
        return {"name": record["size"]}

    @only_create
    @mapping
    def odoo_id(self, record):
        attribute_binder = self.binder_for("pos.product.variant.option")
        attribute = attribute_binder.to_internal(
            record["id"], unwrap=True
        )
        assert attribute
        binding = self.env["product.attribute.value"].search(
            [("name", "=", record["size"]), ("attribute_id", "=", attribute.id)],
            limit=1,
        )
        if binding:
            return {"odoo_id": binding.id}

    @mapping
    def attribute_id(self, record):
        binder = self.binder_for("pos.product.variant.option")
        attribute = binder.to_internal(record["id"], unwrap=True)
        
        return {"attribute_id": attribute.id}

    @mapping
    def backend_id(self, record):
        return {"backend_id": self.backend_record.id}


class ProductProductBatchImporter(Component):
    _name = "pos.product.variant.batch.importer"
    _inherit = "pos.delayed.batch.importer"
    _apply_on = "pos.product.variant"
