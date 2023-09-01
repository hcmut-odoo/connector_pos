# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import logging
from contextlib import contextmanager
from urllib.parse import urljoin

from ...pospyt.pospyt import (
    PosWebservice,
    PosWebServiceDict,
    PosWebServiceError
)

from requests.exceptions import (
    ConnectionError as ConnError,
    HTTPError,
    RequestException,
    Timeout,
)

from odoo import _, exceptions

from odoo.addons.component.core import AbstractComponent
from odoo.addons.connector.exception import NetworkRetryableError

_logger = logging.getLogger(__name__)


def retryable_error(func):
    """
    Sometimes Jobs may fail because of a network error when calling
    pos api. The job have very good chance to go through later
    So we want to retry it automatically.
    """

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (ConnError, Timeout, HTTPError) as err:
            raise NetworkRetryableError(
                "A network error caused the failure of the job: %s" % str(err)
            )
        except Exception as e:
            raise e

    return wrapper


@contextmanager
def api_handle_errors(message=""):
    """Handle error when calling the API

    It is meant to be used when a model does a direct
    call to a job using the API (not using job.delay()).
    Avoid to have unhandled errors raising on front of the user,
    instead, they are presented as :class:`odoo.exceptions.UserError`.
    """
    if message:
        message = message + "\n\n"
    try:
        yield
    except NetworkRetryableError as err:
        raise exceptions.UserError(_("{}Network Error:\n\n{}").format(message, err))
    except (HTTPError, RequestException, ConnError) as err:
        raise exceptions.UserError(
            _("{}API / Network Error:\n\n{}").format(message, err)
        )

class PosLocation:
    def __init__(self, location, webservice_key):
        """
        Initialize a PosLocation instance.

        Args:
            location (str): The URL of the location or API endpoint.
            webservice_key (str): The webservice key for authentication.

        """
        self.location = location.rstrip("/api") + "/api" if location.endswith("/api") else location + "/api"
        if not self.location.startswith("http"):
            self.location = "http://" + self.location
        self.webservice_key = webservice_key
        self.api_url = self.location


class PosCRUDAdapter(AbstractComponent):
    """External Records Adapter for Pos"""

    _name = "pos.crud.adapter"
    _inherit = ["base.backend.adapter", "base.pos.connector"]
    _usage = "backend.adapter"
    # pylint: disable=method-required-super

    def __init__(self, environment):
        """

        :param environment: current environment (backend, session, ...)
        :type environment: :py:class:`connector.connector.ConnectorEnvironment`
        """
        super().__init__(environment)
        self.pos = PosLocation(
            self.backend_record.location, self.backend_record.webservice_key
        )
        self.client = PosWebServiceDict(
            self.pos.api_url,
            self.pos.webservice_key,
            debug=self.backend_record.debug,
            # verbose=self.backend_record.verbose
        )

    def search(self, filters=None):
        """Search records according to some criterias
        and returns a list of ids"""
        raise NotImplementedError

    def read(self, id_, attributes=None):
        """Returns the information of a record"""
        raise NotImplementedError

    def search_read(self, filters=None):
        """Search records according to some criterias
        and returns their information"""
        raise NotImplementedError

    def create(self, data):
        """Create a record on the external system"""
        raise NotImplementedError

    def write(self, id_, data):
        """Update records on the external system"""
        raise NotImplementedError

    def delete(self, id_, attributes=None):
        """Delete a record on the external system"""
        raise NotImplementedError

    def head(self):
        """HEAD"""
        raise NotImplementedError


class GenericAdapter(AbstractComponent):
    _name = "pos.adapter"
    _inherit = "pos.crud.adapter"

    _model_name = None
    _pos_model = None
    _export_node_name = ""
    _export_node_name_res = ""

    @retryable_error
    def search(self, filters=None):
        """
        Search records based on specified criteria and return a list of matching record IDs.

        Args:
            filters (Optional[Dict[str, Any]]): The criteria or filters to apply during the search.
                Defaults to None.

        Returns:
            list: A list of record IDs that match the search criteria.

        Raises:
            Exception: If an error occurs during the search operation.

        """
        print(
            "method search, model %s, filters %s", self._pos_model, str(filters)
        )
        return self.client.search(self._pos_model, filters)


    @retryable_error
    def read(self, id_, attributes=None):
        """
        Returns the information of a record.

        Args:
            id_ (Union[int, str]): The identifier of the record to retrieve.
            attributes (Optional[Dict[str, Any]]): Additional attributes or options for the retrieval.
                Defaults to None.

        Returns:
            dict: A dictionary containing the information of the record.

        Raises:
            Exception: If an error occurs during the retrieval.

        """
        print(
            f"method read, model {self._pos_model} id {id_}"
        )

        res = self.client.find(self._pos_model, id_)
        return res


    def create(self, attributes=None):
        """
        Create a record on the external system.

        Args:
            attributes (Optional[Dict[str, Any]]): The attributes or fields of the record to create.
                Defaults to None.

        Returns:
            Union[int, dict]: If the creation operation is successful and `_export_node_name_res` is set,
                returns the created record's ID. Otherwise, returns a dictionary with the created record's information.

        Raises:
            Exception: If an error occurs during the creation operation.

        """
        print(
            f"method create, model {self._pos_model}, attributes {str(attributes)}"
        )

        res = self.client.add(
            self._pos_model, {self._export_node_name: attributes}
        )
        if self._export_node_name_res:
            return res["pos"][self._export_node_name_res]["id"]
        return res


    def write(self, id_, attributes=None):
        """
        Update records on the external system.

        Args:
            id_ (Union[int, str]): The identifier of the record to update.
            attributes (Optional[Dict[str, Any]]): The attributes or fields to update in the record.
                Defaults to None.

        Returns:
            Union[int, dict]: If the update operation is successful and `_export_node_name_res` is set,
                returns the updated record's ID. Otherwise, returns a dictionary with the updated record's information.

        Raises:
            Exception: If an error occurs during the update operation.

        """
        attributes["id"] = id_
        print(
            "method write, model %s, attributes %s",
            self._pos_model,
            str(attributes),
        )
        res = self.client.edit(
            self._pos_model, {self._export_node_name: attributes}
        )
        if self._export_node_name_res:
            return res["pos"][self._export_node_name_res]["id"]
        return res

    def delete(self, resource, ids, attributes=None):
        """
        Delete one or more records from the external system.

        Args:
            resource (str): The resource name or endpoint from which to delete the record(s).
            ids (Union[int, str, List[Union[int, str]]]): The identifier(s) of the record(s) to delete. 
                Can be a single identifier or a list of identifiers.
            attributes (Optional[Dict[str, Any]]): Additional attributes or parameters for the delete operation. 
                Defaults to None.

        Returns:
            bool: True if the record(s) were successfully deleted, False otherwise.

        Raises:
            Exception: If an error occurs during the delete operation.

        """
        print(
            "method delete, model %s, ids %s", resource, str(ids)
        )
        # Delete a record(s) on the external system
        return self.client.delete(resource, ids)

    @retryable_error
    def head(self, id_=None):
        """
        Send a HEAD request to retrieve the metadata of a resource.

        Args:
            id_ (Optional[Union[int, str]]): The identifier of the resource. Defaults to None.

        Returns:
            dict: A dictionary containing the metadata of the resource.

        Raises:
            Exception: If an error occurs during the HEAD request.

        """
        """HEAD"""
        return self.client.head(self._pos_model, resource_id=id_)
    
    @retryable_error
    def connect(self):
        """
        Send a POST request with API_KEY to check connection with backend.

        Returns:
            dict: A dictionary containing the message of connection.

        Raises:
            Exception: If an error occurs during the POST request.

        """
        """HEAD"""
        return self.client.connect(self._pos_model)
