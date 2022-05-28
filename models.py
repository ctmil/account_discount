from odoo import tools, models, fields, api, _
from odoo.exceptions import ValidationError
import openpyxl
import base64
from datetime import date,datetime

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    discount_journal_id = fields.Many2one('account.journal',string='Journal discounts')
    discount_account_id = fields.Many2one('account.account',string='Account discounts')

class AccountMove(models.Model):
    _inherit = 'account.move'

    discount_move_id = fields.Many2one('account.move',string='Discount move',copy=False)

    def action_post(self):
        res = super(AccountMove, self).action_post()
        for rec in self:
            if rec.move_type in ['in_invoice','out_invoice','in_refund','out_refund']:
                discount_lines = rec.invoice_line_ids.filtered(lambda l: l.discount)
                if discount_lines and rec.journal_id.discount_account_id:
                    vals_move = {
                            'ref': 'Discount for %s'%(rec.name),
                            'date': rec.date,
                            'journal_id': rec.journal_id.discount_journal_id \
                                    and rec.journal_id.discount_journal_id.id \
                                    or rec.journal_id.id,
                            'invoice_origin': rec.name,
                            'move_type': 'entry',
                            }
                    move_id = self.env['account.move'].create(vals_move)
                    rec.discount_move_id = move_id.id
                    if rec.move_type in ['out_invoice','in_refund']:
                        discount_amount = 0
                        for discount_line in discount_lines:
                            discount_amount = discount_line.price_unit * discount_line.quantity \
                                    * discount_line.discount / 100
                        if discount_amount:
                            vals_debit = {
                                    'move_id': move_id.id,
                                    'account_id': discount_line.account_id.id,
                                    'journal_id': move_id.journal_id.id,
                                    'partner_id': rec.partner_id.id,
                                    'name': 'Debit discount %s'%(rec.name),
                                    'debit': discount_amount,
                                    'credit': 0,
                                    }
                            debit_id = self.env['account.move.line'].with_context({'check_move_validity': False}).create(vals_debit)
                            vals_credit = {
                                    'move_id': move_id.id,
                                    'account_id': rec.journal_id.discount_account_id.id,
                                    'journal_id': move_id.journal_id.id,
                                    'partner_id': rec.partner_id.id,
                                    'name': 'Credit discount %s'%(rec.name),
                                    'debit': 0,
                                    'credit': discount_amount,
                                    }
                            credit_id = self.env['account.move.line'].with_context({'check_move_validity': False}).create(vals_credit)
                    else:
                        discount_amount = 0
                        for discount_line in discount_lines:
                            discount_amount = discount_line.price_unit * discount_line.quantity \
                                    * discount_line.discount / 100
                        if discount_amount:
                            vals_credit = {
                                    'move_id': move_id.id,
                                    'account_id': discount_line.account_id.id,
                                    'journal_id': move_id.journal_id.id,
                                    'partner_id': rec.partner_id.id,
                                    'name': 'Credit discount %s'%(rec.name),
                                    'credit': discount_amount,
                                    'debit': 0,
                                    }
                            debit_id = self.env['account.move.line'].with_context({'check_move_validity': False}).create(vals_credit)
                            vals_debit = {
                                    'move_id': move_id.id,
                                    'account_id': rec.journal_id.discount_account_id.id,
                                    'journal_id': move_id.journal_id.id,
                                    'partner_id': rec.partner_id.id,
                                    'name': 'Debit discount %s'%(rec.name),
                                    'credit': 0,
                                    'debit': discount_amount,
                                    }
                            credit_id = self.env['account.move.line'].with_context({'check_move_validity': False}).create(vals_debit)
                    move_id.action_post()
                    rec.message_post(body=_(('Discount move %s created and validated')%(move_id.name)))

        return res
