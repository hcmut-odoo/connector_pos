# Copyright 2011-2013 Camptocamp
# Copyright 2011-2013 Akretion
# Copyright 2015 AvanzOSC
# Copyright 2015-2016 Tecnativa
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Pos-Odoo connector",
    "version": "14.0.2.0.2",
    "license": "AGPL-3",
    "depends": [
        "account",
        "base_vat",  # for vat validation on partner address
        "product",
        "product_multi_category",  # oca/product-attribute
        "product_multi_image",  # oca/product-attribute
        "connector_ecommerce",  # oca/connector-ecommerce
        "purchase",
        "onchange_helper",
    ],
    "external_dependencies": {
        "python": [
            "freezegun",
            "vcrpy",
        ],
    },
    "author": "HOT - HCMUT Odoo Team,"
    "Vo Quy Long,"
    "Nguyen Xuan Vu,"
    "Ha Phuong Dien,",
    "website": "https://github.com/hcmut-odoo/connector-pos",
    "category": "Connector",
    "data": [
        "security/ir.model.access.csv",
        "security/pos_security.xml",
        "data/queue_job_data.xml",
        "data/cron.xml",
        "data/product_decimal_precision.xml",
        "data/ecommerce_data.xml",
        "views/pos_backend_view.xml",
        "views/product_view.xml",
        "views/product_category_view.xml",
        "views/image_view.xml",
        "views/connector_pos_menu.xml",
        "views/account_view.xml",
        "views/queue_job_views.xml",
    ],
    "installable": True,
    "application": True,
}
