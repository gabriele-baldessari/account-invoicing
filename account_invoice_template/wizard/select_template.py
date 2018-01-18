# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2011 Agile Business Group sagl (<http://www.agilebg.com>)
#    Copyright (C) 2011 Domsense srl (<http://www.domsense.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class WizardSelectTemplate(models.TransientModel):

    _name = "wizard.select.invoice.template"

    template_id = fields.Many2one(
        'account.invoice.template',
        'Invoice Template', required=True)
    line_ids = fields.One2many(
        'wizard.select.invoice.template.line',
        'template_id', 'Lines')
    state = fields.Selection([
        ('template_selected', 'Template selected')],
        'State')

    def load_lines(self):
        wizard = self
        template_obj = self.env['account.invoice.template']
        wizard_line_obj = self.env['wizard.select.invoice.template.line']

        template = template_obj.browse(wizard.template_id.id)
        for line in template.template_line_ids:
            if line.type == 'input':
                wizard_line_obj.create({
                    'template_id': wizard.id,
                    'sequence': line.sequence,
                    'name': line.name,
                    'amount': (
                        line.product_id and line.product_id.list_price or 0.0),
                    'account_id': line.account_id.id,
                    'product_id': line.product_id.id,
                })
        if not wizard.line_ids:
            return self.load_template()
        wizard.write({'state': 'template_selected'})

        view_rec = self.env.ref(
            'account_invoice_template.wizard_select_template').id
        view_id = view_rec or False

        return {
            'view_type': 'form',
            'view_id': [view_id],
            'view_mode': 'form',
            'res_model': 'wizard.select.invoice.template',
            'res_id': wizard.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': self.env.context,
        }

    def load_template(self):
        template_obj = self.env['account.invoice.template']
        account_invoice_obj = self.env['account.invoice']
        account_invoice_line_obj = self.env['account.invoice.line']
        wizard = self
        if not template_obj.check_zero_lines(wizard):
            raise UserError(
                _('Error !'),
                _('At least one amount has to be non-zero!'))
        input_lines = {}
        for template_line in wizard.line_ids:
            input_lines[template_line.sequence] = template_line.amount
        computed_lines = wizard.template_id.compute_lines(input_lines)
        inv_values = account_invoice_obj.get_invoice_values(
            wizard.template_id.type,
            wizard.template_id.partner_id.id)['value']
        inv_values['partner_id'] = wizard.template_id.partner_id.id
        inv_values['account_id'] = wizard.template_id.account_id.id
        inv_values['type'] = wizard.template_id.type
        self = self.with_context(type=wizard.template_id.type)
        inv_id = self.env['account.invoice'].create(inv_values)
        for line in wizard.template_id.template_line_ids:
            analytic_account_id = False
            if line.analytic_account_id:
                analytic_account_id = line.analytic_account_id.id
            invoice_line_tax_id = []
            if line.invoice_line_tax_id:
                tax_ids = []
                for tax in line.invoice_line_tax_id:
                    tax_ids.append(tax.id)
                invoice_line_tax_id.append((6, 0, tax_ids))
            val = {
                'name': line.name,
                'invoice_id': inv_id.id,
                'account_analytic_id': analytic_account_id,
                'account_id': line.account_id.id,
                'invoice_line_tax_ids': invoice_line_tax_id,
                'price_unit': computed_lines[line.sequence],
                'product_id': line.product_id.id,
            }
            account_invoice_line_obj.with_context(self.env.context).create(val)

        if wizard.template_id.type in ('out_invoice', 'out_refund'):
            xml_id = 'invoice_form'
        else:
            xml_id = 'invoice_supplier_form'
        resource_id = self.env.ref('account.' + xml_id).id

        return {
            'domain': "[('id','in', [" + str(inv_id.id) + "])]",
            'name': 'Invoice',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice',
            'views': [(resource_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': inv_id.id or False,
        }


class WizardSelectTemplateLine(models.TransientModel):

    _description = 'Template Lines'
    _name = "wizard.select.invoice.template.line"

    template_id = fields.Many2one(
        'wizard.select.invoice.template', 'Template')
    sequence = fields.Integer('Number', required=True)
    name = fields.Char('Name', size=64, required=True, readonly=True)
    account_id = fields.Many2one(
        'account.account', 'Account',
        required=True, readonly=True)
    amount = fields.Float('Amount', required=True)
    product_id = fields.Many2one('product.product', 'Product')


class AccountInvoice(models.Model):

    _inherit = 'account.invoice'

    def get_invoice_values(self, type, partner_id):
        partner_payment_term = False
        acc_id = False
        bank_id = False
        fiscal_position = False

        opt = [('uid', self.env.uid)]
        if partner_id:
            opt.insert(0, ('id', partner_id))
            p = self.env['res.partner'].browse(partner_id)
            if self.company_id:
                if (p.property_account_receivable_id.company_id and (p.property_account_receivable_id.company_id.id != company_id)) and (p.property_account_payable.company_id and (p.property_account_payable.company_id.id != company_id)):
                    property_obj = self.env['ir.property']
                    rec_pro_id = property_obj.search([
                        ('name', '=', 'property_account_receivable_id'),
                        ('res_id', '=', 'res.partner,'+str(partner_id) + ''),
                        ('company_id', '=', self.company_id)])
                    pay_pro_id = property_obj.search([
                        ('name', '=', 'property_account_payable'),
                        ('res_id', '=', 'res.partner,'+str(partner_id) + ''),
                        ('company_id', '=', self.company_id)])
                    if not rec_pro_id:
                        rec_pro_id = property_obj.search([
                            ('name', '=', 'property_account_receivable_id'),
                            ('company_id', '=', self.company_id)])
                    if not pay_pro_id:
                        pay_pro_id = property_obj.search([
                            ('name', '=', 'property_account_payable'),
                            ('company_id', '=', self.company_id)])
                    rec_line_data = property_obj.read(
                        rec_pro_id,
                        ['name', 'value_reference', 'res_id'])
                    pay_line_data = property_obj.read(
                        pay_pro_id,
                        ['name', 'value_reference', 'res_id'])
                    rec_res_id = rec_line_data and rec_line_data[0].get(
                        'value_reference', False) and \
                        int(rec_line_data[0]['value_reference'].split(',')[1]) or False
                    pay_res_id = pay_line_data and pay_line_data[0].get(
                        'value_reference', False) and \
                        int(pay_line_data[0]['value_reference'].split(',')[1]) or False
                    if not rec_res_id and not pay_res_id:
                        raise UserError(
                            _('Configuration Error!'),
                            _('Cannot find a chart of accounts for this company, you should create one.'))
                    account_obj = self.env['account.account']
                    rec_obj_acc = account_obj.browse([rec_res_id])
                    pay_obj_acc = account_obj.browse([pay_res_id])
                    p.property_account_receivable_id = rec_obj_acc[0]
                    p.property_account_payable = pay_obj_acc[0]

            if type in ('out_invoice', 'out_refund'):
                acc_id = p.property_account_receivable_id.id
                partner_payment_term = p.property_payment_term_id and \
                    p.property_payment_term_id.id or False
            else:
                acc_id = p.property_account_payable.id
                partner_payment_term = p.property_supplier_payment_term and \
                    p.property_supplier_payment_term.id or False
            fiscal_position = p.property_account_position_id and \
                p.property_account_position_id.id or False
            if p.bank_ids:
                bank_id = p.bank_ids[0].id
        result = {'value': {
            'account_id': acc_id,
            'payment_term_id': partner_payment_term,
            'fiscal_position_id': fiscal_position
            }
        }

        if type in ('in_invoice', 'in_refund'):
            result['value']['partner_bank_id'] = bank_id

        if self.payment_term_id and self.payment_term_id.id != partner_payment_term:
            if partner_payment_term:
                to_update = self._onchange_payment_term_date_invoice()
                result['value'].update(to_update['value'])
            else:
                result['value']['date_due'] = False

        if self.partner_bank_id != bank_id:
            to_update = self.onchange_partner_bank(bank_id)
            result['value'].update(to_update['value'])
        return result

    def onchange_partner_bank(self, partner_bank_id=False):
        return {'value': {}}
