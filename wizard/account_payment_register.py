from odoo import Command, _, models, fields, api
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = ['account.payment.register']

    def _init_payments(self, to_process, edit_mode=False):
        for vals in to_process:
            invoice_lines = vals.get('to_reconcile', [])
            payment_amount = vals['create_vals'].get('amount', 0.0)
            payment_invoice_values = []
            if len(invoice_lines) == 1:
                # Si solo hay una factura, asignar el total del pago
                line = invoice_lines[0]
                payment_invoice_values.append((0, 0, {
                    'invoice_id': line.move_id.id,
                    'reconcile_amount': payment_amount,
                }))
            else:
                remaining_amount = payment_amount
                for line in invoice_lines:
                    invoice = line.move_id
                    reconcile_amount = min(remaining_amount, abs(line.amount_residual))
                    payment_invoice_values.append((0, 0, {
                        'invoice_id': invoice.id,
                        'reconcile_amount': reconcile_amount,
                    }))
                    remaining_amount -= reconcile_amount
                    if remaining_amount <= 0:
                        break
            vals['create_vals']['payment_invoice_ids'] = payment_invoice_values
        payments = super()._init_payments(to_process, edit_mode=edit_mode)
        return payments


    # def action_create_payments(self):
    #     res = super().action_create_payments()
    #     print('AccountPaymentRegister  action_create_payments : ',res)
    #     return res
