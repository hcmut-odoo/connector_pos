# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import datetime
import logging

from odoo import _, api, models
from odoo.exceptions import ValidationError

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import (
    external_to_m2o,
    mapping,
    only_create,
)
from odoo.addons.queue_job.exception import FailedJobError
from odoo.addons.queue_job.job import identity_exact
from ...utils.datetime import (
    format_date_string,
    parse_date_string
)

_logger = logging.getLogger(__name__)

try:
    import html2text
except ImportError:
    _logger.debug("Cannot import `html2text`")

try:
    from bs4 import BeautifulSoup
except ImportError:
    _logger.debug("Cannot import `bs4`")

try:
    from ....pospyt.pospyt import PosWebServiceError
except ImportError:
    _logger.debug("Cannot import from `pospyt`")


class TemplateMapper(Component):
    _name = "pos.product.template.mapper"
    _inherit = "pos.import.mapper"
    _apply_on = "pos.product.template"

    direct = [
        ("wholesale_price", "wholesale_price"),
        ("reference", "reference"),
        ("available_for_order", "available_for_order"),
        ("on_sale", "on_sale"),
        ("low_stock_threshold", "low_stock_threshold"),
        ("low_stock_alert", "low_stock_alert"),
    ]

    @mapping
    def standard_price(self, record):
        if self.has_variants(record):
            return {}
        else:
            return {"standard_price": record.get("wholesale_price", 0.0)}

    @mapping
    def weight(self, record):
        if self.has_variants(record):
            return {}
        else:
            return {"weight": record.get("weight", 0.0)}

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
    def list_price(self, record):
        price = 0.0
        tax = self._get_tax_ids(record)
        if record["price"] != "":
            price = float(record["price"])
        price = self._apply_taxes(tax, price)
        return {"list_price": price}

    @mapping
    def name(self, record):
        if record["name"]:
            return {"name": record["name"]}
        return {"name": "noname"}

    @mapping
    def date_add(self, record):
        if record["created_at"] is None or record["created_at"] == "0000-00-00 00:00:00":
            date_add = datetime.datetime.now()
        else:
            date_add = parse_date_string(record["created_at"])

        return {"date_add": format_date_string(date_add)}

    @mapping
    def date_upd(self, record):
        if record["updated_at"] is None or record["updated_at"] == "0000-00-00 00:00:00":
            date_upd = datetime.datetime.now()
        else:
            date_upd = parse_date_string(record["updated_at"])

        return {"date_upd": format_date_string(date_upd)}

    def has_variants(self, record):
        associations = record.get("associations", {})
        variants = associations.get("variants", {})

        return len(variants or "") != 0

    def _match_variant_odoo_record(self, record):
        # Browse variants for matching products and find if there
        # is a potential template to be matched
        template = self.env["product.template"]
        associations = record.get("associations", {})
        variants = associations.get("variants", {}).get(
            self.backend_record.get_version_pos_key("variants")
        )
        if len(variants) == 1:
            # Defensive mode when product have no variants, force
            # the list mode
            variants = [variants]
        for prod in variants:
            backend_adapter = self.component(
                usage="backend.adapter",
                model_name="pos.product.variant",
            )
            variant = backend_adapter.read(int(prod["id"]))
            code = variant.get(self.backend_record.matching_product_ch)
            if not code:
                continue
            if self.backend_record.matching_product_ch == "reference":
                product = self.env["product.product"].search(
                    [("default_code", "=", code)]
                )
                if len(product) > 1:
                    raise ValidationError(
                        _(
                            "Error! Multiple products found with "
                            "variants reference %s. Maybe consider to "
                            "update you datas"
                        )
                        % code
                    )
                template |= product.product_tmpl_id

            if self.backend_record.matching_product_ch == "barcode":
                product = self.env["product.product"].search([("barcode", "=", code)])
                if len(product) > 1:
                    raise ValidationError(
                        _(
                            "Error! Multiple products found with "
                            "variants reference %s. Maybe consider to "
                            "update you datas"
                        )
                        % code
                    )
                template |= product.product_tmpl_id

        _logger.debug("template %s" % template)
        if len(template) == 1:
            return {"odoo_id": template.id}
        if len(template) > 1:
            raise ValidationError(
                _(
                    "Error! Multiple templates are found with "
                    "variants reference. Maybe consider to change "
                    "matching option"
                )
            )

    def _match_template_odoo_record(self, record):
        code = record.get(self.backend_record.matching_product_ch)
        if self.backend_record.matching_product_ch == "reference":
            if code:
                if self._template_code_exists(code):
                    product = self.env["product.template"].search(
                        [("default_code", "=", code)], limit=1
                    )
                    if product:
                        return {"odoo_id": product.id}

        if self.backend_record.matching_product_ch == "barcode":
            if code:
                product = self.env["product.template"].search(
                    [("barcode", "=", code)], limit=1
                )
                if product:
                    return {"odoo_id": product.id}

    @only_create
    @mapping
    def odoo_id(self, record):
        """Will bind the product to an existing one with the same code"""
        if not self.backend_record.matching_product_template:
            return {}
        if self.has_variants(record):
            return self._match_variant_odoo_record(record)
        else:
            return self._match_template_odoo_record(record)

    def _template_code_exists(self, code):
        model = self.env["product.template"]
        template_binder = self.binder_for("pos.product.template")
        template = model.with_context(active_test=False).search(
            [
                ("default_code", "=", code),
                ("company_id", "=", self.backend_record.company_id.id),
            ],
            limit=1,
        )
        return template and not template_binder.to_external(template, wrap=True)

    @mapping
    def default_code(self, record):
        if self.has_variants(record):
            return {}
        
        code = record.get("reference")

        if not code:
            code = "backend_%d_product_%s" % (self.backend_record.id, record["id"])

        if (
            not self._template_code_exists(code)
            or self.backend_record.matching_product_ch == "reference"
        ):
            return {"default_code": code}
        
        i = 1
        current_code = "%s_%d" % (code, i)

        while self._template_code_exists(current_code):
            i += 1
            current_code = "%s_%d" % (code, i)

        return {"default_code": current_code}

    def clear_html_field(self, content):
        html = html2text.HTML2Text()
        html.ignore_images = True
        html.ignore_links = True

        return html.handle(content)

    @mapping
    def description(self, record):
        return {
            "description": record.get("description", "")
        }

    @mapping
    def active(self, record):
        if record["deleted_at"]:
            return {"always_available": False}
        return {"always_available": True}

    @mapping
    def sale_ok(self, record):
        return {"sale_ok": True}

    @mapping
    def purchase_ok(self, record):
        return {"purchase_ok": True}

    @mapping
    def categ_ids(self, record):
        categories = (
            record["associations"]
            .get("categories", {})
            .get("category", [])
        )
        
        if not isinstance(categories, list):
            categories = [categories]

        product_categories = self.env["product.category"].browse()
        binder = self.binder_for("pos.product.category")

        for pos_category in categories:
            product_categories |= binder.to_internal(
                pos_category["id"],
                unwrap=True,
            )

        return {"categ_ids": [(6, 0, product_categories.ids)]}

    @mapping
    def default_category_id(self, record):
        if not int(record["category_id"]):
            return
        binder = self.binder_for("pos.product.category")
        category = binder.to_internal(
            record["category_id"],
            unwrap=True,
        )
        if category:
            return {"pos_default_category_id": category.id}

    @mapping
    def default_image_id(self, record):
        image_id = record.get("id_default_image", {}).get("value", -1)
        return {"default_image_id": image_id}

    @mapping
    def backend_id(self, record):
        return {"backend_id": self.backend_record.id}

    @mapping
    def company_id(self, record):
        return {"company_id": self.backend_record.company_id.id}

    @mapping
    def barcode(self, record):
        if self.has_variants(record):
            return {}
        barcode = record.get("barcode") or record.get("ean13")
        if barcode in ["", "0"]:
            return {}
        if self.env["barcode.nomenclature"].check_ean(barcode):
            return {"barcode": barcode}
        return {}

    def _get_tax_ids(self, record):
        binder = self.binder_for("pos.account.tax.group")
        tax_group = binder.to_internal(
            record["id_tax_rules_group"],
            unwrap=True,
        )
        tax_ids = tax_group.tax_ids
        if tax_group:
            ERROR = "Tax group `{}` should have one and only one tax, currently have {}"
            assert len(tax_ids) == 1, _(ERROR).format(tax_group.name, len(tax_ids))
        return tax_ids

    @mapping
    def taxes_id(self, record):
        taxes = self._get_tax_ids(record)
        return {"taxes_id": [(6, 0, taxes.ids)]}

    @mapping
    def type(self, record):
        return {"type": "product"}

    @mapping
    def visibility(self, record):
        visibility = record.get("visibility")
        if visibility not in ("both", "catalog", "search"):
            visibility = "none"
        return {"visibility": visibility}


class ImportInventory(models.TransientModel):
    # In actual connector version is mandatory use a model
    _name = "_import_stock_available"
    _description = "Dummy Import Inventory Transient model"

    @api.model
    def import_record(self, backend, pos_id, record=None, **kwargs):
        """Import a record from Pos"""
        with backend.work_on(self._name) as work:
            importer = work.component(usage="record.importer")
            return importer.run(pos_id, record=record, **kwargs)


class ProductInventoryBatchImporter(Component):
    _name = "pos._import_stock_available.batch.importer"
    _inherit = "pos.delayed.batch.importer"
    _apply_on = "_import_stock_available"

    def run(self, filters=None, **kwargs):
        if filters is None:
            filters = {}

        filters["display"] = "[id,id_product,id_product_attribute]"
        _super = super()

        return _super.run(filters, **kwargs)

    def _run_page(self, filters, **kwargs):
        records = self.backend_adapter.get(filters)
        for record in records["stock_availables"]["stock_available"]:
            # if product has variants then do not import product stock
            # since variant stocks will be imported
            if record["id_product_attribute"] == "0":
                variant_stock_ids = self.backend_adapter.search(
                    {
                        "filter[id_product]": record["id_product"],
                        "filter[id_product_attribute]": ">[0]",
                    }
                )
                if variant_stock_ids:
                    continue

            self._import_record(record["id"], record=record, **kwargs)
        return records["stock_availables"]["stock_available"]

    def _import_record(self, record_id, record=None, **kwargs):
        """Delay the import of the records"""
        assert record
        self.env["_import_stock_available"].with_delay().import_record(
            self.backend_record, record_id, record=record, **kwargs
        )


class ProductInventoryImporter(Component):
    _name = "pos._import_stock_available.importer"
    _inherit = "pos.importer"
    _apply_on = "_import_stock_available"

    def _get_quantity(self, record):
        filters = {
            "filter[id_product]": record["id_product"],
            "filter[id_product_attribute]": record["id_product_attribute"],
            "display": "[quantity]",
        }
        quantities = self.backend_adapter.get(filters)
        all_qty = 0
        quantities = quantities["stock_availables"]["stock_available"]

        if isinstance(quantities, dict):
            quantities = [quantities]
        for quantity in quantities:
            all_qty += int(quantity["quantity"])

        return all_qty

    def _get_binding(self):
        record = self.pos_record
        if record["id_product_attribute"] == "0":
            binder = self.binder_for("pos.product.template")
            return binder.to_internal(record["id_product"])
        
        binder = self.binder_for("pos.product.variant")

        return binder.to_internal(record["id_product_attribute"])

    def _import_dependencies(self):
        """Import the dependencies for the record"""
        record = self.pos_record
        self._import_dependency(record["id_product"], "pos.product.template")
        if record["id_product_attribute"] != "0":
            self._import_dependency(
                record["id_product_attribute"], "pos.product.variant"
            )

    def run(self, pos_id, record=None, **kwargs):
        assert record
        self.pos_record = record
        return super().run(pos_id, **kwargs)

    def _import(self, binding, **kwargs):
        record = self.pos_record
        qty = self._get_quantity(record)
        if qty < 0:
            qty = 0
        if binding._name == "pos.product.template":
            products = binding.odoo_id.product_variant_ids
        else:
            products = binding.odoo_id

        for product in products:
            vals = {
                "product_id": product.id,
                "product_tmpl_id": product.product_tmpl_id.id,
                "new_quantity": qty,
            }
            template_qty = self.env["stock.change.product.qty"].create(vals)
            template_qty.with_context(
                active_id=product.id,
                connector_no_export=True,
            ).change_product_qty()


class ProductTemplateImporter(Component):
    """Import one translatable record"""

    _name = "pos.product.template.importer"
    _inherit = "pos.importer"
    _apply_on = "pos.product.template"

    _base_mapper = TemplateMapper

    _translatable_fields = {
        "pos.product.template": [
            "name",
            "description",
            "link_rewrite",
            "description_short",
            "meta_title",
            "meta_description",
            "meta_keywords",
        ],
    }

    def __init__(self, environment):
        """
        :param environment: current environment (backend, session, ...)
        :type environment: :py:class:`connector.connector.ConnectorEnvironment`
        """
        super().__init__(environment)
        self.default_category_error = False

    def _after_import(self, binding):
        super()._after_import(binding)
        self.import_images(binding)
        self.attribute_line(binding)
        self.import_variants()
        self.deactivate_default_product(binding)
        self.warning_default_category_missing(binding)

    def warning_default_category_missing(self, binding):
        if self.default_category_error:
            pass
            # msg = _("The default category could not be imported.")
            # TODO post msg / create activity

    def deactivate_default_product(self, binding):
        # don't consider product as having variant if they are unactive.
        # don't try to inactive a product if it is already inactive.
        binding = binding.with_context(active_test=True)
        if binding.product_variant_count == 1:
            return
        for product in binding.product_variant_ids:
            if product.product_template_attribute_value_ids:
                continue
            self.env["product.product"].browse(product.id).write({"active": False})

    def attribute_line(self, binding):
        record = self.pos_record
        template = binding.odoo_id
        attribute_values = {}
        option_value_binder = self.binder_for(
            "pos.product.variant.option.value"
        )

        # pos_key = self.backend_record.get_version_pos_key("product_option_value")
        option_values = (
            record.get("associations", {})
            .get("product_option_values", {})
            # .get(pos_key, [])
        )
        if not isinstance(option_values, list):
            option_values = [option_values]

        for option_value in option_values:
            value = option_value_binder.to_internal(option_value["id"]).odoo_id
            attr_id = value.attribute_id.id
            value_id = value.id
            if attr_id not in attribute_values:
                attribute_values[attr_id] = []
            attribute_values[attr_id].append(value_id)

        remaining_attr_lines = template.with_context(
            active_test=False
        ).attribute_line_ids
        for attr_id, value_ids in attribute_values.items():
            attr_line = template.with_context(
                active_test=False
            ).attribute_line_ids.filtered(lambda l: l.attribute_id.id == attr_id)
            if attr_line:
                attr_line.write({"value_ids": [(6, 0, value_ids)], "active": True})
                remaining_attr_lines -= attr_line
            else:
                attr_line = self.env["product.template.attribute.line"].create(
                    {
                        "attribute_id": attr_id,
                        "product_tmpl_id": template.id,
                        "value_ids": [(6, 0, value_ids)],
                    }
                )
        if remaining_attr_lines:
            remaining_attr_lines.unlink()

    def _import_variant(self, variant, **kwargs):
        """Import a variant

        Can be overriden for instance to forward arguments to the importer
        """
        # We need to pass the template pos record because we need it
        # for variant mapper
        self.work.parent_pos_record = self.pos_record
        if "parent_pos_record" not in self.work._propagate_kwargs:
            self.work._propagate_kwargs.append("parent_pos_record")
        self._import_dependency(
            variant["id"], "pos.product.variant", always=True, **kwargs
        )

    # def _delay_product_image_variant(self, variants, **kwargs):
    #     delayable = self.env["pos.product.variant"].with_delay(
    #         priority=15,
    #         identity_key=identity_exact,
    #     )
    #     delayable.set_product_image_variant(self.backend_record, variants, **kwargs)

    def import_variants(self):
        pos_record = self._get_pos_data()
        associations = pos_record.get("associations", {})

        pos_key = self.backend_record.get_version_pos_key("variants")
        variants = associations.get("variants", {}).get(pos_key, [])

        if not isinstance(variants, list):
            variants = [variants]
        if variants:
            first_exec = variants.pop(
                variants.index(
                    {"id": pos_record["id_default_variant"]["value"]}
                )
            )
            if first_exec:
                self._import_variant(first_exec)

            for variant in variants:
                self._import_variant(variant)

            # if variants and associations["images"].get("image"):
            #     self._delay_product_image_variant([first_exec] + variants)

    def import_images(self, binding):
        pos_record = self._get_pos_data()
        associations = pos_record.get("associations", {})
        images = associations.get("images", {}).get(
            self.backend_record.get_version_pos_key("image"), {}
        )
        
        if not isinstance(images, list):
            images = [images]

        for image in images:
            if image.get("id"):
                delayable = self.env["pos.product.image"].with_delay(
                    priority=10,
                    identity_key=identity_exact,
                )
                delayable.import_product_image(
                    self.backend_record, pos_record["id"], image["id"]
                )

    def _import_dependencies(self):
        self._import_default_category()
        self._import_categories()

        record = self.pos_record
        option_values = (
            record.get("product_variants", {})
            .get("product_variant_ids", [])
        )

        if not isinstance(option_values, list):
            option_values = [option_values]

        backend_adapter = self.component(
            usage="backend.adapter",
            model_name="pos.product.variant.option.value",
        )

        for option_value in option_values:
            option_value = backend_adapter.read(option_value["id"])
            self._import_dependency(
                option_value["id_attribute_group"],
                "pos.product.variant.option",
            )
            self._import_dependency(
                option_value["id"], "pos.product.variant.option.value"
            )

    def get_template_model_id(self):
        ir_model = self.env["ir.model"].search(
            [("model", "=", "product.template")], limit=1
        )
        assert len(ir_model) == 1
        return ir_model.id

    def _import_default_category(self):
        record = self.pos_record
        print(record)
        if int(record["category_id"]):
            try:
                self._import_dependency(
                    record["category_id"], "pos.product.category"
                )
            except PosWebServiceError:
                # an activity will be added in _after_import (because
                # we'll know the binding at this point)
                self.default_category_error = True

    def _import_categories(self):
        record = self.pos_record
        category_id = record.get("category_id")    

        self._import_dependency(category_id, "pos.product.category")


class ProductTemplateBatchImporter(Component):
    _name = "pos.product.template.batch.importer"
    _inherit = "pos.delayed.batch.importer"
    _apply_on = "pos.product.template"
