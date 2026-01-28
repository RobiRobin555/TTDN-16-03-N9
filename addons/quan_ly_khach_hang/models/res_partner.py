from odoo import models, fields

class ResPartner(models.Model):
    _inherit = "res.partner"

    customer_code = fields.Char(string="Mã khách hàng")
    customer_type = fields.Selection([
        ("individual", "Cá nhân"),
        ("company", "Doanh nghiệp")
    ], string="Loại khách hàng")
    customer_status = fields.Selection([
        ("potential", "Tiềm năng"),
        ("active", "Đang giao dịch"),
        ("inactive", "Ngừng hợp tác")
    ], string="Trạng thái khách hàng")
    responsible_employee_id = fields.Many2one("hr.employee", string="Nhân viên phụ trách chính")
    participant_employee_ids = fields.Many2many(
        "hr.employee",
        "res_partner_hr_employee_rel",
        "partner_id",
        "employee_id",
        string="Nhân viên tham gia"
    )
    work_history_ids = fields.One2many("qlkh.partner.work.history", "partner_id", string="Lịch sử làm việc")
