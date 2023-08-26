# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import threading
from contextlib import closing, contextmanager

import odoo
from odoo import _

from odoo.addons.component.core import AbstractComponent
from odoo.addons.queue_job.exception import FailedJobError, RetryableJobError

_logger = logging.getLogger(__name__)

RETRY_ON_ADVISORY_LOCK = 1  # seconds
RETRY_WHEN_CONCURRENT_DETECTED = 1  # seconds


def import_record():
    pass


def import_batch():
    pass


class PosBaseImporter(AbstractComponent):
    _name = "pos.base.importer"
    _inherit = ["base.importer", "base.pos.connector"]

    def _import_dependency(
        self, pos_id, binding_model, importer_class=None, always=False, **kwargs
    ):
        """
        Import a dependency. The importer class is a subclass of
        ``PosImporter``. A specific class can be defined.

        :param pos_id: ID of the POS ID to import.
        :type pos_id: int | str
        :param binding_model: Name of the binding model for the relation.
        :type binding_model: str | unicode
        :param importer_class: Class or parent class to use for the import.
                            By default: PosImporter.
        :type importer_class: :py:class:`odoo.addons.connector.connector.MetaConnectorUnit`
        :param always: If True, the record is updated even if it already exists.
                    It is still skipped if it has not been modified on Pos.
        :type always: bool
        :param kwargs: Additional keyword arguments passed to the importer.
        """
        if not pos_id:
            return
        if importer_class is None:
            importer_class = PosImporter
        binder = self.binder_for(binding_model)
        if always or not binder.to_internal(pos_id):
            importer = self.component(usage="record.importer", model_name=binding_model)
            importer.run(pos_id, **kwargs)

class PosImporter(AbstractComponent):
    """Base importer for Pos"""

    _name = "pos.importer"
    _inherit = "pos.base.importer"
    _usage = "record.importer"

    def __init__(self, environment):
        """
        Initialize the object.

        :param environment: Current environment (backend, session, ...)
        :type environment: :py:class:`connector.connector.ConnectorEnvironment`
        """
        super().__init__(environment)
        self.pos_id = None
        self.pos_record = None


    def _get_pos_data(self):
        """
        Return the raw Pos data for `self.pos_id`.
        """

        return self.backend_adapter.read(self.pos_id, {'action': 'find'})


    def _has_to_skip(self, binding=False):
        """
        Check if the import can be skipped.

        :param binding: Flag indicating whether the import is for binding.
        :type binding: bool
        :return: True if the import can be skipped, False otherwise.
        :rtype: bool
        """
        return False

    def _import_dependencies(self):
        """Import the dependencies for the record"""
        return

    def _map_data(self):
        """
        Map the data and return an instance of `odoo.addons.connector.unit.mapper.MapRecord`.

        :return: An instance of `odoo.addons.connector.unit.mapper.MapRecord`.
        """
        return self.mapper.map_record(self.pos_record)


    def _validate_data(self, data):
        """
        Validate the data before import.

        Proactively check if the values to import are correct before calling
        `Model.create` or `Model.update`. Raise `InvalidDataError` if any
        required fields are missing or the data is invalid.

        :param data: The data to validate.
        :type data: dict
        :raises: `InvalidDataError` if the data is invalid.
        """
        return

    def _get_binding(self):
        """
        Get the Odoo ID associated with the POS ID.

        :return: The Odoo ID corresponding to the POS ID.
        """
        return self.binder.to_internal(self.pos_id)

    def _context(self, **kwargs):
        """
        Create a new context dictionary with additional keyword arguments.

        :param kwargs: Additional key-value pairs to be added to the context.
        :return: The updated context dictionary.
        :rtype: dict
        """
        return dict(self._context, connector_no_export=True, **kwargs)

    def _create_context(self):
        """
        Create and return a new context dictionary for the connector.

        :return: The context dictionary with the "connector_no_export" flag set to True.
        :rtype: dict
        """
        return {"connector_no_export": True}

    def _create_data(self, map_record):
        """
        Create and return the data for record creation.

        :param map_record: The mapped record.
        :type map_record: odoo.addons.connector.unit.mapper.MapRecord
        :return: The data for record creation.
        :rtype: dict
        """
        return map_record.values(for_create=True)


    def _update_data(self, map_record):
        """
        Create and return the data for record update.

        :param map_record: The mapped record.
        :type map_record: odoo.addons.connector.unit.mapper.MapRecord
        :return: The data for record update.
        :rtype: dict
        """
        return map_record.values()


    def _create(self, data):
        """
        Create the Odoo record.

        :param data: The data for record creation.
        :type data: dict
        :return: The created binding record.
        """
        # Special check on data before import
        self._validate_data(data)
        binding = self.model.with_context(**self._create_context()).create(data)
        return binding

    def _update(self, binding, data):
        """
        Update the Odoo record.

        :param binding: The binding record to update.
        :param data: The updated data for the record.
        :type binding: odoo.models.Model
        :type data: dict
        """
        # Special check on data before import
        self._validate_data(data)
        binding.with_context(connector_no_export=True).write(data)
        _logger.debug("%d updated from POS %s", binding.id, self.pos_id)

    def _before_import(self):
        """
        Perform actions before the import, when Pos data is available.
        """
        pass

    def _after_import(self, binding):
        """
        Perform actions at the end of the import process.

        :param binding: The created/updated binding record.
        """
        pass


    @contextmanager
    def do_in_new_connector_env(self, model_name=None):
        """
        Context manager that yields a new connector environment using a new Odoo Environment.

        This context manager is used to create a new connector environment with a new PG transaction.
        It can be used to perform preemptive checks in a separate transaction, for example, to see if
        another transaction has already completed the required work.

        :param model_name: The name of the model associated with the new connector environment.
        :type model_name: str
        :yield: The new connector environment within the context.
        """
        with odoo.api.Environment.manage():
            registry = odoo.modules.registry.Registry(self.env.cr.dbname)
            with closing(registry.cursor()) as cr:
                try:
                    new_env = odoo.api.Environment(cr, self.env.uid, self.env.context)
                    with self.backend_record.with_env(new_env).work_on(self.model._name) as work2:
                        yield work2
                except BaseException:
                    cr.rollback()
                    raise
                else:
                    # Despite what pylint says, this a perfectly valid commit (in a new cursor).
                    # Disable the warning.
                    self.env["base"].flush()
                    if not getattr(threading.currentThread(), "testing", False):
                        cr.commit()

    def _check_in_new_connector_env(self):
        """
        Check for concurrent imports in a new connector environment.

        This method is used to handle concurrent import scenarios by performing a check within a new connector environment
        using a separate PostgreSQL transaction.

        The check is performed by retrieving the binder for the current model and checking if there is already an internal
        record corresponding to the given POS ID. If a record is found, a RetryableJobError is raised, indicating a
        concurrent error. This error is designed to trigger a retry of the job later.

        :raises RetryableJobError: If a concurrent import is detected.
        """
        with self.do_in_new_connector_env():
            # Even when we use an advisory lock, we may have
            # concurrent issues.
            # Explanation:
            # We import Partner A and B, both of them import a
            # partner category X.
            #
            # The squares represent the duration of the advisory
            # lock, the transactions starts and ends on the
            # beginnings and endings of the 'Import Partner'
            # blocks.
            # T1 and T2 are the transactions.
            #
            # ---Time--->
            # > T1 /------------------------\
            # > T1 | Import Partner A       |
            # > T1 \------------------------/
            # > T1        /-----------------\
            # > T1        | Imp. Category X |
            # > T1        \-----------------/
            #                     > T2 /------------------------\
            #                     > T2 | Import Partner B       |
            #                     > T2 \------------------------/
            #                     > T2        /-----------------\
            #                     > T2        | Imp. Category X |
            #                     > T2        \-----------------/
            #
            # As you can see, the locks for Category X do not
            # overlap, and the transaction T2 starts before the
            # commit of T1. So no lock prevents T2 to import the
            # category X and T2 does not see that T1 already
            # imported it.
            #
            # The workaround is to open a new DB transaction at the
            # beginning of each import (e.g. at the beginning of
            # "Imp. Category X") and to check if the record has been
            # imported meanwhile. If it has been imported, we raise
            # a Retryable error so T2 is rollbacked and retried
            # later (and the new T3 will be aware of the category X
            # from the its inception).
            binder = self.binder_for(model=self.model._name)
            if binder.to_internal(self.pos_id):
                raise RetryableJobError(
                    "Concurrent error. The job will be retried later",
                    seconds=RETRY_WHEN_CONCURRENT_DETECTED,
                    ignore_retry=True,
                )

    def run(self, pos_id, **kwargs):
        """
        Run the synchronization process.

        :param pos_id: Identifier of the record on Pos.
        :param kwargs: Additional keyword arguments.
        :return: The result of the synchronization process. Returns `None` if the synchronization is skipped or
                an error occurs during the process.
        :rtype: Any
        """
        self.pos_id = pos_id
        lock_name = "import({}, {}, {}, {})".format(
            self.backend_record._name,
            self.backend_record.id,
            self.model._name,
            self.pos_id,
        )
        # Keep a lock on this import until the transaction is committed
        self.advisory_lock_or_retry(lock_name, retry_seconds=RETRY_ON_ADVISORY_LOCK)
        if not self.pos_record:
            self.pos_record = self._get_pos_data()
        # put back a not active test domain so the rest of the import process
        # happen in normal conditions
        binding = self._get_binding().with_context(active_test=True)
        if not binding:
            self._check_in_new_connector_env()

        skip = self._has_to_skip(binding=binding)
        if skip:
            return skip

        # import the missing linked resources
        self._import_dependencies()

        self._import(binding, **kwargs)

    def _import(self, binding, **kwargs):
        """
        Import the external record.

        This method is responsible for importing the external record into the Odoo system. It can be inherited and modified
        to implement custom behavior, such as modifying the session or changing values in the context.

        :param binding: The existing binding record, if it exists.
        :param kwargs: Additional keyword arguments passed to the method.
        """

        map_record = self._map_data()
        if binding:
            record = self._update_data(map_record)
        else:
            record = self._create_data(map_record)

        # Perform a special check on the data before the import
        self._validate_data(record)

        if binding:
            self._update(binding, record)
        else:
            binding = self._create(record)

        self.binder.bind(self.pos_id, binding)

        self._after_import(binding)



class BatchImporter(AbstractComponent):
    """The role of a BatchImporter is to search for a list of
    items to import, then it can either import them directly or delay
    the import of each item separately.
    """

    _name = "pos.batch.importer"
    _inherit = ["base.importer", "base.pos.connector"]
    _usage = "batch.importer"

    page_size = 1000

    def run(self, filters=None, **kwargs):
        """
        Run the synchronization process.

        :param filters: Optional filters to apply during the synchronization. Default is None.
        :type filters: dict or None
        :param kwargs: Additional keyword arguments.
        """
        print("1st run")
        if filters is None:
            filters = {}
        if "limit" in filters:
            self._run_page(filters, **kwargs)
            return

        # Make a copy of filters to prevent applying the parameters to other batch imports
        filters = filters.copy()
        # page_number = 0
        # filters["limit"] = "%d" % (page_number * self.page_size, self.page_size)
        # record_ids = self._run_page(filters, **kwargs)
        # while len(record_ids) == self.page_size:
        #     page_number += 1
        #     filters["limit"] = "%d,%d" % (page_number * self.page_size, self.page_size)
        self._run_page(filters, **kwargs)

    def _run_page(self, filters, **kwargs):
        """
        Process a single page of records during the synchronization.

        :param filters: Filters to apply for retrieving the records.
        :type filters: dict
        :param kwargs: Additional keyword arguments.
        :return: The list of record IDs processed in this page.
        :rtype: list
        """
        print("access _run_page")
        print("filter _run_page", filters)
        record_ids = self.backend_adapter.search(filters)
        print("record_ids", record_ids)
        for record_id in record_ids:
            print("1st _run_page")
            self._import_record(record_id, **kwargs)
        print("end _run_page")
        return record_ids

    def _import_record(self, record):
        """
        Import a record directly or delay the import of the record.

        :param record: The record to be imported.
        :raises: NotImplementedError
        """
        raise NotImplementedError

class DirectBatchImporter(AbstractComponent):
    """
    Batch importer for importing Pos Shop Groups and Shops directly.

    This component is responsible for importing Pos Shop Groups and Shops directly 
    from the backend system. It is designed for rare and fast operations that are 
    typically performed from the user interface (UI).

    This class inherits from `pos.batch.importer` and provides the necessary 
    implementation for the batch import functionality.

    :ivar _name: Name of the component.
    :vartype _name: str
    :ivar _inherit: Inherited component.
    :vartype _inherit: str
    :ivar _model_name: Name of the Odoo model associated with the import.
    :vartype _model_name: str | None
    """

    _name = "pos.direct.batch.importer"
    _inherit = "pos.batch.importer"
    _model_name = None
    
    def _import_record(self, external_id):
        """
        Import a record directly.

        :param external_id: The external ID of the record to be imported.
        """
        self.env[self.model._name].import_record(
            backend=self.backend_record, pos_id=external_id
        )

class DelayedBatchImporter(AbstractComponent):
    """
    Batch importer for delaying the import of records.

    This component is responsible for delaying the import of records from the backend
    system. It is designed to handle cases where the import process needs to be scheduled 
    for a later time or when additional processing is required before the actual import.

    This class inherits from `pos.batch.importer` and provides the necessary 
    implementation for the batch import functionality.

    :ivar _name: Name of the component.
    :vartype _name: str
    :ivar _inherit: Inherited component.
    :vartype _inherit: str
    :ivar _model_name: Name of the Odoo model associated with the import.
    :vartype _model_name: str | None
    """

    _name = "pos.delayed.batch.importer"
    _inherit = "pos.batch.importer"
    _model_name = None

    def _import_record(self, external_id, **kwargs):
        """
        Delay the import of the records.

        :param external_id: The external ID of the record to be imported.
        :param kwargs: Additional keyword arguments for configuring the delayed import.
        """
        priority = kwargs.pop("priority", None)
        eta = kwargs.pop("eta", None)
        max_retries = kwargs.pop("max_retries", None)
        description = kwargs.pop("description", None)
        channel = kwargs.pop("channel", None)
        identity_key = kwargs.pop("identity_key", None)

        self.env[self.model._name].with_delay(
            priority=priority,
            eta=eta,
            max_retries=max_retries,
            description=description,
            channel=channel,
            identity_key=identity_key,
        ).import_record(
            backend=self.backend_record, pos_id=external_id, **kwargs
        )