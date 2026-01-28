from odoo import models, fields

class NhanVien(models.Model):
    _name = 'nhan_vien'
    _description = 'Bang chua thong tin nhan vien'

    ma_dinh_danh = fields.Char('Ma dinh danh', required=True)
    ngay_sinh = fields.Date('Ngay sinh')
    que_quan = fields.Char('Que quan')
    email = fields.Char('Email')
    so_dien_thoai = fields.Char('So dien thoai')
    phong_ban_id = fields.Many2one('nhan_su.phong_ban', string='Phong ban')
    cham_cong_ids = fields.One2many('nhan_su.cham_cong', 'nhan_vien_id', string='Cham cong')
    chung_chi_ids = fields.One2many('nhan_su.chung_chi', 'nhan_vien_id', string='Chung chi')
    lich_su_ids = fields.One2many('nhan_su.lich_su_cong_tac', 'nhan_vien_id', string='Lich su cong tac')
