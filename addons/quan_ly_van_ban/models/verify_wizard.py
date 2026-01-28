import requests
import base64
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class DocumentVerifyWizard(models.TransientModel):
    _name = "qlvb.verify.wizard"
    _description = "Công cụ Xác thực Văn bản"

    # --- INPUT ---
    file = fields.Binary(string="File PDF", required=True, attachment=False)
    file_name = fields.Char(string="Tên file")
    
    # --- BIẾN ĐIỀU KHIỂN GIAO DIỆN ---
    check_performed = fields.Boolean(default=False, string="Đã bấm kiểm tra chưa")
    has_data = fields.Boolean(default=False, string="Đã có dữ liệu")
    show_result = fields.Boolean(default=False)

    # --- OUTPUT ---
    verification_status = fields.Selection([
        ('VALID', '✅ HỢP LỆ'),
        ('INVALID', '❌ KHÔNG HỢP LỆ'),
        ('TAMPERED', '⚠️ BỊ CHỈNH SỬA'),
        ('UNSIGNED', '⚪ KHÔNG CÓ CHỮ KÝ'),
        ('ERROR', '⛔ LỖI HỆ THỐNG')
    ], string="Trạng thái tổng", readonly=True)

    status_message = fields.Char(string="Thông báo hệ thống", readonly=True)
    signature_ids = fields.One2many('qlvb.verify.signature.line', 'wizard_id', string="Chi tiết chữ ký")

    # --- 1. SỰ KIỆN UPLOAD FILE (Hiện Info ngay) ---
    @api.onchange('file')
    def _onchange_file(self):
        if self.file:
            self._perform_analyze_api()
            # Quan trọng: Đặt False để ẩn kết quả check, chỉ hiện Info
            self.check_performed = False 
            self.has_data = True
            self.show_result = True
        else:
            self.signature_ids = [(5, 0, 0)]
            self.has_data = False
            self.check_performed = False

    # --- 2. SỰ KIỆN BẤM NÚT (Lưu & Hiện kết quả Check) ---
    def action_verify(self):
        # Gọi lại hàm phân tích để lưu dữ liệu cứng vào DB
        self._perform_analyze_api()
        # Đặt True để hiện các cột Valid/Intact
        self.write({'check_performed': True})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'qlvb.verify.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _perform_analyze_api(self):
        """Gọi API và map dữ liệu JSON vào Odoo"""
        api_url = self.env['ir.config_parameter'].sudo().get_param('pdf.api.url')
        if not api_url:
            self.status_message = "Chưa cấu hình 'pdf.api.url'"
            return

        endpoint = f"{api_url}/verify-pdf/"

        try:
            real_name = str(self.file_name) if self.file_name else "document.pdf"
            # Xử lý data file an toàn cho cả onchange và button
            pdf_data = self.file if self.file else b''
            files = {'pdf_file': (real_name, base64.b64decode(pdf_data), 'application/pdf')}
            
            response = requests.post(endpoint, files=files, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                self.verification_status = result.get('status', 'ERROR')
                self.status_message = result.get('status_message')

                lines = []
                self.signature_ids = [(5, 0, 0)] # Xóa cũ
                
                for sig in result.get('signatures', []):
                    # --- Tìm User Odoo (Optional) ---
                    found_owner = "Không xác định"
                    owner_avatar = False
                    signer_email = sig.get('email')
                    signer_name = sig.get('signer_name')

                    user = self.env['res.users'].search([('login', 'ilike', signer_email)], limit=1)
                    if not user and signer_name:
                         user = self.env['res.users'].search([('name', 'ilike', signer_name)], limit=1)
                    
                    if user:
                        found_owner = user.name
                        owner_avatar = user.image_128

                    # --- MAP DỮ LIỆU JSON -> ODOO ---
                    vals = {
                        'signature_index': sig.get('signature_index'),
                        'signer_name': signer_name, # Tên từ PDF (Nguyen Van A)
                        'owner_info': found_owner,  # Tên User Odoo (Nếu khớp)
                        'owner_avatar': owner_avatar,
                        
                        # [QUAN TRỌNG] Lấy Public Key từ JSON
                        'public_key_pem': sig.get('public_key_pem'),
                        
                        'organization': sig.get('organization'),
                        'email': sig.get('email'),
                        'signing_time': sig.get('signing_time'),
                        'is_intact': sig.get('is_intact'),
                        'is_valid': sig.get('is_valid'),
                        'serial_number': sig.get('serial_number'),
                        'issuer': sig.get('issuer'),
                        'cert_valid_from': sig.get('cert_valid_from'),
                        'cert_valid_to': sig.get('cert_valid_to'),
                        'validation_summary': sig.get('validation_summary'),
                    }
                    lines.append((0, 0, vals))
                
                self.signature_ids = lines
            else:
                self.status_message = f"API Error: {response.text}"

        except Exception as e:
            self.status_message = f"Lỗi kết nối: {str(e)}"

class VerifySignatureLine(models.TransientModel):
    _name = "qlvb.verify.signature.line"
    _description = "Chi tiết chữ ký PDF"

    wizard_id = fields.Many2one('qlvb.verify.wizard')
    
    # Biến cờ để giao diện biết đã check chưa (store=True là bắt buộc)
    wizard_checked = fields.Boolean(related='wizard_id.check_performed', store=True)

    # Nhóm 1: Hiện ngay lập tức
    signature_index = fields.Integer(string="#")
    owner_info = fields.Char(string="User hệ thống")
    owner_avatar = fields.Binary(string="Avatar")
    signer_name = fields.Char(string="Tên trong PDF") # Nguyen Van A
    public_key_pem = fields.Text(string="Public Key") # -----BEGIN PUBLIC KEY...
    organization = fields.Char(string="Tổ chức")
    
    # Nhóm 2: Hiện sau khi check
    is_intact = fields.Boolean(string="Toàn vẹn")
    is_valid = fields.Boolean(string="Hợp lệ")
    signing_time = fields.Char(string="Thời gian ký")
    
    # Nhóm 3: Chi tiết
    email = fields.Char(string="Email")
    serial_number = fields.Char(string="Serial")
    issuer = fields.Char(string="Issuer")
    cert_valid_from = fields.Char(string="Valid From")
    cert_valid_to = fields.Char(string="Valid To")
    validation_summary = fields.Char(string="Note")