from odoo import models, fields

class ChungChi(models.Model):
    _name = 'nhan_su.chung_chi'
    _description = 'Chung chi'

    name = fields.Char(string='Ten chung chi', required=True)
    nhan_vien_id = fields.Many2one('nhan_vien', required=True, ondelete='cascade', string='Nhan vien')
    don_vi_cap = fields.Char(string='Don vi cap')
    ngay_cap = fields.Date(string='Ngay cap')
    ngay_het_han = fields.Date(string='Ngay het han')
    tep = fields.Binary(string='Tep chung chi', attachment=True)
    mo_ta = fields.Text(string='Mo ta')
