from odoo import models, fields

class ResPartner(models.Model):
    _inherit = "res.partner"

    document_ids = fields.One2many("qlvb.document", "partner_id", string="Hồ sơ số hóa")
    document_count = fields.Integer(compute="_compute_document_count")

    def _compute_document_count(self):
        for rec in self:
            rec.document_count = len(rec.document_ids)
