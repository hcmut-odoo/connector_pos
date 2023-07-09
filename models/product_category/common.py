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
    :param description: The HTML field containing the description from the POS.
    :type description: odoo.fields.Html
    :param link_rewrite: The char field representing the friendly URL of the POS binding.
    :type link_rewrite: odoo.fields.Char
    :param meta_description: The char field representing the meta description of the POS binding.
    :type meta_description: odoo.fields.Char
    :param meta_keywords: The char field representing the meta keywords of the POS binding.
    :type meta_keywords: odoo.fields.Char
    :param meta_title: The char field representing the meta title of the POS binding.
    :type meta_title: odoo.fields.Char
    :param active: The boolean field indicating whether the POS binding is active or not.
    :type active: odoo.fields.Boolean
    :param position: The integer field indicating the position of the POS binding.
    :type position: odoo.fields.Integer
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
    description = fields.Html(
        string="Description",
        translate=True,
        help="HTML description from the POS",
    )
    link_rewrite = fields.Char(string="Friendly URL", translate=True)
    meta_description = fields.Char(string="Meta description", translate=True)
    meta_keywords = fields.Char(string="Meta keywords", translate=True)
    meta_title = fields.Char(string="Meta title", translate=True)
    active = fields.Boolean(string="Active", default=True)
    position = fields.Integer(string="Position")

    def import_product_categories(self, backend, since_date=None, **kwargs):
        filters = None
        now_fmt = fields.Datetime.now()
        if since_date:
            filters = {'updated_at': {'operator': 'gt', 'value': since_date}}
        else:
            filters = {'updated_at': {'operator': 'lt', 'value': now_fmt}}

        self.env["pos.product.category"].import_batch(
            backend, filters=filters, priority=10
        )
        backend.import_categories_from_date = now_fmt
        return True

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
    _pos_model = "categories"
    _export_node_name = "category"
    _export_node_name_res = "category"
