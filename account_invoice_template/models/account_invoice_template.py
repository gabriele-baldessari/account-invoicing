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

from odoo import fields, models, api


class AccountInvoiceTemplate(models.Model):

    _inherit = 'account.document.template'
    _name = 'account.invoice.template'

    partner_id = fields.Many2one(
        'res.partner',
        'Partner',
        required=True)
    account_id = fields.Many2one(
        'account.account',
        'Account',
        required=True)
    template_line_ids = fields.One2many(
        'account.invoice.template.line',
        'template_id',
        'Template Lines')
    type = fields.Selection([
        ('out_invoice', 'Customer Invoice'),
        ('in_invoice', 'Supplier Invoice'),
        ('out_refund', 'Customer Refund'),
        ('in_refund', 'Supplier Refund')],
        string='Type',
        required=True)


class AccountInvoiceTemplateLine(models.Model):

    _name = 'account.invoice.template.line'
    _inherit = 'account.document.template.line'

    account_id = fields.Many2one(
        'account.account',
        'Account',
        required=True)
    analytic_account_id = fields.Many2one(
        string='Analytic Account',
        comodel_name='account.analytic.account',
        ondelete='cascade')
    invoice_line_tax_id = fields.Many2many(
        string='Taxes',
        comodel_name='account.tax',
        relation='account_invoice_template_line_tax',
        column1='invoice_line_id',
        column2='tax_id')
    template_id = fields.Many2one(
        'account.invoice.template',
        'Template',
        ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product')

    _sql_constraints = [
        ('sequence_template_uniq', 'unique (template_id,sequence)',
            'The sequence of the line must be unique per template !')
    ]

    @api.onchange('product_id')
    def product_id_change(self):
        result = {}
        if not self.product_id:
            return {}
        product = self.product_id
        # name
        result.update({'name': product.name})
        # account
        account_id = False
        if self.template_id.type in ('out_invoice', 'out_refund'):
            account_id = product.product_tmpl_id.property_account_income_id.id
            if not account_id:
                account_id = product.categ_id.property_account_income_categ_id.id
        else:
            account_id = product.product_tmpl_id.property_account_expense_id.id
            if not account_id:
                account_id = product.categ_id.property_account_expense_categ_id.id
        if account_id:
            result['account_id'] = account_id
        # taxes
        account_obj = self.env['account.account']
        taxes = account_id and account_obj.browse(account_id).tax_ids or False
        if self.template_id.type in ('out_invoice', 'out_refund') and product.taxes_id:
            taxes = product.taxes_id
        elif product.supplier_taxes_id:
            taxes = product.supplier_taxes_id
        tax_ids = taxes and [tax.id for tax in taxes] or False
        result.update({'invoice_line_tax_id': tax_ids})

        return {'value': result}
