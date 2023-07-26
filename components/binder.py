# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.component.core import Component


class PosModelBinder(Component):
    """Bind records and give odoo/pos ids correspondence

    Binding models are models called ``pos.{normal_model}``,
    like ``pos.res.partner`` or ``pos.product.product``.
    They are ``_inherits`` of the normal models and contains
    the Pos ID, the ID of the Pos Backend and the additional
    fields belonging to the Pos instance.
    """

    _name = "pos.binder"
    _inherit = ["base.binder", "base.pos.connector"]
    _external_field = "pos_id"

    _apply_on = [
        "pos.store",
        "pos.product.category",
        "pos.res.parner"
    ]
