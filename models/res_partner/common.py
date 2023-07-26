# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models

from odoo.addons.component.core import Component


class ResPartner(models.Model):
    _inherit = "res.partner"

    pos_bind_ids = fields.One2many(
        comodel_name="pos.res.partner",
        inverse_name="odoo_id",
        string="Pos Bindings",
    )
    # pos_address_bind_ids = fields.One2many(
    #     comodel_name="pos.address",
    #     inverse_name="odoo_id",
    #     string="Pos Address Bindings",
    # )


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
    # backend_id = fields.Many2one(
    #     related="shop_group_id.backend_id",
    #     comodel_name="pos.backend",
    #     string="Pos Backend",
    #     store=True,
    #     readonly=True,
    # )
    # newsletter = fields.Boolean(string="Newsletter")
    # birthday = fields.Date(string="Birthday")

    def import_customers_since(self, backend_record=None, since_date=None, **kwargs):
        """Prepare the import of partners modified on Pos"""
        filters = None
        if since_date:
            filters = {"date": "1", "filter[date_upd]": ">[%s]" % since_date}
        now_fmt = fields.Datetime.now()
        self.env["pos.res.partner"].import_batch(
            backend=backend_record, filters=filters, priority=15, **kwargs
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


class PartnerAdapter(Component):
    _name = "pos.res.partner.adapter"
    _inherit = "pos.adapter"
    _apply_on = "pos.res.partner"
    _pos_model = "customers"
