{
    'name': 'Project Funding',
    'version': '1.0',
    'summary': 'Management proiecte: devize, achizitii, activitati, rambursare',
    'description': """
        Aplicatie pentru gestionarea proiectelor finantate:
        - Devize detaliate
        - Achizitii
        - Activitati
        - Grafic rambursare
        - Beneficiari si date proiect
    """,
    'author': 'Sorin',
    'license': 'LGPL-3',

    # Dependințe Odoo
    'depends': ['base', 'web'],

    # Date care se încarcă la instalare
    'data': [
        'security/ir.model.access.csv',
        'data/module_category.xml',
        'views/project_funding_views.xml',
    	'views/project_activity_views.xml',          # ← ADĂUGĂ
        'views/project_acquisition_views.xml',
      ],

    # Assets pentru interfață (CSS custom pentru Deviz + layout formular)
	'assets': {
    		'web.assets_backend': [
        	'project_funding/static/src/css/deviz_styles.css',
        	'project_funding/static/src/css/project_funding.css',
        	'project_funding/static/src/js/project_budget_confirm_delete.js',
    ],
},

    # Iconița aplicației
    'images': [
        'static/description/icon.png',
    ],

    # Categoria aplicației (după ce ai definit-o în module_category.xml)
    'category': 'Project',

    # Setări instalare
    'installable': True,
    'application': True,
}
