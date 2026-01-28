# -*- coding: utf-8 -*-
{
    'name': 'Nhan Su',
    'version': '1.0',
    'summary': 'Quan ly nhan su',
    'description': 'Module quan ly nhan su',
    'category': 'Human Resources',
    'author': 'Manh Linh',
    'depends': ['base', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'views/cham_cong.xml',
        'views/chung_chi.xml',
        'views/phong_ban.xml',
        'views/lich_su_cong_tac.xml',
        'views/nhan_vien.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
