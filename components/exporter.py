# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import threading
from contextlib import contextmanager

import psycopg2

from odoo import _, exceptions

from odoo.addons.component.core import AbstractComponent
from odoo.addons.connector.exception import RetryableJobError

_logger = logging.getLogger(__name__)


# Exporters for Pos.
# In addition to its export job, an exporter has to:
# * Check in Pos if the record has been updated more recently than the
#   last sync date. If yes, delay an import.
# * Call the ``bind`` method of the binder to update the last sync date.


class PosBaseExporter(AbstractComponent):
    """Base exporter for Pos"""

    _name = "pos.base.exporter"
    _inherit = ["base.exporter", "base.pos.connector"]
    _usage = "record.exporter"

    def __init__(self, environment):
        """
        Initialize a new instance of the class.

        Args:
            environment (:py:class:`connector.connector.ConnectorEnvironment`):
                The current environment (backend, session, ...).

        """
        super().__init__(environment)
        self.pos_id = None
        self.binding_id = None


    def _get_binding(self):
        """
        Return the raw Odoo data for the binding specified by ``self.binding_id``.

        Returns:
            Record: The raw Odoo data for the binding.

        """
        return self.model.browse(self.binding_id)


    def run(self, binding, *args, **kwargs):
        """
        Run the synchronization.

        Args:
            binding (:py:class:`binding.BaseBinding`): The binding record to export.

        Returns:
            Any: The result of the synchronization operation.

        """
        self.binding_id = binding.id
        self.binding = binding
        self.pos_id = self.binder.to_external(self.binding)
        result = self._run(*args, **kwargs)

        self.binder.bind(self.pos_id, self.binding)
        # Commit so we keep the external ID if several cascading exports
        # are called and one of them fails
        if not getattr(threading.currentThread(), "testing", False):
            self.env.cr.commit()
        self._after_export()
        return result


    def _run(self, *args, **kwargs):
        """
        Flow of the synchronization, implemented in inherited classes.

        Raises:
            NotImplementedError: This method should be implemented in the inherited classes.

        """
        raise NotImplementedError


    def _after_export(self):
        """
        Create records of dependent Pos objects.

        This method is called after the export operation to create records of dependent Pos objects.

        """
        return



class PosExporter(AbstractComponent):
    """A common flow for the exports to Pos"""

    _name = "pos.exporter"
    _inherit = "pos.base.exporter"

    _odoo_field = "odoo_id"

    def __init__(self, environment):
        """
        Initialize a new instance of the class.

        Args:
            environment (:py:class:`connector.connector.ConnectorEnvironment`):
                The current environment (backend, session, ...).

        """
        super().__init__(environment)
        self.binding = None


    def _has_to_skip(self, binding=False):
        """
        Return True if the export can be skipped.

        Args:
            binding (bool): Indicates whether the binding should be considered.
                Defaults to False.

        Returns:
            bool: True if the export can be skipped, False otherwise.

        """
        return False


    @contextmanager
    def _retry_unique_violation(self):
        """
        Context manager: catch Unique constraint error and retry the job later.

        When executing several job workers concurrently, it can happen that two jobs are
        attempting to create the same record at the same time, resulting in a
        Unique constraint violation error. In that case, we retry the import later.

        Yields:
            None: The context manager yields control.

        Raises:
            RetryableJobError: If a database error other than UNIQUE_VIOLATION occurs.
                The error message explains that the failure was likely caused by two concurrent
                jobs trying to create the same record.

        """
        try:
            yield
        except psycopg2.IntegrityError as err:
            if err.pgcode == psycopg2.errorcodes.UNIQUE_VIOLATION:
                raise RetryableJobError(
                    "A database error caused the failure of the job:\n"
                    f"{err}\n\n"
                    "This error is likely due to two concurrent jobs attempting "
                    "to create the same record. The job will be retried later."
                )
            else:
                raise


    def _get_or_create_binding(
        self,
        relation,
        binding_model,
        binding_field_name="pos_bind_ids",
        bind_values=None,
    ):
        """
        Get or create the binding record for the relation.

        Args:
            relation: The relation record for which to get or create the binding.
            binding_model (str): The name of the binding model.
            binding_field_name (str): The name of the binding field. Defaults to "pos_bind_ids".
            bind_values (dict): Additional values to set on the binding record. Defaults to None.

        Returns:
            :py:class:`odoo.models.Model`: The binding record.

        """
        binding = None
        wrap = relation._name != binding_model  # wrap is True if relation is not the binding model
        if wrap and hasattr(relation, binding_field_name):
            domain = [
                (self._odoo_field, "=", relation.id),
                ("backend_id", "=", self.backend_record.id),
            ]
            model = self.env[binding_model].with_context(active_test=False)
            binding = model.search(domain)
            if binding:
                binding.ensure_one()
            else:
                _bind_values = {
                    "backend_id": self.backend_record.id,
                    self._odoo_field: relation.id,
                }
                _bind_values.update(bind_values or {})
                with self._retry_unique_violation():
                    model_c = (
                        self.env[binding_model]
                        .sudo()
                        .with_context(connector_no_export=True)
                    )
                    binding = model_c.create(_bind_values)
                    if not getattr(threading.currentThread(), "testing", False):
                        # Eager commit to avoid conflicts during export
                        model_c._cr.commit()  
        else:
            binding = relation
        return binding


    def _export_dependency(
        self,
        relation,
        binding_model,
        exporter_class=None,
        component_usage="record.exporter",
        binding_field_name="pos_bind_ids",
        bind_values=None,
        force_sync=False,
    ):
        """
        Export a dependency record to the external system.

        The exporter class is a subclass of `PosExporter`, but a more precise
        class can be defined.

        When a binding does not exist yet, it is automatically created.

        **Warning**: A commit is performed at the end of exporting each dependency
        to ensure that the record's external ID is preserved. Therefore, you must
        take care not to modify the Odoo database except when writing back the
        external ID or any other external data that needs to be kept on this side.
        This method should be called only at the beginning of the exporter
        synchronization (in `~._export_dependencies`) and should not write data
        that should be rolled back in case of an error.

        Args:
            relation: The record to export if it has not been exported already.
            binding_model (str): The name of the binding model for the relation.
            exporter_class: The class or parent class of `PosExporter` to use
                for the export. Defaults to None.
            component_usage (str): The component usage to look for in order to find
                the Component for the export. Defaults to "record.exporter".
            binding_field_name (str): The name of the one2many field towards the bindings.
                The default value is "pos_bind_ids".
            bind_values (dict): Override values used to create a new binding. Defaults to None.
            force_sync (bool): Whether to force the update of an already synchronized item.
                Defaults to False.

        Returns:
            :py:class:`odoo.models.Model`: The binding record.

        """
        if not relation:
            return

        binding = self._get_or_create_binding(
            relation,
            binding_model,
            binding_field_name=binding_field_name,
            bind_values=bind_values,
        )

        rel_binder = self.binder_for(binding_model)

        if not rel_binder.to_external(binding) or force_sync:
            exporter = self.component(usage=component_usage, model_name=binding_model)
            exporter.run(binding)
        return binding


    def _export_dependencies(self):
        """
        Export the dependencies for the record.

        This method is responsible for exporting the dependencies of the record
        to the external system. It should be implemented in the subclass.

        Returns:
            None
        """
        return


    def _map_data(self):
        """
        Convert the external record to Odoo.

        This method is responsible for mapping the external record to the corresponding
        Odoo record. It uses the mapper defined for the exporter to perform the mapping.

        Returns:
            dict: The mapped data as a dictionary representing the Odoo record.
        """
        return self.mapper.map_record(self.binding)


    def _validate_data(self, data):
        """
        Check if the values to import are correct.

        This method proactively checks if the values in the data to be imported are correct
        and complete before performing the actual import using the `Model.create` or
        `Model.update` methods.

        If any required fields are missing or if the data is invalid, this method should raise
        an `InvalidDataError` to indicate the validation failure.

        Args:
            data (dict): The data to be imported.

        Raises:
            InvalidDataError: If the data is not valid or complete.

        Returns:
            None
        """
        return


    def _create(self, data):
        """
        Create the Pos record.

        This method is responsible for creating the Pos record in the external system
        using the provided data.

        Args:
            data (dict): The data for creating the Pos record.

        Returns:
            dict: The created Pos record data in the external system.
        """
        return self.backend_adapter.create(data)


    def _update(self, data):
        """
        Update a Pos record.

        This method is responsible for updating the Pos record in the external system
        with the provided data.

        Args:
            data (dict): The updated data for the Pos record.

        Returns:
            dict: The updated Pos record data in the external system.
        """
        assert self.pos_id
        return self.backend_adapter.write(self.pos_id, data)


    def _lock(self):
        """
        Lock the binding record.

        This method locks the binding record to ensure that only one export job is running
        for this record when concurrent jobs need to export the same record.

        When multiple concurrent jobs try to export the same record, the first job will
        successfully lock and proceed, while the other jobs will fail to lock and will be
        retried later.

        This behavior also applies when exporting multiple levels of dependencies with the
        `_export_dependencies` method. Each level will set its own lock on the binding record
        it needs to export.

        The method uses `NO KEY UPDATE` to avoid FK accesses being blocked in PostgreSQL
        versions > 9.3.

        Raises:
            RetryableJobError: If a concurrent job is already exporting the same record,
                indicating that the current job should be retried later.

        """
        sql = (
            "SELECT id FROM %s WHERE ID = %%s FOR NO KEY UPDATE NOWAIT"
            % self.model._table
        )
        try:
            self.env.cr.execute(sql, (self.binding_id,), log_exceptions=False)
        except psycopg2.OperationalError:
            _logger.info(
                "A concurrent job is already exporting the same "
                "record (%s with id %s). Job delayed later.",
                self.model._name,
                self.binding_id,
            )
            raise RetryableJobError(
                "A concurrent job is already exporting the same record "
                "(%s with id %s). The job will be retried later."
                % (self.model._name, self.binding_id)
            )


    def _run(self, fields=None, **kwargs):
        """
        Flow of the synchronization, implemented in inherited classes.

        This method represents the main flow of the synchronization process and is
        implemented in the inherited classes. It performs the following steps:

        - Asserts that the binding ID and binding object are present.
        - Checks if the record to export still exists. If not, returns an appropriate message.
        - Checks if the export can be skipped based on certain conditions. If so, returns.
        - Exports the missing linked resources by calling the `_export_dependencies` method.
        - Acquires a lock on the binding record to prevent other jobs from exporting the same record.
        - Maps the data from the binding record to the external system using the `_map_data` method.
        - Checks if the `pos_id` is already assigned. If it is, updates the corresponding record
        in the external system with the mapped data.
        - If `pos_id` is not assigned, creates a new record in the external system with the mapped data.
        - Validates the exported data using the `_validate_data` method.
        - Returns a message indicating the successful export with the ID of the exported record.

        Args:
            fields (list): A list of fields to include in the export. Default is None.
            **kwargs: Additional keyword arguments.

        Returns:
            str: A message indicating the success of the export with the ID of the exported record.

        Raises:
            exceptions.Warning: If the record on the Pos system has not been created.

        """
        assert self.binding_id
        assert self.binding

        if not self.binding.exists():
            return _("Record to export no longer exists.")

        if self._has_to_skip():
            return

        # Export the missing linked resources
        self._export_dependencies()

        # Prevent other jobs from exporting the same record
        # The lock will be released on commit (or rollback)
        self._lock()

        map_record = self._map_data()

        if self.pos_id:
            record = map_record.values()
            if not record:
                return _("Nothing to export.")
            # Special check on data before export
            self._validate_data(record)
            self._update(record)
        else:
            record = map_record.values(for_create=True)
            if not record:
                return _("Nothing to export.")
            # Special check on data before export
            self._validate_data(record)
            self.pos_id = self._create(record)
            if self.pos_id == 0:
                raise exceptions.Warning(_("Record on Pos has not been created"))

        message = _("Record exported with ID %s on Pos.")
        return message % self.pos_id

