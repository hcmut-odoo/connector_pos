# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models
import json
from odoo.addons.component.core import Component


class ResPartner(models.Model):
    _inherit = "res.partner"

    pos_bind_ids = fields.One2many(
        comodel_name="pos.res.partner",
        inverse_name="odoo_id",
        string="Pos Bindings",
    )


class PosPartnerMixin(models.AbstractModel):
    _name = "pos.partner.mixin"
    _description = "Mixin for Partner Bindings"

    date_add = fields.Datetime(
        string="Created At (on Pos)",
        readonly=True,
    )
    date_upd = fields.Datetime(
        string="Updated At (on Pos)",
        readonly=True,
    )
    company = fields.Char(string="Partner Company")


class PosResPartner(models.Model):
    _name = "pos.res.partner"
    _inherit = [
        "pos.binding.odoo",
        "pos.partner.mixin",
    ]
    _inherits = {"res.partner": "odoo_id"}
    _description = "Partner pos bindings"

    odoo_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
        required=True,
        ondelete="cascade",
    )

    def import_customers_since(self, backend_record=None, since_date=None, **kwargs):
        """Prepare the import of partners modified on Pos"""   
        now_fmt =  fields.Datetime.now()

        if since_date:
            date = {'start': since_date}
        else:
            date = {'end': now_fmt}


        self.env["pos.res.partner"].import_batch(
            backend=backend_record, filters={'date': date}, priority=5, **kwargs
        )

        backend_record.import_partners_since = now_fmt
        return True


class PosAddressMixin(models.AbstractModel):
    _name = "pos.address.mixin"
    _description = "Mixin for pos adress bindings"

    date_add = fields.Datetime(
        string="Created At (on Pos)",
        readonly=True,
    )
    date_upd = fields.Datetime(
        string="Updated At (on Pos)",
        readonly=True,
    )
    company = fields.Char(string="Address Company")


class PosAddress(models.Model):
    _name = "pos.address"
    _inherit = [
        "pos.binding.odoo",
        "pos.address.mixin",
    ]
    _inherits = {"res.partner": "odoo_id"}
    _rec_name = "odoo_id"
    _description = "Addreses pos bindings"

    pos_partner_id = fields.Many2one(
        comodel_name="pos.res.partner",
        string="Pos Partner",
        required=True,
        ondelete="cascade",
    )
    backend_id = fields.Many2one(
        comodel_name="pos.backend",
        string="Pos Backend",
        related="pos_partner_id.backend_id",
        store=True,
        readonly=True,
    )
    odoo_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
        required=True,
        ondelete="cascade",
    )


class PartnerAdapter(Component):
    _name = "pos.res.partner.adapter"
    _inherit = "pos.adapter"
    _apply_on = "pos.res.partner"
    _pos_model = "user"


class PartnerAddressAdapter(Component):
    _name = "pos.address.adapter"
    _inherit = "pos.adapter"
    _apply_on = "pos.address"
    _pos_model = "address"


