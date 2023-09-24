# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, exceptions, fields, models
from odoo.addons.base.models.res_partner import _tz_get
from odoo.addons.component.core import Component

from ...components.backend_adapter import api_handle_errors

_logger = logging.getLogger(__name__)


class PosBackend(models.Model):
    """
    The `PosBackend` class represents the configuration of a Point of Sale (POS)
    backend in Odoo.

    It inherits from the `connector.backend` class and extends it to include specific
    fields and settings related to the POS functionality.

    POS backends are used to define the settings and parameters for integrating and
    synchronizing data between Odoo and the external POS system.

    Example usage:
    ```python
    class PosBackendConfig(models.Model):
        _name = "pos.backend.config"
        _description = "POS Backend Configuration"

        # Define specific fields and settings for the POS backend
        ...
    ```

    Attributes:
    - `_name`: The internal technical name of the model.
    - `_description`: A human-readable description of the model.
    - `_inherit`: The parent model to inherit from (in this case, "connector.backend").

    Fields:
    - `name`: A character field representing the name of the POS backend.
    - `location`: A character field specifying the location of the POS backend.
    - `webservice_key`: A character field used as the webservice key for the POS backend.
    - `warehouse_id`: A many-to-one field linking the backend to the associated stock
    warehouse.
    - `stock_location_id`: A many-to-one field specifying the stock location used to 
    import stock quantities.
    - `sale_team_id`: A many-to-one field representing the sales team assigned to the
    imported sales orders.
    - `taxes_included`: A boolean field indicating whether tax-included prices should be
    used.
    - `import_partners_since`: A datetime field specifying the date and time since
    which partner records should be imported.
    - `import_orders_since`: A datetime field indicating the date and time since
    which sales orders should be imported.
    - `import_payment_mode_since`: A datetime field specifying the date and time
    since which payment modes should be imported.
    - `import_products_since`: A datetime field indicating the date and time since
    which products should be imported.
    - `company_id`: A many-to-one field linking the backend to the associated company.
    - `discount_product_id`: A many-to-one field representing the discount product
    associated with the backend.
    - `shipping_product_id`: A many-to-one field specifying the shipping product
    associated with the backend.
    - `importable_order_state_ids`: A many-to-many field listing the importable
    sale order states for the backend.
    - `active`: A boolean field indicating whether the backend is active.
    - `state`: A selection field representing the state of the backend. It can
    have values like "draft", "checked", or "production".
    - `verbose`: A boolean field indicating whether to output request details in the logs.
    - `debug`: A boolean field used to activate the POS webservice debug mode.
    - `matching_product_template`: A boolean field specifying whether product
    matching should be based on product templates.
    - `matching_product_ch`: A selection field determining the matching field
    for products, such as "reference" or "barcode".
    - `matching_customer`: A boolean field indicating whether customer matching
    should be performed.
    - `tz`: A selection field representing the timezone of the backend, 
    used to synchronize sale order dates.
    - `product_qty_field`: A selection field determining how the quantity
    to push to the external POS system should be calculated.

    Note: This is a configuration model and should not be instantiated directly.
    """
    _name = "pos.backend"
    _description = "Pos Backend Configuration"
    _inherit = "connector.backend"

    @api.model
    def _select_state(self):
        """
        Get the available states for this backend.

        :return: List of state tuples
        """
        return [
            ("draft", "Draft"),
            ("checked", "Checked"),
            ("production", "In Production"),
        ]

    name = fields.Char(string="Name", required=True)
    location = fields.Char("Location")
    webservice_key = fields.Char(
        string="Webservice key",
        help="You have to put it in 'username' of the Pos "
        "Webservice api path invite",
    )
    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        string="Warehouse",
        required=True,
        help="Warehouse used to compute the stock quantities.",
    )
    stock_location_id = fields.Many2one(
        comodel_name="stock.location",
        string="Stock Location",
        help="Location used to import stock quantities.",
    )
    sale_team_id = fields.Many2one(
        comodel_name="crm.team",
        string="Sales Team",
        help="Sales Team assigned to the imported sales orders.",
    )
    taxes_included = fields.Boolean("Use tax included prices")
    import_partners_since = fields.Datetime("Import partners since")
    import_orders_since = fields.Datetime("Import Orders since")
    import_payment_mode_since = fields.Datetime("Import Payment Modes since")
    import_categories_from_date = fields.Datetime("Import categories from date")
    import_products_since = fields.Datetime("Import Products since")
    import_all_data_since = fields.Datetime("Import all data since")
    company_id = fields.Many2one(
        comodel_name="res.company",
        index=True,
        required=True,
        default=lambda self: self.env["res.company"]._company_default_get(
            "pos.backend"
        ),
        string="Company",
    )
    # discount_product_id = fields.Many2one(
    #     comodel_name="product.product",
    #     index=True,
    #     required=True,
    #     string="Discount Product",
    # )
    # shipping_product_id = fields.Many2one(
    #     comodel_name="product.product",
    #     index=True,
    #     required=True,
    #     string="Shipping Product",
    # )
    importable_order_state_ids = fields.Many2many(
        comodel_name="sale.order.state",
        string="Importable sale order states",
        help="If valued only orders matching these states will be imported.",
    )
    active = fields.Boolean(string="Active", default=True)
    state = fields.Selection(selection="_select_state", string="State", default="draft")

    verbose = fields.Boolean(help="Output requests details in the logs")
    debug = fields.Boolean(help="Activate Pos's webservice debug mode")

    matching_product_template = fields.Boolean(string="Match product template")

    matching_product_ch = fields.Selection(
        [("reference", "Reference"), ("barcode", "Barcode")],
        string="Matching Field for product",
    )

    matching_customer = fields.Boolean(
        string="Matching Customer",
        help="The selected fields will be matched to the ref field of the "
        "partner. Please adapt your datas consequently.",
    )
    tz = fields.Selection(
        _tz_get,
        "Timezone",
        help="The timezone of the backend. Used to synchronize the sale order date.",
    )
    product_qty_field = fields.Selection(
        selection=[
            ("qty_available_not_res", "Immediately usable qty"),
            ("qty_available", "Qty available"),
        ],
        string="Product qty",
        help="Select how you want to calculate the qty to push to PS. ",
        default="qty_available",
        required=True,
    )
    import_refresh_data_interval_time = fields.Integer(
        string='Interval time import refresh data', 
        help='Import refresh data each an interval time',
        default=5
    )
    status_import_routine_scheduler = fields.Boolean(
        string="Active import routine scheduler",
        default=True
    )
    import_routine_data_since = fields.Datetime("Import routine data since")
    created_import_routine_data = fields.Boolean(
        string="Created import routine scheduler",
        default=False
    )

    import_routine_data_interval_time = fields.Integer(
        string='Interval time import routine data', 
        help='Import routine data each an interval time',
        default=1
    )
    status_import_refresh_scheduler = fields.Boolean(
        string="Active import refresh scheduler",
        default=True
    )
    created_import_refresh_data = fields.Boolean(
        string="Created import refresh scheduler",
        default=False
    )
    import_refresh_data_since = fields.Datetime("Import refresh data since")
    
    @api.constrains('import_routine_data_interval_time')
    def _check_routine_data_interval_time(self):
        if self.import_routine_data_interval_time == 0:
            raise exceptions.UserError(_('Import routine data interval time must be larger than 0.'))

    @api.constrains('import_refresh_data_interval_time')
    def _check_refresh_data_interval_time(self):
        if self.import_refresh_data_interval_time == 0:
            raise exceptions.UserError(_('Import refresh data interval time must be larger than 0.'))

    @api.constrains("product_qty_field")
    def check_product_qty_field_dependencies_installed(self):
        """
        Check the dependencies for the `product_qty_field` field.

        This constraint method verifies if the required module "stock_available_unreserved" 
        is installed when the `product_qty_field` is set to "qty_available_not_res". 
        If the module is not installed, it raises a `UserError` with an appropriate 
        error message.

        :raises UserError: If the "stock_available_unreserved" module is not installed.
        """
        for backend in self:
            # Check if the product_qty_field is set to "qty_available_not_res"
            # we only support stock_available_unreserved module for now.
            # In order to support stock_available_immediately or
            # virtual_available for example, we would need to recompute
            # the pos qty at stock move level, it can't work to
            # recompute it only at quant level, like it is done today
            if backend.product_qty_field == "qty_available_not_res":
                # Search for the "stock_available_unreserved" module
                module = (
                    self.env["ir.module.module"]
                    .sudo()
                    .search([("name", "=", "stock_available_unreserved")], limit=1)
                )
                # Check if the module exists and is installed
                if not module or module.state != "installed":
                    # Raise a UserError with the appropriate error message
                    raise exceptions.UserError(
                        _(
                            "In order to choose this option, you have to "
                            "install the module stock_available_unreserved."
                        )
                    )

    @api.onchange("matching_customer")
    def change_matching_customer(self):
        """
        Update the field list related to matching customers.

        This onchange method is triggered when the value of the `matching_customer` 
        field changes. It updates the field list to ensure that if there are any 
        changes in the API, the new fields can be mapped correctly.

        Note: This method internally calls the `fill_matched_fields` method.

        :return: None
        """
        if self._origin.id:
            # Call the `fill_matched_fields` method to update the field list
            self.fill_matched_fields(self._origin.id)

    def fill_matched_fields(self, backend_id):
        self.ensure_one()

    def button_reset_to_draft(self):
        """
        Reset the state of the record to "draft".

        This method sets the `state` field of the current record to "draft". 
        It is typically used as a button action to reset the state of the record 
        to the initial draft state.

        :return: None
        """
        self.ensure_one()
        self.write({"state": "draft"})

    def synchronize_basedata(self):
        """
        Synchronize base data for the specified models with the specified backends.

        This method iterates over the backends and imports the base data for the 
        following models:
        - pos.res.country
        - pos.res.currency
        - pos.account.tax
        The import is performed using the appropriate import components based 
        on the backend's work context.

        Additionally, it imports the base data for the `pos.account.tax.group` 
        and `pos.sale.order.state` models using the `import_batch` method.

        :return: True if the base data synchronization is successful.
        :rtype: bool
        """
        return True

    def _check_connection(self):
        """
        Test the connection to the POS backend.

        This method tests the connection to the POS backend by retrieving 
        the `pos.adapter.test` component and performing a `head` request 
        to check the connection status. It ensures that there is only one 
        record in the current context.

        :raises: An exception with the message "Connection failed" if the 
        connection test fails.
        :return: None
        """
        self.ensure_one()
        with self.work_on("pos.backend") as work:
            component = work.component_by_name(name="pos.adapter.test")
            with api_handle_errors("Connection failed"):
                component.connect()

    def button_check_connection(self):
        """
        Perform a connection check to the POS backend.

        This method calls the `_check_connection` method to test the 
        connection to the POS backend. If the connection test is successful, 
        it updates the state of the backend to "checked".

        :return: None
        """
        self._check_connection()
        self.write({"state": "checked"})

    def import_customers_since(self):
        """
        Initiate the import of customers from the POS backend.

        This method initiates the import of customers from the POS backend. 
        It retrieves the value of the `import_partners_since` field from the 
        backend record and passes it to the `import_customers_since` method 
        of the `pos.res.partner` model with a delay.

        :return: True if the import process is initiated successfully.
        :rtype: bool
        """
        for backend_record in self:
            since_date = backend_record.import_partners_since
            self.env["pos.res.partner"].with_delay().import_customers_since(
                backend_record=backend_record, since_date=since_date
            )
        return True
    
    def import_product_categories(self):
        """
        Initiate the import of product categories from the POS backend.

        This method initiates the import of product categories from the POS backend. 
        It retrieves the value of the `import_categories_from_date` field from the 
        backend record and passes it to the `import_product_categories` method of the 
        `pos.product.template` model with a delay.

        :return: True if the import process is initiated successfully.
        :rtype: bool
        """
        for backend_record in self:
            since_date = backend_record.import_categories_from_date
            self.env["pos.product.category"].with_delay().import_product_categories(
                backend_record, since_date
            )
        return True

    def import_products(self):
        """
        Initiate the import of products from the POS backend.

        This method initiates the import of products from the POS backend. 
        It retrieves the value of the `import_products_since` field from the 
        backend record and passes it to the `import_products` method of the 
        `pos.product.template` model with a delay.

        :return: True if the import process is initiated successfully.
        :rtype: bool
        """
        for backend_record in self:
            since_date = backend_record.import_products_since
            self.env["pos.product.template"].with_delay().import_products(
                backend_record, since_date
            )
        return True

    def import_carriers(self):
        """
        Initiate the import of carriers from the POS backend.

        This method initiates the import of carriers from the POS backend.
        It calls the `import_batch` method of the `pos.delivery.carrier`
        model with a delay to perform the import.

        :return: True if the import process is initiated successfully.
        :rtype: bool
        """
        for backend_record in self:
            self.env["pos.delivery.carrier"].with_delay().import_batch(
                backend_record,
            )
        return True

    def update_product_stock_qty(self):
        """
        Update the stock quantities of products in the POS backend.

        This method updates the stock quantities of products in the POS backend.
        It calls the `export_product_quantities` method of the `pos.product.template`
        and `pos.product.variant` models with a delay to perform the 
        export and update the stock quantities.

        :return: True if the update process is initiated successfully.
        :rtype: bool
        """
        for backend_record in self:
            backend_record.env["pos.product.template"].with_delay().export_product_quantities(
                backend=backend_record
            )
            backend_record.env["pos.product.variant"].with_delay().export_product_quantities(
                backend=backend_record
            )
        return True

    def import_stock_qty(self):
        """
        Import stock quantities from the POS backend.

        This method imports the stock quantities from the POS backend. 
        It calls the `import_inventory` method of the `pos.product.template` 
        model with a delay to perform the import.

        :return: True if the import process is initiated successfully.
        :rtype: bool
        """
        for backend_record in self:
            backend_record.env["pos.product.template"].with_delay().import_inventory(
                backend_record
            )
        return True

    def import_sale_orders(self):
        """
        Import sale orders from the POS backend.

        This method imports sale orders from the POS backend. 
        It calls the `import_orders_since` method of the `pos.sale.order` 
        model with a delay to perform the import. The import is performed 
        for the specified since date.

        :return: True if the import process is initiated successfully.
        :rtype: bool
        """
        for backend_record in self:
            since_date = backend_record.import_orders_since
            backend_record.env["pos.sale.order"].with_delay().import_orders_since(
                backend_record, since_date
            )
        return True

    def import_payment_modes(self):
        """
        Import payment modes from the POS backend.

        This method imports payment modes from the POS backend.
        It retrieves the current datetime and determines the since date
        for the import based on the `import_payment_mode_since` field.
        It sets up filters to retrieve the updated payment modes based
        on the since date. The import is performed using the `batch.importer`
        component of the `account.payment.mode` model, and the
        `import_payment_mode_since` field is updated to the current datetime.

        :return: True if the import process is completed successfully.
        :rtype: bool
        """
        now_fmt = fields.Datetime.now()
        for backend_record in self:
            since_date = backend_record.import_payment_mode_since
            filters = {}
            if since_date:
                filters = {"date": "1", "filter[date_upd]": ">[%s]" % (since_date)}
            with backend_record.work_on("account.payment.mode") as work:
                importer = work.component(usage="batch.importer")
                importer.run(filters=filters)
            backend_record.import_payment_mode_since = now_fmt
        return True
    
    def import_refresh(self):
        now_fmt = fields.Datetime.now()
        for backend_record in self:
            import_category_since_date = backend_record.import_categories_from_date
            import_partner_since_date = backend_record.import_partners_since
            import_order_since_date = backend_record.import_orders_since
            import_product_since_date = backend_record.import_products_since
            
            self.env["pos.product.category"].import_product_categories(
                backend_record, import_category_since_date
            )

            self.env["pos.res.partner"].import_customers_since(
                backend_record=backend_record, since_date=import_partner_since_date
            )

            self.env["pos.product.template"].import_products(
                backend_record, import_product_since_date
            )

            backend_record.env["pos.sale.order"].import_orders_since(
                backend_record, import_order_since_date
            )

            backend_record.import_refresh_data_since = now_fmt
        
        return True
    
    def create_import_refresh_data(self):
        for backend_record in self:
            import_refresh_data_interval_time = backend_record.import_refresh_data_interval_time
            backend_record.created_import_refresh_data = True

            cron_record = self.env['ir.cron'].search([('name', '=', 'Pos - Import Refresh')])
            if cron_record:
                return True
            
            self.env['ir.cron'].create({
                    'name': 'Pos - Import Refresh',
                    'active': True,
                    'user_id': self.env.ref('base.user_root').id,
                    'interval_number': import_refresh_data_interval_time,
                    'state': 'code',
                    'code': 'model._scheduler_import_refresh()',
                    'interval_type': 'minutes',
                    'numbercall': -1,
                    'doall': False,
                    'model_id': self.env.ref('connector_pos.model_pos_backend').id,
                })
        
        return True

    def create_import_routine_data(self):
        for backend_record in self:
            import_routine_data_interval_time = backend_record.import_routine_data_interval_time
            backend_record.created_import_routine_data = True

            cron_record = self.env['ir.cron'].search([('name', '=', 'Pos - Import Routine')])
            if cron_record:
                return True

            self.env['ir.cron'].create({
                    'name': 'Pos - Import Routine',
                    'active': True,
                    'user_id': self.env.ref('base.user_root').id,
                    'interval_number': import_routine_data_interval_time,
                    'state': 'code',
                    'code': 'model._scheduler_import_routine()',
                    'interval_type': 'days',
                    'numbercall': -1,
                    'doall': False,
                    'model_id': self.env.ref('connector_pos.model_pos_backend').id,
                })

        return True

    def unactive_import_routine_scheduler(self):
        for backend_record in self:
            cron_record = self.env['ir.cron'].search([('cron_name', '=', 'Pos - Import Routine'), ('active', '=', True)])
            print("unactive_import_routine_scheduler", cron_record)
            backend_record.status_import_routine_scheduler = False
            if cron_record:
                cron_record.active = False
                self.env.cr.commit()

    def unactive_import_refresh_scheduler(self):
        for backend_record in self:
            backend_record.status_import_refresh_scheduler = False
            cron_record = self.env['ir.cron'].search([('cron_name', '=', 'Pos - Import Refresh'), ('active', '=', True)])
            print("unactive_import_refresh_scheduler", cron_record)
            if cron_record:
                cron_record.active = False 
                self.env.cr.commit()

    def active_import_refresh_scheduler(self):
        for backend_record in self:
            backend_record.status_import_refresh_scheduler = True
            cron_record = self.env['ir.cron'].search([('cron_name', '=', 'Pos - Import Refresh'), ('active', '=', False)])
            if cron_record:
                cron_record.active = True
                self.env.cr.commit()

    def active_import_routine_scheduler(self):
        for backend_record in self:            
            cron_record = self.env['ir.cron'].search([('cron_name', '=', 'Pos - Import Routine'), ('active', '=', False)])
            print("active_import_routine_scheduler", cron_record)
            backend_record.status_import_routine_scheduler = True
            if cron_record:
                cron_record.active = True  
                self.env.cr.commit()

    def import_all(self):
        now_fmt = fields.Datetime.now()
        for backend_record in self:
            import_category_since_date = backend_record.import_categories_from_date
            import_partner_since_date = backend_record.import_partners_since
            import_order_since_date = backend_record.import_orders_since
            import_product_since_date = backend_record.import_products_since

            
            self.env["pos.product.category"].import_product_categories(
                backend_record, import_category_since_date
            )

            self.env["pos.res.partner"].import_customers_since(
                backend_record=backend_record, since_date=import_partner_since_date
            )

            self.env["pos.product.template"].import_products(
                backend_record, import_product_since_date
            )

            backend_record.env["pos.product.template"].import_inventory(
                backend_record
            )

            backend_record.env["pos.sale.order"].import_orders_since(
                backend_record, import_order_since_date
            )

            backend_record.import_all_data_since = now_fmt
            backend_record.import_routine_data_since = now_fmt

        return True

    @api.model
    def _scheduler_update_product_stock_qty(self, domain=None):
        """
        Scheduled job method to update the stock quantities of products.

        This method is a scheduled job that updates the stock quantities of products.
        It can be called on the model itself rather than on specific records.
        The optional `domain` parameter can be used to filter the records
        on which the stock quantities should be updated. If no `domain` is provided,
        all records of the model will be considered.

        :param domain: Optional domain to filter the records.
        :type domain: list or tuple or None
        """
        self.search(domain or []).update_product_stock_qty()

    @api.model
    def _scheduler_import_refresh(self, domain=None):
        self.search(domain or []).import_refresh()
    
    @api.model
    def _scheduler_import_routine(self, domain=None):
        self.search(domain or []).import_all()

    @api.model
    def _scheduler_import_sale_orders(self, domain=None):
        """
        Scheduled job method to import sale orders.

        This method is a scheduled job that imports sale orders. 
        It can be called on the model itself rather than on specific records.
        The optional `domain` parameter can be used to filter the records on 
        which the sale orders should be imported. If no `domain` is provided, 
        all records of the model will be considered.

        :param domain: Optional domain to filter the records.
        :type domain: list or tuple or None
        """
        self.search(domain or []).import_sale_orders()

    @api.model
    def _scheduler_import_customers(self, domain=None):
        """
        Scheduled job method to import customers.

        This method is a scheduled job that imports customers. 
        It can be called on the model itself rather than on specific records.
        The optional `domain` parameter can be used to filter the records on 
        which the customers should be imported. If no `domain` is provided, 
        all records of the model will be considered.

        :param domain: Optional domain to filter the records.
        :type domain: list or tuple or None
        """
        self.search(domain or []).import_customers_since()

    @api.model
    def _scheduler_import_products(self, domain=None):
        """
        Scheduled job method to import products.

        This method is a scheduled job that imports products. 
        It can be called on the model itself rather than on specific records.
        The optional `domain` parameter can be used to filter the records on 
        which the products should be imported. If no `domain` is provided, 
        all records of the model will be considered.

        :param domain: Optional domain to filter the records.
        :type domain: list or tuple or None
        """
        self.search(domain or []).import_products()

    @api.model
    def _scheduler_import_carriers(self, domain=None):
        """
        Scheduled job method to import carriers.

        This method is a scheduled job that imports carriers. 
        It can be called on the model itself rather than on specific records.
        The optional `domain` parameter can be used to filter the records on 
        which the carriers should be imported. If no `domain` is provided, 
        all records of the model will be considered.

        :param domain: Optional domain to filter the records.
        :type domain: list or tuple or None
        """
        self.search(domain or []).import_carriers()

    @api.model
    def _scheduler_import_payment_methods(self, domain=None):
        """
        Scheduled job method to import payment methods.

        This method is a scheduled job that imports payment methods. 
        It can be called on the model itself rather than on specific records. 
        The optional `domain` parameter can be used to filter the records on 
        which the payment methods should be imported. If no `domain` is provided,
        all records of the model will be considered.

        :param domain: Optional domain to filter the records.
        :type domain: list or tuple or None
        """
        backends = self.search(domain or [])
        backends.import_payment_modes()

    def _get_locations_for_stock_quantities(self):
        """
        Retrieve the locations to consider when computing product quantities for the backend.

        This method searches for locations that should be considered when computing the product quantity for the backend. It takes into account the root location based on the 'stock_location_id' or the 'lot_stock_id' of the associated warehouse. The locations must meet the following criteria:
        - They are descendants (including the root location itself) of the root location.
        - They are marked as synchronized with the point of sale (pos_synchronized = True).
        - They have the usage set to 'internal'.

        If no locations are found with these criteria, a fallback search is performed without considering the 'pos_synchronized' flag but still considering the other criteria.

        If no locations are found even after the fallback search, a UserError is raised indicating that no internal location was found to compute the product quantity.

        :return: Locations to consider when computing product quantities.
        :rtype: recordset of stock.location
        :raise: UserError if no internal location is found.
        """
        root_location = self.stock_location_id or self.warehouse_id.lot_stock_id
        locations = self.env["stock.location"].search(
            [
                ("id", "child_of", root_location.id),
                ("pos_synchronized", "=", True),
                ("usage", "=", "internal"),
            ]
        )
        # if we choosed a location but none where flagged
        # 'pos_synchronized', consider we want all of them in the tree
        if not locations:
            locations = self.env["stock.location"].search(
                [
                    ("id", "child_of", root_location.id),
                    ("usage", "=", "internal"),
                ]
            )
        if not locations:
            # we must not pass an empty location or we would have the
            # stock for every warehouse, which is the last thing we
            # expect
            raise exceptions.UserError(
                _("No internal location found to compute the product quantity.")
            )
        return locations


class NoModelAdapter(Component):
    """
    Adapter component used to test the connection with the backend.

    This adapter is used for testing purposes and does not work with 
    a specific POS model. It inherits from the 'pos.adapter' class and 
    is applied to the 'pos.backend' model.

    :param pos.adapter: The base adapter component.
    :type pos.adapter: class
    :param pos.backend: The model representing the POS backend configuration.
    :type pos.backend: str
    """
    _name = "pos.adapter.test"
    _inherit = "pos.adapter"
    _apply_on = "pos.backend"
    _pos_model = "check-connection"
