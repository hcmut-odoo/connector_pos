# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import _, exceptions

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class AutoMatchingImporter(Component):
    _name = "pos.auto.matching.importer"
    _inherit = "pos.importer"
    _usage = "auto.matching.importer"

    _erp_field = None
    _pos_field = None
    _copy_fields = []
    _filters = None

    def _compare_function(self, pos_val, erp_val, pos_dict, erp_dict):
        """
        Compare function to determine if the POS value and ERP value match.
        Implement the comparison logic based on your specific requirements.

        Args:
            pos_val (any): Value from the POS system.
            erp_val (any): Value from the ERP system.
            pos_dict (dict): Dictionary containing other POS field values.
            erp_dict (dict): Dictionary containing other ERP field values.

        Returns:
            bool: True if the values match, False otherwise.
        """
        # TODO: Implement the comparison logic based on your specific requirements
        # Placeholder implementation that compares the values directly
        return pos_val == erp_val


    def run(self):
        """
        This method performs synchronization between Odoo and the POS system.
        It maps POS entries to corresponding Odoo entries based on certain criteria.
        """
        _logger.debug(
            "[%s] Starting synchronization between Odoo and POS" % self.model._name
        )
        
        # Initialize counters
        nr_pos_already_mapped = 0
        nr_pos_mapped = 0
        nr_pos_not_mapped = 0
        
        # Get the model name and record name of the corresponding ERP system
        erp_model_name = next(iter(self.model._inherits))
        erp_rec_name = self.env[erp_model_name]._rec_name
        
        # Get the model with inactive records from the ERP system
        model = self.env[erp_model_name].with_context(active_test=False)
        
        # Retrieve all ERP system IDs
        erp_ids = model.search([])
        erp_list_dict = erp_ids.read()
        
        # Retrieve the adapter for POS system integration
        adapter = self.component(usage="backend.adapter")
        
        # Get the POS IDs using the specified filters
        pos_ids = adapter.search(self._filters)
        if not pos_ids:
            raise exceptions.Warning(
                _("Failed to query %s via POS webservice") % adapter._pos_model
            )
        
        # Initialize the binder for mapping POS IDs to Odoo IDs
        binder = self.binder_for()
        
        # Loop through each POS ID
        for pos_id in pos_ids:
            # Check if the POS ID is already mapped to an Odoo ID
            record = binder.to_internal(pos_id)
            if record:
                # Skip already mapped POS IDs
                _logger.debug(
                    "[%s] POS ID %s is already mapped to Odoo ID %s"
                    % (self.model._name, pos_id, record.id)
                )
                nr_pos_already_mapped += 1
            else:
                # Handle POS IDs that are not mapped yet
                pos_dict = adapter.read(pos_id)  # Read field values from POS
                mapping_found = False
                
                # Loop through ERP IDs to find a match
                pos_val = pos_dict[self._pos_field]
                for erp_dict in erp_list_dict:
                    erp_val = erp_dict[self._erp_field]
                    if self._compare_function(pos_val, erp_val, pos_dict, erp_dict):
                        # Match found, create a new Odoo entry and bind the POS ID
                        data = {
                            "odoo_id": erp_dict["id"],
                            "backend_id": self.backend_record.id,
                        }
                        for oe_field, pos_field in self._copy_fields:
                            data[oe_field] = pos_dict[pos_field]
                        record = self.model.create(data)
                        binder.bind(pos_id, record)
                        _logger.debug(
                            "[%s] Mapping POS '%s' (%s) to Odoo '%s' (%s)"
                            % (
                                self.model._name,
                                pos_dict["name"],  # Not hardcoded, change if needed
                                pos_dict[self._pos_field],
                                erp_dict[erp_rec_name],
                                erp_dict[self._erp_field],
                            )
                        )
                        nr_pos_mapped += 1
                        mapping_found = True
                        break
                
                if not mapping_found:
                    # No match found, print a warning
                    _logger.warning(
                        "[%s] POS '%s' (%s) was not mapped to any Odoo entry"
                        % (self.model._name, pos_dict["name"], pos_dict[self._pos_field])
                    )
                    nr_pos_not_mapped += 1
        
        # Log synchronization summary
        _logger.info(
            "[%s] Synchronization between Odoo and POS successful" % self.model._name
        )
        _logger.info(
            "[%s] Number of POS entries already mapped = %s"
            % (self.model._name, nr_pos_already_mapped)
        )
        _logger.info(
            "[%s] Number of POS entries mapped = %s"
            % (self.model._name, nr_pos_mapped)
        )
        _logger.info(
            "[%s] Number of POS entries not mapped = %s"
            % (self.model._name, nr_pos_not_mapped)
        )
        
        return True
