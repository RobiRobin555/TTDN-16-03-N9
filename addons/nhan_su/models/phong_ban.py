from odoo import models, fields

class PhongBan(models.Model):
    _name = 'nhan_su.phong_ban'
    _description = 'Phong ban'

    name = fields.Char(string='Ten phong ban', required=True)
    ma_phong = fields.Char(string='Ma phong')
    parent_id = fields.Many2one('nhan_su.phong_ban', string='Phong ban cha')
    quan_ly_id = fields.Many2one('nhan_vien', string='Quan ly')
