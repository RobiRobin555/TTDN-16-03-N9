from odoo import models, fields, api

class ChamCong(models.Model):
    _name = 'nhan_su.cham_cong'
    _description = 'Cham cong'

    nhan_vien_id = fields.Many2one('nhan_vien', required=True, ondelete='cascade', string='Nhan vien')
    ngay = fields.Date(required=True, string='Ngay')
    gio_vao = fields.Datetime(string='Gio vao')
    gio_ra = fields.Datetime(string='Gio ra')
    so_gio_lam_viec = fields.Float(string='So gio lam viec', compute='_compute_so_gio', store=True)

    @api.depends('gio_vao', 'gio_ra')
    def _compute_so_gio(self):
        for rec in self:
            if rec.gio_vao and rec.gio_ra and rec.gio_ra > rec.gio_vao:
                delta = fields.Datetime.to_datetime(rec.gio_ra) - fields.Datetime.to_datetime(rec.gio_vao)
                rec.so_gio_lam_viec = delta.total_seconds() / 3600.0
            else:
                rec.so_gio_lam_viec = 0.0
