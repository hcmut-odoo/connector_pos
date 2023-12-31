# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models

from odoo.addons.component.core import Component


class ProductCategory(models.Model):
    """
    This class represents a product category in the system.
    It extends the base "product.category" model to add additional functionality.

    Field `pos_bind_ids` represents the one-to-many relationship between the 
    current product category and the POS product category model (`pos.product.category`).

    :param comodel_name: Name of the related model (`pos.product.category`).
    :type comodel_name: str
    :param inverse_name: Name of the inverse field in the related model (`odoo_id`).
    :type inverse_name: str
    :param string: Optional string label for the field (`Pos Bindings`).
    :type string: str
    """

    _inherit = "product.category"

    pos_bind_ids = fields.One2many(
        comodel_name="pos.product.category",
        inverse_name="odoo_id",
        string="Pos Bindings",
    )


class PosProductCategory(models.Model):
    """
    This class represents the POS bindings for product categories in the system.
    It extends the base `pos.binding.odoo` model and inherits from the 
    `product.category` model.

    :param odoo_id: The many-to-one field linking to the original product category.
    :type odoo_id: odoo.fields.Many2one
    :param default_backend_id: The many-to-one field linking to the default POS backend.
    :type default_backend_id: odoo.fields.Many2one
    :param date_add: The datetime field indicating the creation date of the POS binding.
    :type date_add: odoo.fields.Datetime
    :param date_upd: The datetime field indicating the last update date of the POS binding.
    :type date_upd: odoo.fields.Datetime
    :param name: The name field indicating the name of category in POS.
    :type name: odoo.fields.Chars
    """

    _name = "pos.product.category"
    _inherit = "pos.binding.odoo"
    _inherits = {"product.category": "odoo_id"}
    _description = "Product category POS bindings"

    odoo_id = fields.Many2one(
        comodel_name="product.category",
        required=True,
        ondelete="cascade",
        string="Product Category",
    )
    default_backend_id = fields.Many2one(comodel_name="pos.backend")
    date_add = fields.Datetime(string="Created At (on POS)", readonly=True)
    date_upd = fields.Datetime(string="Updated At (on POS)", readonly=True)

    def import_product_categories(self, backend, since_date=None, **kwargs):
        now_fmt = fields.Datetime.now()

        if since_date:
            date = {'start': since_date}
        else:
            date = {'end': now_fmt}

        self.env["pos.product.category"].import_batch(
            backend, filters={'date': date}, priority=5, **kwargs
        )

        backend.import_categories_from_date = now_fmt
        return True

    def export_product_category(self, backend, data):
        with backend.work_on(self._name) as work:
                exporter = work.component(usage="product.category.exporter")
                exporter.export_category(data=data, backend=backend)

class ProductCategoryAdapter(Component):
    """
    This class represents the adapter for synchronizing POS product categories.
    It extends the base `pos.adapter` component.

    :param _model_name: The name of the model associated with the adapter (`pos.product.category`).
    :type _model_name: str
    :param _pos_model: The name of the corresponding POS model (`categories`).
    :type _pos_model: str
    :param _export_node_name: The XML node name for exporting a single category (`category`).
    :type _export_node_name: str
    :param _export_node_name_res: The XML node name for exporting multiple categories (`category`).
    :type _export_node_name_res: str
    """

    _name = "pos.product.category.adapter"
    _inherit = "pos.adapter"
    _apply_on = "pos.product.category"
    
    _model_name = "pos.product.category"
    _pos_model = "category"
    _export_node_name = "category"
    _export_node_name_res = "category"

    def update_new_category(self, data):
        try:
            response = self.client.add(self._pos_model, content=data, options={})
            return response
        except Exception as e:
            print("Response:", e)
