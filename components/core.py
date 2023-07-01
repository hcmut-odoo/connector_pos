from odoo.addons.component.core import AbstractComponent


class BasePosConnectorComponent(AbstractComponent):
    """Base Pos Connector Component

    All components of this connector should inherit from it.
    """

    _name = "base.pos.connector"
    _inherit = "base.connector"
    _collection = "pos.backend"
