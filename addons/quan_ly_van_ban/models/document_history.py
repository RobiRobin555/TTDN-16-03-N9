from odoo import models, fields

class QLVBDocumentHistory(models.Model):
    _name = "qlvb.document.history"
    _order = "date desc, id desc"

    document_id = fields.Many2one("qlvb.document", required=True, ondelete="cascade", string="Tài liệu")
    date = fields.Datetime(default=fields.Datetime.now, string="Ngày")
    from_state = fields.Char(string="Từ trạng thái")
    to_state = fields.Char(string="Sang trạng thái")
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user, string="Người thực hiện")
    note = fields.Text(string="Ghi chú")
