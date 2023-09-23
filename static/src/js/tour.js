odoo.define('connector_pos.tour', function(require) {
    "use strict";
    
    var core = require('web.core');
    var tour = require('web_tour.tour');
    
    var _t = core._t;
    
    tour.register("connector_tour", {
        url: "/web",
        rainbowMan: false,
        sequence: 10,
    }, [tour.stepUtils.showAppsMenuItem(), {
        trigger: ".o_app[data-menu-xmlid='connector.menu_connector_root']",
        content: _t("Mở ứng dụng Connector để bắt đầu tạo connector."),
        position: "right",
        edition: "community"
    },{
        trigger: ".o_list_button_add",
        content: _t("Nhấn để tạo connector mới."),
        position: "right",
    },{
        trigger: ".o_form_editable .o_input[name='name']",
        content: _t("Nhập tên connector."),
        position: "right",
        run: function (actions) {
            actions.text("Agrolait", this.$anchor.find("input"));
        },
    },{
        trigger: ".o_form_editable .o_field_many2one[name='company_id']",
        content: _t("Nhập tên công ty hoặc chọn công ty có sẵn."),
        position: "bottom",
        run: function (actions) {
            actions.text("Agrolait", this.$anchor.find("input"));
        },
    },{
        trigger: ".o_form_editable .o_input[name='location']",
        content: _t("Nhập địa chỉ URL."),
        position: "right",
        run: function (actions) {
            actions.text("Agrolait", this.$anchor.find("input"));
        },
    },{
        trigger: ".o_form_editable .o_input[name='webservice_key']",
        content: _t("Nhập webservice key."),
        position: "right",
        run: function (actions) {
            actions.text("Agrolait", this.$anchor.find("input"));
        },
    },{
        trigger: ".o_form_editable .o_field_many2one[name='warehouse_id']",
        content: _t("Nhập tên nhà kho hoặc chọn nhà kho có sẵn."),
        position: "right",
        run: function (actions) {
            actions.text("Agrolait", this.$anchor.find("input"));
        },
    },
    ...tour.stepUtils.statusbarButtonsSteps(
        "Check Connection",
        _t("<b>Check connection</b> để hoàn tất tạo connector."),
        ".o_statusbar_buttons button[name='button_check_connection']"
    ),
]);

    tour.register("sale_connector_tour", {
        url: "/web",
        rainbowMan: false,
        sequence: 11,
    }, [tour.stepUtils.showAppsMenuItem(), {
        trigger: ".o_app[data-menu-xmlid='sale.sale_menu_root']",
        content: _t("Mở ứng dụng Sales để bắt đầu xử lý đơn hàng."),
        position: "right",
        edition: "community"
    },{
        trigger: ".o_menu_sections a:contains('To Invoice')",
        extra_trigger: '.o_main_navbar',
        content: _t("Mở đơn hàng"),
        position: "bottom",
    },{
        trigger: ".o_menu_sections a:has(span:contains('Orders to Invoice'))",
        content: _t("Xem đơn hàng đang chờ."),
        position: "right"
    },{
        mobile: false,
        trigger: '.o_data_row:first',
        content: _t('Chọn một đơn hàng'),
        position: 'bottom',
    },
    ...tour.stepUtils.statusbarButtonsSteps(
        "Create Invoice",
        _t("Tạo hoá đơn."),
        ".o_statusbar_buttons"
    ),
    ...tour.stepUtils.statusbarButtonsSteps(
        "Create Invoice",
        _t("Tạo hoá đơn."),
        ".o_web_client .o_legacy_dialog button[id='create_invoice']"
    ),
]);

});