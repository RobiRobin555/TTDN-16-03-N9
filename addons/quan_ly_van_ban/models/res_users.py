from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
import os
import time

# [THAY ĐỔI] Dùng OpenSSL thay vì cryptography để tương thích server cũ
try:
    from OpenSSL import crypto
except ImportError:
    crypto = None

class ResUsers(models.Model):
    _inherit = 'res.users'

    # Ảnh chữ ký hiển thị trên PDF (file PNG nền trong suốt)
    signing_signature = fields.Binary(string="Ảnh chữ ký (PNG)")
    
    # File khóa cá nhân (.p12) - Tự sinh
    signing_cert_file = fields.Binary(string="File Chứng thư số (.p12)", attachment=True, readonly=True)
    signing_cert_filename = fields.Char(string="Tên file P12")
    signing_cert_password = fields.Char(string="Mật khẩu P12", readonly=True, groups="base.group_user")
    
    # Thông tin bổ sung cho chứng thư
    cert_organization = fields.Char(string="Tổ chức", default="My Company")
    cert_job_title = fields.Char(string="Chức vụ/Đơn vị", default="Staff")

    def action_generate_digital_key(self):
        """Hàm tự động sinh khóa P12 cho user dùng thư viện OpenSSL"""
        self.ensure_one()
        if not crypto:
            raise UserError("Hệ thống thiếu thư viện 'pyOpenSSL'.")

        try:
            # 1. Tạo cặp khóa (Key Pair) RSA 2048
            k = crypto.PKey()
            k.generate_key(crypto.TYPE_RSA, 2048)

            # 2. Tạo Chứng thư số (Certificate)
            cert = crypto.X509()
            
            # Cấu hình thông tin chủ thể (Subject)
            subj = cert.get_subject()
            subj.C = "VN"  # Country
            subj.O = self.cert_organization or "My Company" # Organization
            subj.OU = self.cert_job_title or "Staff"        # Organizational Unit
            subj.CN = self.name                             # Common Name (Tên người ký)
            
            # Email (OpenSSL set email hơi khác một chút nên ta gán vào CN hoặc bỏ qua nếu phức tạp)
            # Ở đây ta dùng Common Name là quan trọng nhất để định danh
            
            # Cấu hình Serial Number (Random)
            cert.set_serial_number(int(time.time() * 1000))
            
            # Cấu hình thời hạn (5 năm = 5 * 365 * 24h * 60m * 60s)
            cert.gmtime_adj_notBefore(0)
            cert.gmtime_adj_notAfter(5 * 365 * 24 * 60 * 60)
            
            # Tự ký (Issuer = Subject)
            cert.set_issuer(cert.get_subject())
            
            # Gán Public Key vào Cert
            cert.set_pubkey(k)
            
            # Ký Cert bằng Private Key (SHA256)
            cert.sign(k, 'sha256')

            # 3. Đóng gói thành file P12
            p12 = crypto.PKCS12()
            p12.set_privatekey(k)
            p12.set_certificate(cert)
            
            # Tạo mật khẩu ngẫu nhiên
            p12_password = base64.b64encode(os.urandom(12)).decode('utf-8')
            
            # Export ra binary (passphrase phải là bytes)
            p12_data = p12.export(passphrase=p12_password.encode('utf-8'))

            # 4. Lưu vào Odoo
            self.write({
                'signing_cert_file': base64.b64encode(p12_data),
                'signing_cert_filename': f"{self.login}_signature.p12",
                'signing_cert_password': p12_password
            })

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Thành công',
                    'message': f'Đã tạo chữ ký số mới cho {self.name} (OpenSSL Core)!',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(f"Lỗi khi tạo khóa OpenSSL: {str(e)}")