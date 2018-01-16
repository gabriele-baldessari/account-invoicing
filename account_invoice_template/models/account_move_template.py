# -*- coding: utf-8 -*-

from odoo import fields, models, api, exceptions, _


class AccountDocumentTemplate(models.Model):

    _inherit = 'account.document.template'

    def check_zero_lines(self, wizard):
        if not wizard.line_ids:
            return True
        for template_line in wizard.line_ids:
            if template_line.amount:
                return True
        return False

    @api.multi
    def compute_lines(self, input_lines):
        if len(input_lines) != self._input_lines():
            raise exceptions.Warning(
                _('You can not add a different number of lines in this wizard '
                  'you should try to create the move normally and then edit '
                  'the created move. Inconsistent between input lines and '
                  ' filled lines for template %s') % self.name
            )
        computed_lines = self._generate_empty_lines()
        computed_lines.update(input_lines)
        for line_number in computed_lines:
            computed_lines[line_number] = self.lines(
                line_number, computed_lines)
        return computed_lines
