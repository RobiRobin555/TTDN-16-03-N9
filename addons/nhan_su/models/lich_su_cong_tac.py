from odoo import models, fields

class LichSuCongTac(models.Model):
    _name = 'nhan_su.lich_su_cong_tac'
    _description = 'Lich su cong tac'
    _order = 'tu_ngay desc'

    nhan_vien_id = fields.Many2one('nhan_vien', required=True, ondelete='cascade', string='Nhan vien')
    phong_ban_id = fields.Many2one('nhan_su.phong_ban', string='Phong ban')
    chuc_danh = fields.Char(string='Chuc danh')
    tu_ngay = fields.Date(string='Tu ngay', required=True)
    den_ngay = fields.Date(string='Den ngay')
    mo_ta = fields.Text(string='Mo ta')
