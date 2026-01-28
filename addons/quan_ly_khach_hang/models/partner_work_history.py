from odoo import models, fields

class PartnerWorkHistory(models.Model):
    _name = "qlkh.partner.work.history"
    _order = "date desc, id desc"

    partner_id = fields.Many2one("res.partner", required=True, string="Khách hàng")
    note = fields.Text(string="Ghi chú")
    date = fields.Datetime(default=fields.Datetime.now, string="Ngày cập nhật")
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user, string="Người cập nhật")
