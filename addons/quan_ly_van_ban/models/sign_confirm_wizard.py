import base64
import urllib.parse
import time
from odoo import models, fields, api, _

class SignConfirmWizard(models.TransientModel):
    _name = "qlvb.sign.confirm.wizard"
    _description = "Xem trước file đã ký trước khi lưu"

    document_id = fields.Many2one("qlvb.document", string="Văn bản gốc", required=True)
    file_generated = fields.Binary(string="File vừa ký xong", required=True, attachment=False)
    file_name = fields.Char(string="Tên file")
    
    # Trường HTML để hiển thị Preview trong Pop-up
    pdf_preview = fields.Html(compute='_compute_pdf_preview', string="Xem trước", sanitize=False)

    @api.depends('file_generated')
    def _compute_pdf_preview(self):
        for rec in self:
            if rec.file_generated:
                base_url = rec.env['ir.config_parameter'].sudo().get_param('web.base.url') or ''
                
                # Timestamp để chống cache
                timestamp = int(time.time() * 1000)
                
                # URL trỏ vào chính Wizard này (model tạm)
                # Lưu ý: model là qlvb.sign.confirm.wizard
                pdf_url = f"/web/content/qlvb.sign.confirm.wizard/{rec.id}/file_generated?t={timestamp}"
                
                # Dùng Embed để xem
                rec.pdf_preview = f"""
                    <embed src="{pdf_url}" 
                           type="application/pdf"
                           width="100%" 
                           height="700px"
                           style="border:none;">
                    </embed>
                """
            else:
                rec.pdf_preview = "<div style='text-align:center; padding:50px;'>Đang tải file...</div>"

    def action_confirm_save(self):
        """ 
        Người dùng đồng ý -> Ghi file từ Wizard vào Hồ sơ chính (qlvb.document)
        """
        self.ensure_one()
        doc = self.document_id
        
        # 1. Lưu file song song với file gốc
        doc.file_signed = self.file_generated
        doc.file_signed_name = self.file_name
        
        # 2. Tự động chuyển chế độ xem sang 'File đã ký'
        doc.preview_type = 'signed' 
        
        # 3. Ghi log
        doc._add_history(doc.state, doc.state, note="Đã xác nhận và lưu trữ bản ký số")
        doc.message_post(body="✅ Đã ký số và lưu trữ thành công.")
        
        # 4. Đóng Wizard và Reload lại trang mẹ để hiển thị file mới
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_cancel(self):
        """ Hủy bỏ -> Không làm gì cả, đóng window """
        return {'type': 'ir.actions.act_window_close'}