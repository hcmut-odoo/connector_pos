import logging

from odoo.addons.component.core import AbstractComponent

_logger = logging.getLogger(__name__)


class PosListener(AbstractComponent):
    """
    Base Backend Adapter for the Pos connectors.

    This component serves as the base backend adapter for the connectors related 
    to Pos. It inherits from `base.connector.listener` and provides the 
    necessary methods for checking if a record needs to be exported to Pos.

    :ivar _name: Name of the component.
    :vartype _name: str
    :ivar _inherit: Inherited component.
    :vartype _inherit: str
    """

    _name = "pos.connector.listener"
    _inherit = "base.connector.listener"

    def need_to_export(self, record, fields=None):
        """
        Check if the record needs to be exported to Pos.

        This method determines whether the given record needs to be exported to 
        Pos based on the written fields and the "no_export" flag of the record.

        To be used with :func:`odoo.addons.component_event.skip_if`
        on Events::

            from odoo.addons.component.core import Component
            from odoo.addons.component_event import skip_if


            class MyEventListener(Component):
                _name = 'my.event.listener'
                _inherit = 'base.connector.event.listener'
                _apply_on = ['magento.res.partner']

                @skip_if(lambda: self, record, *args, **kwargs:
                         self.need_to_export(record, fields=fields))
                def on_record_write(self, record, fields=None):
                    record.with_delay().export_record()
                    
        :param record: Record to be checked for export.
        :type record: odoo.models.Model
        :param fields: Optional list of specific fields to consider.
        :type fields: list[str] or None
        :return: True if the record should be skipped for export, False otherwise.
        :rtype: bool
        """
        if not record or not record.backend_id:
            return True
        with record.backend_id.work_on(record._name) as work:
            mapper = work.component(usage="export.mapper")
            exported_fields = mapper.changed_by_fields()
            if fields:
                if not exported_fields & set(fields):
                    _logger.debug(
                        "Skip export of %s because modified fields: %s are not part of exported fields %s",
                        record,
                        fields,
                        list(exported_fields),
                    )
                    return True
        if record.no_export:
            _logger.debug("Skip export of %s because export is disabled for it", record)
            return True
        return False

