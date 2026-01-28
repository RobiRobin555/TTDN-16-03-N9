{
    "name": "Quản lý Văn bản",
    "version": "15.0.1.0.0",
    "category": "Custom",
    "summary": "Quản lý văn bản số hóa, quy trình duyệt và cảnh báo",
    "depends": ["base", "hr", "web", "mail", "quan_ly_khach_hang"],
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        'data/ir_config_parameter.xml', # Load file config
        'views/res_users_views.xml',
        'views/verify_wizard_views.xml',
        "views/document_views.xml",
        "views/sign_confirm_wizard_views.xml",
        "views/res_partner_inherit_views.xml",
        "data/ir_cron.xml"
    ],
    # ĐÃ XÓA PHẦN ASSETS ĐỂ KHÔNG BỊ LỖI FILE NOT FOUND
    "application": True,
    "auto_install": True,
    "license": "LGPL-3"
}