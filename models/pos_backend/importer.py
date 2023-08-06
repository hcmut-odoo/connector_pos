from odoo.addons.component.core import Component


class MetadataBatchImporter(Component):
    """Import the records directly, without delaying the jobs.

    Import the Pos Websites, Shop Groups and Shops

    They are imported directly because this is a rare and fast operation,
    and we don't really bother if it blocks the UI during this time.
    (that's also a mean to rapidly check the connectivity with pos).

    """

    _name = "pos.metadata.batch.importer"
    _inherit = "pos.direct.batch.importer"
    _apply_on = [
        "pos.backend"
    ]
