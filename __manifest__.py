{
    "name": "Ecuadorian Multi Invoice Payment For Customer and Vendor",
    'version': '18.01',
    "description": """
        Con este módulo, puede pagar varias facturas con un solo clic.
        Pago de varias facturas | Conciliación de varias facturas
        Conciliación de pagos parciales de facturas
    """,
    'icon': '/account/static/description/l10n.png',
    'countries': ['ec'],
    'author': 'Elmer Salazar Arias',
    'category': 'Accounting/Localizations/Payments',
    'maintainer': 'Elmer Salazar Arias',
    'website': 'http://www.galapagos.tech',
    'email': 'esalazargps@gmail.com',
    'license': 'LGPL-3',
    "depends": [
        "account",
        'l10n_ec_edi',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/account_payment_views.xml'
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
