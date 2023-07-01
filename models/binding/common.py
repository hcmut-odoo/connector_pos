from odoo import api, fields, models

from odoo.addons.connector.exception import RetryableJobError


class PosBinding(models.AbstractModel):
    """
    The `PosBinding` class is an abstract model used for binding records 
    between Odooand an external Point of Sale (POS) system.

    It serves as a base class for concrete models that represent specific 
    POS entities such as products, customers, orders, etc. The purpose of 
    this class is to provide common functionality and structure for handling 
    the synchronization of data between Odoo and the POS system.

    By inheriting from `PosBinding`, concrete models can define their specific 
    fields, constraints, and methods for importing, exporting, and synchronizing 
    records with the POS system.

    Example usage:
    ```python
    class PosProductBinding(models.Model):
        _name = "pos.product.binding"
        _inherit = "pos.binding"
        _description = "POS Product Binding"

        # Define specific fields and methods for product bindings
        ...
    ```

    Attributes:
    - `_name`: The internal technical name of the model.
    - `_inherit`: The parent model to inherit from (in this case, "external.binding").
    - `_description`: A human-readable description of the model.

    Fields:
    - `backend_id`: A many-to-one field that represents the POS backend associated 
    with the binding.
    - `active`: A boolean field indicating whether the binding is active.
    - `pos_id`: An integer field representing the ID of the record on the POS system.
    - `no_export`: A boolean field indicating whether the record should be exported
    to the POS system.

    Constraints:
    - `_sql_constraints`: A list of SQL constraints to enforce uniqueness of records 
    based on the combination of `backend_id` and `pos_id`.

    Methods:
    - `check_active`: Checks if the associated POS backend is active. 
    Raises `RetryableJobError` if it is inactive.
    - `import_record`: Imports a record from the POS system based on the given 
    POS backend and POS ID.
    - `import_batch`: Prepares a batch import of records from the POS system 
    based on the given POS backend and optional filters.
    - `export_record`: Exports a record to the POS system.
    - `export_delete_record`: Deletes a record on the POS system.
    - `resync`: Resynchronizes the record with the POS system by importing or 
    updating it.

    Note: This is an abstract class and should not be instantiated directly.
    """
    _name = "pos.binding"
    _inherit = "external.binding"
    _description = "Pos Binding (abstract)"

    backend_id = fields.Many2one(
        comodel_name="pos.backend",
        string="Pos Backend",
        required=True,
        ondelete="restrict",
    )
    active = fields.Boolean(string="Active", default=True)
    pos_id = fields.Integer("ID on Pos")
    no_export = fields.Boolean("No export to Pos")

    _sql_constraints = [
        (
            "pos_uniq",
            "unique(backend_id, pos_id)",
            "A record with the same ID on Pos already exists.",
        ),
    ]

    def check_active(self, backend):
        """
        Check if the backend is active.

        :param backend: Pos backend record
        :raises RetryableJobError: If the backend is inactive
        """
        if not backend.active:
            raise RetryableJobError(
                "Backend %s is inactive. Please consider changing this. "
                "The job will be retried later." % (backend.name,)
            )

    @api.model
    def import_record(self, backend, pos_id, force=False):
        """
        Import a record from Pos.

        :param backend: Pos backend record
        :param pos_id: ID of the record on Pos
        :param force: Force import even if the record already exists
        :return: Imported record
        """
        self.check_active(backend)
        with backend.work_on(self._name) as work:
            importer = work.component(usage="record.importer")
            return importer.run(pos_id, force=force)

    @api.model
    def import_batch(self, backend, filters=None, **kwargs):
        """
        Prepare a batch import of records from Pos.

        :param backend: Pos backend record
        :param filters: Filters to apply during the import
        :param kwargs: Additional keyword arguments
        :return: Result of the batch import
        """
        self.check_active(backend)
        if filters is None:
            filters = {}
        with backend.work_on(self._name) as work:
            importer = work.component(usage="batch.importer")
            return importer.run(filters=filters, **kwargs)

    def export_record(self, fields=None):
        """
        Export a record to Pos.

        :param fields: Fields to export (optional)
        :return: Exported record
        """
        self.ensure_one()
        self.check_active(self.backend_id)
        with self.backend_id.work_on(self._name) as work:
            exporter = work.component(usage="record.exporter")
            return exporter.run(self, fields)

    def export_delete_record(self, backend, external_id, attributes=None):
        """
        Delete a record on Pos.

        :param backend: Pos backend record
        :param external_id: External ID of the record on Pos
        :param attributes: Attributes related to the deletion (optional)
        :return: Result of the deletion
        """
        self.check_active(backend)
        with backend.work_on(self._name) as work:
            deleter = work.component(usage="record.exporter.deleter")
            return deleter.run(external_id, attributes)

    def resync(self):
        """
        Resynchronize the record with Pos.

        This method imports the record if it doesn't exist on Pos or updates
        it if it already exists.

        :return: True if the resynchronization was successful
        """
        func = self.import_record
        if self.env.context.get("connector_delay"):
            func = self.with_delay(priority=5).import_record
        for record in self:
            func(record.backend_id, record.pos_id)
        return True

class PosBindingOdoo(models.AbstractModel):
    """
    The `PosBindingOdoo` class is an abstract model used for binding records
    between Odoo and an external Point of Sale (POS) system with an additional
    binding to Odoo.

    It inherits from the `PosBinding` class and extends it to include a many-to-one
    reference to an Odoo record. This allows for a tighter integration between
    Odoo and the POS system by maintaining a direct link to the corresponding
    Odoo record.

    Concrete models that represent specific POS entities and require an Odoo
    binding can inherit from `PosBindingOdoo` and define their specific fields,
    constraints, and methods.

    Example usage:
    ```python
    class PosProductBindingOdoo(models.Model):
        _name = "pos.product.binding.odoo"
        _inherit = "pos.binding.odoo"
        _description = "POS Product Binding with Odoo binding"

        # Define specific fields and methods for product bindings with Odoo binding
        ...
    ```

    Attributes:
    - `_name`: The internal technical name of the model.
    - `_inherit`: The parent model to inherit from (in this case, "pos.binding").
    - `_description`: A human-readable description of the model.

    Fields:
    - `odoo_id`: A reference field that represents the binding to the Odoo record.
    - `backend_id`: A many-to-one field that represents the POS backend associated
    with the binding.
    - `active`: A boolean field indicating whether the binding is active.
    - `pos_id`: An integer field representing the ID of the record on the POS system.
    - `no_export`: A boolean field indicating whether the record should be exported
    to the POS system.

    Constraints:
    - `_sql_constraints`: A list of SQL constraints to enforce uniqueness of
    records based on the combination of `backend_id` and `odoo_id`.

    Note: This is an abstract class and should not be instantiated directly.
    """
    _name = "pos.binding.odoo"
    _inherit = "pos.binding"
    _description = "Pos Binding with Odoo binding (abstract)"

    def _get_selection(self):
        """
        Get the selection options for the `odoo_id` field.

        :return: List of model and name tuples for all Odoo models
        """
        records = self.env["ir.model"].search([])
        return [(r.model, r.name) for r in records] + [("", "")]

    odoo_id = fields.Reference(
        required=True,
        ondelete="cascade",
        string="Odoo binding",
        selection=_get_selection,
    )

    _sql_constraints = [
        (
            "pos_erp_uniq",
            "unique(backend_id, odoo_id)",
            "An ERP record with the same ID already exists on Pos.",
        ),
    ]
