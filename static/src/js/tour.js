odoo.define('connector_pos.tour', function(require) {
    "use strict";
    
    var core = require('web.core');
    var tour = require('web_tour.tour');
    
    var _t = core._t;
    
    tour.register("connector_tour", {
        url: "/web",
        rainbowMan: false,
        sequence: 19,
    }, [tour.stepUtils.showAppsMenuItem(), {
        trigger: ".o_app[data-menu-xmlid='connector.menu_connector_root']",
        content: _t("Mở ứng dụng Connector để bắt đầu tạo connector."),
        position: "right",
        edition: "community"
    },
]);
});