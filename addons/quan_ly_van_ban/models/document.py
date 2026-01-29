import requests
import base64
import time
import urllib.parse
import re
import unicodedata
import io
import mimetypes
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError

# Import thư viện xử lý ảnh
try:
    from PIL import Image
except ImportError:
    Image = None

# Import thư viện PDF
try:
    from PyPDF2 import PdfFileReader
    PYPDF_VERSION = 2
except ImportError:
    try:
        from pypdf import PdfReader as PdfFileReader
        PYPDF_VERSION = 3
    except ImportError:
        PdfFileReader = None

class QLVBDocument(models.Model):
    _name = "qlvb.document"
    _description = "Văn bản số hóa"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    def _slugify_name(self, text):
        if not text: return ""
        text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
        text = re.sub(r'[^\w\s-]', '', text).strip().lower()
        return re.sub(r'[-\s]+', '_', text)

    # --- CÁC TRƯỜNG DỮ LIỆU ---
    name = fields.Char(required=True, string="Tên tài liệu")
    document_type = fields.Selection([
        ("contract", "Hợp đồng"), ("quotation", "Báo giá"),
        ("legal", "Pháp lý"), ("other", "Khác")
    ], required=True, string="Loại tài liệu")
    
    file = fields.Binary(attachment=True, string="File tài liệu (PDF/Ảnh)")
    partner_id = fields.Many2one("res.partner", required=True, string="Khách hàng")
    employee_id = fields.Many2one("hr.employee", required=True, string="Nhân viên xử lý")
    upload_date = fields.Date(default=fields.Date.context_today, string="Ngày upload")
    expiry_date = fields.Date(string="Ngày hết hạn")
    version = fields.Char(string="Phiên bản tài liệu")
    
    state = fields.Selection([
        ("draft", "Nháp"), ("submitted", "Trình duyệt"),
        ("approved", "Đã duyệt"), ("archived", "Lưu trữ")
    ], default="draft", tracking=True, string="Trạng thái xử lý")
    
    history_ids = fields.One2many("qlvb.document.history", "document_id", string="Lịch sử trạng thái")

    # --- KÝ SỐ ---
    file_signed = fields.Binary(string="File đã ký số", attachment=True, readonly=True)
    file_signed_name = fields.Char(string="Tên file đã ký")
    custom_sign_image = fields.Binary(string="Ảnh chữ ký (Tùy chọn)", attachment=True)

    sign_position_preset = fields.Selection([
        ('custom', '✍️ Tự nhập tọa độ'),
        ('top_left', '↖️ Góc trên - Trái'), ('top_right', '↗️ Góc trên - Phải'),
        ('bottom_left', '↙️ Góc dưới - Trái'), ('bottom_right', '↘️ Góc dưới - Phải'),
        ('center_bottom', '⬇️ Giữa - Dưới cùng')
    ], string="Vị trí ký", default='bottom_right')

    sign_page = fields.Integer(string="Trang ký", default=1)
    sign_x = fields.Integer(string="Tọa độ X", default=400)
    sign_y = fields.Integer(string="Tọa độ Y", default=50)

    # --- HÀM HỖ TRỢ: CHUYỂN ẢNH SANG PDF ---
    def _convert_image_to_pdf_bytes(self, file_base64):
        file_content = base64.b64decode(file_base64)
        is_image = False
        
        filename = str(self.name).lower()
        if filename.endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            is_image = True
        
        if not is_image and Image:
            try:
                img = Image.open(io.BytesIO(file_content))
                img.verify()
                is_image = True
            except: pass

        if is_image and Image:
            try:
                image = Image.open(io.BytesIO(file_content))
                if image.mode in ("RGBA", "P"): image = image.convert("RGB")
                output = io.BytesIO()
                image.save(output, format="PDF", resolution=100.0)
                return output.getvalue(), True
            except Exception as e:
                raise UserError(f"Lỗi chuyển đổi ảnh: {e}")
        
        return file_content, False

    # --- TÍNH TỌA ĐỘ ---
    @api.onchange('sign_position_preset', 'sign_page', 'file')
    def _onchange_sign_position(self):
        if not self.file or self.sign_position_preset == 'custom': return
        if PdfFileReader is None:
            if self.sign_position_preset == 'bottom_right': self.sign_x = 400; self.sign_y = 50
            return

        try:
            pdf_bytes, _ = self._convert_image_to_pdf_bytes(self.file)
            pdf_stream = io.BytesIO(pdf_bytes)
            r = PdfFileReader(pdf_stream)
            
            if PYPDF_VERSION == 3:
                num_pages = len(r.pages)
                page_idx = max(0, self.sign_page - 1)
                if page_idx >= num_pages: 
                    page_idx = num_pages - 1
                    self.sign_page = num_pages
                page = r.pages[page_idx]
                page_width = float(page.mediabox.width)
                page_height = float(page.mediabox.height)
            else:
                num_pages = r.numPages
                page_idx = max(0, self.sign_page - 1)
                if page_idx >= num_pages: 
                    page_idx = num_pages - 1
                    self.sign_page = num_pages
                page = r.getPage(page_idx)
                page_width = float(page.mediaBox[2])
                page_height = float(page.mediaBox[3])

            sig_w = 150; sig_h = 60; margin = 20

            if self.sign_position_preset == 'top_left':
                self.sign_x = margin; self.sign_y = int(page_height - sig_h - margin)
            elif self.sign_position_preset == 'top_right':
                self.sign_x = int(page_width - sig_w - margin); self.sign_y = int(page_height - sig_h - margin)
            elif self.sign_position_preset == 'bottom_left':
                self.sign_x = margin; self.sign_y = margin
            elif self.sign_position_preset == 'bottom_right':
                self.sign_x = int(page_width - sig_w - margin); self.sign_y = margin
            elif self.sign_position_preset == 'center_bottom':
                self.sign_x = int((page_width - sig_w) / 2); self.sign_y = margin

        except Exception:
            if self.sign_position_preset == 'bottom_right': self.sign_x = 400; self.sign_y = 50

    preview_type = fields.Selection([
        ('original', '📄 Xem Tài liệu Gốc'),
        ('signed', '✍️ Xem File Đã Ký')
    ], string="Chế độ xem", default='original')

    pdf_preview = fields.Html(compute='_compute_pdf_preview', string="Xem trước", sanitize=False)

    @api.depends('file', 'file_signed', 'preview_type', 'create_date', 'write_date')
    def _compute_pdf_preview(self):
        for rec in self:
            real_id = rec.id
            if not real_id and hasattr(rec, '_origin') and rec._origin:
                real_id = rec._origin.id
            
            is_stored_in_db = real_id and isinstance(real_id, int)
            timestamp = int(time.time() * 1000)

            if rec.preview_type == 'signed':
                if rec.file_signed:
                    if is_stored_in_db:
                        pdf_url = f"/web/content/qlvb.document/{real_id}/file_signed?t={timestamp}"
                        rec.pdf_preview = f"""<embed src="{pdf_url}" type="application/pdf" width="100%" height="750px" style="border:none;"></embed>"""
                    else:
                        rec.pdf_preview = "<div style='text-align:center; padding:50px;'>Vui lòng lưu để xem file đã ký.</div>"
                else:
                    rec.pdf_preview = "<div style='text-align:center; padding:50px; color:red;'>⚠️ Chưa có bản ký số.</div>"
                continue

            if rec.file:
                fname = (rec.name or "file").lower()
                mime_type, _ = mimetypes.guess_type(fname)
                if not mime_type:
                    if fname.endswith(('.jpg', '.jpeg')): mime_type = 'image/jpeg'
                    elif fname.endswith('.png'): mime_type = 'image/png'
                    else: mime_type = 'application/pdf'

                is_image = mime_type.startswith('image')

                if is_stored_in_db:
                    if is_image:
                        img_url = f"/web/image?model=qlvb.document&id={real_id}&field=file&t={timestamp}"
                        rec.pdf_preview = f"""
                            <div style="text-align: center; background: #e9ecef; padding: 20px; height: 750px; overflow: auto;">
                                <img src="{img_url}" style="max-width: 90%; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"/>
                            </div>
                        """
                    else:
                        file_url = f"/web/content/qlvb.document/{real_id}/file?t={timestamp}"
                        rec.pdf_preview = f"""<embed src="{file_url}" type="application/pdf" width="100%" height="750px" style="border:none;"></embed>"""
                else:
                    file_size_mb = len(rec.file) / (1024 * 1024)
                    if file_size_mb > 5.0:
                        rec.pdf_preview = f"""<div style='text-align:center; padding:50px;'>File lớn ({round(file_size_mb, 2)} MB). Bấm Lưu để xem.</div>"""
                    else:
                        try:
                            b64_str = rec.file.decode('utf-8')
                            if is_image:
                                rec.pdf_preview = f"""
                                    <div style="text-align: center; background: #e9ecef; padding: 20px; height: 750px; overflow: auto;">
                                        <img src="data:{mime_type};base64,{b64_str}" style="max-width: 90%; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"/>
                                    </div>
                                """
                            else:
                                rec.pdf_preview = f"""<embed src="data:application/pdf;base64,{b64_str}" type="application/pdf" width="100%" height="750px" style="border:none;"></embed>"""
                        except Exception as e:
                            rec.pdf_preview = f"<div style='text-align:center;'>Lỗi hiển thị: {str(e)}</div>"
            else:
                rec.pdf_preview = "<div style='text-align:center; padding:100px; color: #666;'><h3>📂 Vui lòng chọn file (PDF, JPG, PNG)</h3></div>"

    # --- API KÝ SỐ  ---
    def action_sign_via_api(self):
        self.ensure_one()
        user = self.env.user 
        
        # 1. Kiểm tra File
        if not self.file: 
            raise UserError("Vui lòng đính kèm file.")
        
        # 2. Kiểm tra Chữ ký (Ảnh)
        signature_to_use = self.custom_sign_image or user.signing_signature
        if not signature_to_use: 
            raise UserError(f"Bạn ({user.name}) chưa có ảnh chữ ký. Vui lòng vào Hồ sơ cá nhân -> Tab Chữ ký số để upload ảnh.")
        
        # 3. Kiểm tra Khóa bảo mật (P12)
        if not user.signing_cert_file: 
            raise UserError(f"Bạn ({user.name}) chưa có Khóa bảo mật (.p12). Vui lòng vào Hồ sơ cá nhân -> Tab Chữ ký số -> Bấm 'Tạo khóa mới'.")

        api_url = self.env['ir.config_parameter'].sudo().get_param('pdf.api.url')
        if not api_url: 
            raise UserError("Chưa cấu hình pdf.api.url")
        endpoint = f"{api_url}/sign-pdf/"

        try:
            # 4. Chuẩn bị dữ liệu gửi đi
            pdf_bytes, converted = self._convert_image_to_pdf_bytes(self.file)
            fname = self.name
            if converted or not str(fname).lower().endswith('.pdf'):
                fname = f"{fname}.pdf"

            files = {
                'pdf_file': (fname, pdf_bytes, 'application/pdf'),
                'image_file': ('sign.png', base64.b64decode(signature_to_use), 'image/png'),
               
                'cert_file': (f"{user.login}_key.p12", base64.b64decode(user.signing_cert_file), 'application/x-pkcs12'),
            }
            
           
            data = {
                'password': user.signing_cert_password or '',
                'page_number': self.sign_page,
                'x_coord': self.sign_x, 'y_coord': self.sign_y,
                'width': 150, 'height': 60
            }
            
            response = requests.post(endpoint, files=files, data=data, timeout=30)

            if response.status_code == 200:
                signed_content = base64.b64encode(response.content)
                clean_filename = self._slugify_name(self.name)
                clean_username = self._slugify_name(user.name)
                signed_name = f"{clean_filename}_signed_by_{clean_username}.pdf"

                # Tạo Wizard xem trước
                wizard = self.env['qlvb.sign.confirm.wizard'].create({
                    'document_id': self.id,
                    'file_generated': signed_content,
                    'file_name': signed_name,
                })
                
                return {
                    'name': 'Kiểm tra & Lưu trữ File Ký số',
                    'type': 'ir.actions.act_window',
                    'res_model': 'qlvb.sign.confirm.wizard',
                    'view_mode': 'form',
                    'res_id': wizard.id,
                    'target': 'new',
                }
            else:
                err_msg = response.text
                try: err_msg = response.json().get('detail', err_msg)
                except: pass
                raise UserError(f"API Error: {err_msg}")

        except requests.exceptions.ConnectionError: raise UserError(f"Không thể kết nối API tại: {api_url}.")
        except Exception as e: raise UserError(f"Lỗi hệ thống: {str(e)}")

    def _add_history(self, from_state, to_state, note=""):
        for rec in self:
            self.env["qlvb.document.history"].create({
                "document_id": rec.id, "from_state": from_state or "", "to_state": to_state or "",
                "user_id": self.env.user.id, "note": note, "date": fields.Datetime.now(),
            })

    def action_submit(self):
        for rec in self:
            if rec.state != "draft": continue
            self._add_history(rec.state, "submitted")
            rec.state = "submitted"
        return True

    def action_approve(self):
        if not (self.env.user.has_group("hr.group_hr_manager") or self.env.user.has_group("base.group_system")):
            raise AccessError("Chỉ Trưởng phòng hoặc HR/Admin được duyệt")
        for rec in self:
            if rec.state != "submitted": continue
            self._add_history(rec.state, "approved")
            rec.state = "approved"
        return True

    def action_archive(self):
        for rec in self:
            if rec.state == "archived": continue
            self._add_history(rec.state, "archived")
            rec.state = "archived"
        return True

    def action_reset_to_draft(self):
        for rec in self:
            if rec.state == "draft": continue
            self._add_history(rec.state, "draft")
            rec.state = "draft"
        return True

    @api.model
    def _cron_check_expiry(self):
        today = fields.Date.context_today(self)
        soon = self.search([("expiry_date", "!=", False), ("expiry_date", ">=", today), ("state", "!=", "archived")])
        todo_type = self.env.ref("mail.mail_activity_data_todo")
        for doc in soon:
            if doc.expiry_date and doc.employee_id and doc.employee_id.user_id:
                existing = self.env["mail.activity"].search([("res_id", "=", doc.id), ("res_model", "=", "qlvb.document"), ("user_id", "=", doc.employee_id.user_id.id), ("summary", "=", "Cảnh báo hết hạn")], limit=1)
                if existing: continue
                self.env["mail.activity"].create({
                    "res_id": doc.id,
                    "res_model": "qlvb.document",
                    "activity_type_id": todo_type.id,
                    "user_id": doc.employee_id.user_id.id,
                    "summary": "Cảnh báo hết hạn",
                    "note": "Tài liệu sắp hết hạn"
                })
        return True

class QLVBDocumentHistory(models.Model):
    _name = "qlvb.document.history"
    _description = "Lịch sử trạng thái tài liệu"

    document_id = fields.Many2one("qlvb.document", string="Tài liệu", ondelete="cascade")
    user_id = fields.Many2one("res.users", string="Người thực hiện")
    date = fields.Datetime(string="Thời gian", default=fields.Datetime.now)
    from_state = fields.Char(string="Từ trạng thái")
    to_state = fields.Char(string="Đến trạng thái")
    note = fields.Text(string="Ghi chú")