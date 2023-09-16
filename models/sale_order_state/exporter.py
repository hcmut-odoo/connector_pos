# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo.addons.component.core import Component


class SaleStateExporter(Component):
    _name = "pos.sale.order.state.exporter"
    _inherit = "pos.exporter"
    _apply_on = ["pos.sale.order"]
    _usage = "sale.order.state.exporter"

    def run(self, binding, state, **kwargs):
        # datas = {
        #     "order_history": {
        #         "id_order": binding.pos_id,
        #         "id_order_state": state,
        #     }
        # }
        print("sale.order.state.exporter")
        
        datas = {
            'action': state,
            'id': binding.pos_id
        }

        print(datas)

        self.backend_adapter.update_sale_state(datas)
