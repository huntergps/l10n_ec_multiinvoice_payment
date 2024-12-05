# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models , Command
from odoo.exceptions import UserError
from datetime import date, timedelta



class AccountPayment(models.Model):
    _inherit = 'account.payment'

    type_mov = fields.Selection([
        ('current', 'Pago Ordinario'),
    ], string='Tipo de Transacción', default='current', store=True)

    payment_invoice_ids = fields.One2many('account.payment.invoice', 'payment_id', string="Facturas")
    invoice_type = fields.Char(string='Tipo Documento', compute='_compute_invoice_type', store=True, copy=False)
    amount = fields.Monetary(compute="_compute_amount", readonly=False, store=True)

    @api.constrains('payment_method_line_id')
    def _check_payment_method_line_id(self):
        for pay in self:
            if pay.type_mov in ('current'):
                if not pay.payment_method_line_id:
                    raise ValidationError(_("Please define a payment method line on your payment."))
                elif pay.payment_method_line_id.journal_id and pay.payment_method_line_id.journal_id != pay.journal_id:
                    raise ValidationError(_("The selected payment method is not available for this payment, please select the payment method again."))

    @api.depends('payment_invoice_ids.reconcile_amount', 'payment_method_code')
    def _compute_amount(self):
        for rec in self:
            rec.amount = sum(rec.payment_invoice_ids.mapped('reconcile_amount'))

    @api.model_create_multi
    def create(self, vals_list):
        # Crear pagos
        payments = super().create(vals_list)
        # print("create payments",vals_list)
        # print(payments.invoice_ids)
        return payments

    def write(self, vals):
        res = super().write(vals)
        # print("write payments",vals)
        self._synchronize_to_moves(set(vals.keys()))
        return res

    @api.depends('payment_type', 'partner_id')
    def _compute_invoice_type(self):
        for payment in self:
            if not payment.partner_id:
                if payment.payment_type == 'inbound':
                    payment.invoice_type = 'out_invoice'
                elif payment.payment_type == 'outbound':
                    payment.invoice_type = 'in_invoice'
            else:
                if payment.payment_type == 'inbound' and payment.partner_type == 'customer':
                    payment.invoice_type = 'out_invoice'
                elif payment.payment_type == 'outbound' and payment.partner_type == 'customer':
                    payment.invoice_type = 'out_refund'
                elif payment.payment_type == 'outbound' and payment.partner_type == 'supplier':
                    payment.invoice_type = 'in_invoice'
                else:
                    payment.invoice_type = 'in_refund'


    @api.onchange('payment_type', 'partner_type', 'partner_id', 'currency_id')
    def _onchange_to_get_vendor_invoices(self):
        if self.payment_type in ['inbound', 'outbound'] and self.partner_type and self.partner_id and self.currency_id:
            existing_partner_id = self.payment_invoice_ids.mapped('invoice_id.partner_id.id')
            if existing_partner_id and existing_partner_id[0] != self.partner_id.id:
                self.payment_invoice_ids = [(6, 0, [])]

            if (len(self.payment_invoice_ids)<1):
                self.payment_invoice_ids = [(6, 0, [])]
                invoice_recs = self.env['account.move'].search([
                    ('partner_id', 'child_of', self.partner_id.id),
                    ('state', '=', 'posted'),
                    ('move_type', '=', self.invoice_type),
                    ('payment_state', '!=', 'paid'),
                    ('currency_id', '=', self.currency_id.id)])
                payment_invoice_values = []
                for invoice_rec in invoice_recs:
                    payment_invoice_values.append([0, 0, {'invoice_id': invoice_rec.id,'reconcile_amount':invoice_rec.amount_residual}])
                self.payment_invoice_ids = payment_invoice_values


    def action_post(self):
        super(AccountPayment, self).action_post()
        for payment in self:
            if payment.payment_invoice_ids:
                if payment.amount < sum(payment.payment_invoice_ids.mapped('reconcile_amount')):
                    raise UserError(
                        _("La suma del importe total a pagar de las facturas listadas ({reconcile_amount_sum}) es mayor que el importe del pago ({payment_amount}).").format(
                            reconcile_amount_sum=sum(payment.payment_invoice_ids.mapped('reconcile_amount')),
                            payment_amount=payment.amount
                        )
                    )


            for line_id in payment.payment_invoice_ids:
                if not line_id.reconcile_amount:
                    continue
                if line_id.amount_total <= line_id.reconcile_amount:
                    self.ensure_one()
                    if payment.payment_type == 'inbound':
                        lines = payment.move_id.line_ids.filtered(lambda line: line.credit > 0)
                        if lines:
                            lines += line_id.invoice_id.line_ids.filtered(
                                lambda line: line.account_id == lines[0].account_id and not line.reconciled)
                            lines.reconcile()
                    elif payment.payment_type == 'outbound':
                        lines = payment.move_id.line_ids.filtered(lambda line: line.debit > 0)
                        if lines:
                            lines += line_id.invoice_id.line_ids.filtered(
                                lambda line: line.account_id == lines[0].account_id and not line.reconciled)
                            lines.reconcile()
                else:
                    self.ensure_one()
                    if payment.payment_type == 'inbound':
                        lines = payment.move_id.line_ids.filtered(lambda line: line.credit > 0)
                        if lines:
                            lines += line_id.invoice_id.line_ids.filtered(
                                lambda line: line.account_id == lines[0].account_id and not line.reconciled)
                            lines.with_context(amount=-line_id.reconcile_amount).reconcile()
                    elif payment.payment_type == 'outbound':
                        lines = payment.move_id.line_ids.filtered(lambda line: line.debit > 0)
                        if lines:
                            lines += line_id.invoice_id.line_ids.filtered(
                                lambda line: line.account_id == lines[0].account_id and not line.reconciled)
                            lines.with_context(amount=line_id.reconcile_amount).reconcile()
                payment._compute_stat_buttons_from_reconciliation()
        return True


class AccountPaymentInvoices(models.Model):
    _name = 'account.payment.invoice'

    invoice_id = fields.Many2one('account.move', string='Factura')
    payment_id = fields.Many2one('account.payment', string='Pago')
    currency_id = fields.Many2one(related='invoice_id.currency_id')
    origin = fields.Char(related='invoice_id.invoice_origin')
    date_invoice = fields.Date(related='invoice_id.invoice_date')
    date_due = fields.Date(related='invoice_id.invoice_date_due')
    payment_state = fields.Selection(related='payment_id.state', store=True)
    reconcile_amount = fields.Monetary(string='Reconcile Amount')
    amount_total = fields.Monetary(related="invoice_id.amount_total")
    residual = fields.Monetary(related="invoice_id.amount_residual")
