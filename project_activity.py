from odoo import models, fields, api
from datetime import timedelta


class ProjectActivity(models.Model):
    _name = 'project.activity'
    _description = 'Activitate proiect'
    _order = 'sequence, id'

    project_id = fields.Many2one(
        'project.funding',
        string='Proiect',
        required=True,
        ondelete='restrict',
        index=True,
    )

    name = fields.Char(string='Denumire activitate', required=True)
    code = fields.Char(string='Cod activitate')
    sequence = fields.Integer(string='Ordine', default=10)

    # Fază: înainte / după semnarea contractului
    phase = fields.Selection(
        [
            ('pre', 'Înainte de semnare'),
            ('post', 'După semnare'),
        ],
        string='Fază proiect',
        default='post',
        required=True,
    )

    # ------------------------------
    # DATA DE ÎNCEPUT - CONFIGURABILĂ
    # ------------------------------
    start_source_type = fields.Selection(
        [
            ('project', 'Dată proiect'),
            ('activity', 'Altă activitate'),
        ],
        string="Sursă dată început",
        default='project',
        required=True,
    )

    start_project_ref = fields.Selection(
        [
            ('depunere', 'Data depunerii'),
            ('semnare', 'Data semnării'),
            ('finalizare', 'Data finalizării'),
        ],
        string="Dată proiect pentru început",
        default='semnare',
    )

    start_activity_id = fields.Many2one(
        'project.activity',
        string="Activitate referință (început)",
        domain="[('project_id', '=', project_id)]",
        help="Activitatea din proiect de la care se preia data de început/sfârșit."
    )

    start_activity_ref_type = fields.Selection(
        [
            ('start', 'Data de început a activității'),
            ('end', 'Data de sfârșit a activității'),
        ],
        string="Tip dată referință (început)",
        default='start',
    )

    start_offset_days = fields.Integer(
        string='Offset început (zile)',
        help='Număr de zile (+/-) față de data de referință pentru început.'
    )

    date_start = fields.Date(
        string='Data început',
        compute='_compute_dates',
        store=True,
    )

    # ------------------------------
    # DATA DE SFÂRȘIT - CONFIGURABILĂ
    # ------------------------------
    end_source_type = fields.Selection(
        [
            ('project', 'Dată proiect'),
            ('activity', 'Altă activitate'),
        ],
        string="Sursă dată sfârșit",
        default='project',
        required=True,
    )

    end_project_ref = fields.Selection(
        [
            ('depunere', 'Data depunerii'),
            ('semnare', 'Data semnării'),
            ('finalizare', 'Data finalizării'),
        ],
        string="Dată proiect pentru sfârșit",
        default='semnare',
    )

    end_activity_id = fields.Many2one(
        'project.activity',
        string="Activitate referință (sfârșit)",
        domain="[('project_id', '=', project_id)]",
        help="Activitatea din proiect de la care se preia data de început/sfârșit."
    )

    end_activity_ref_type = fields.Selection(
        [
            ('start', 'Data de început a activității'),
            ('end', 'Data de sfârșit a activității'),
        ],
        string="Tip dată referință (sfârșit)",
        default='end',
    )

    end_offset_days = fields.Integer(
        string='Offset sfârșit (zile)',
        help='Număr de zile (+/-) față de data de referință pentru sfârșit.'
    )

    date_end = fields.Date(
        string='Data sfârșit',
        compute='_compute_dates',
        store=True,
    )

    state = fields.Selection(
        [
            ('draft', 'Planificată'),
            ('in_progress', 'În derulare'),
            ('done', 'Finalizată'),
        ],
        string='Stare',
        default='draft',
    )

    @api.depends(
        'start_source_type',
        'start_project_ref',
        'start_activity_id.date_start',
        'start_activity_id.date_end',
        'start_offset_days',
        'end_source_type',
        'end_project_ref',
        'end_activity_id.date_start',
        'end_activity_id.date_end',
        'end_offset_days',
        'project_id.data_depunere',
        'project_id.data_semnare',
        'project_id.data_finalizare',
    )
    def _compute_dates(self):
        for act in self:
            # ---------------------
            # Calcul DATA ÎNCEPUT
            # ---------------------
            start_base = None

            if act.start_source_type == 'project':
                if act.start_project_ref == 'depunere':
                    start_base = act.project_id.data_depunere
                elif act.start_project_ref == 'semnare':
                    start_base = act.project_id.data_semnare
                elif act.start_project_ref == 'finalizare':
                    start_base = act.project_id.data_finalizare
            elif act.start_source_type == 'activity' and act.start_activity_id:
                if act.start_activity_ref_type == 'start':
                    start_base = act.start_activity_id.date_start
                else:
                    start_base = act.start_activity_id.date_end

            if start_base:
                act.date_start = start_base + timedelta(days=(act.start_offset_days or 0))
            else:
                act.date_start = False

            # ---------------------
            # Calcul DATA SFÂRȘIT
            # ---------------------
            end_base = None

            if act.end_source_type == 'project':
                if act.end_project_ref == 'depunere':
                    end_base = act.project_id.data_depunere
                elif act.end_project_ref == 'semnare':
                    end_base = act.project_id.data_semnare
                elif act.end_project_ref == 'finalizare':
                    end_base = act.project_id.data_finalizare
            elif act.end_source_type == 'activity' and act.end_activity_id:
                if act.end_activity_ref_type == 'start':
                    end_base = act.end_activity_id.date_start
                else:
                    end_base = act.end_activity_id.date_end

            if end_base:
                act.date_end = end_base + timedelta(days=(act.end_offset_days or 0))
            else:
                act.date_end = False


class ProjectActivityTemplate(models.Model):
    _name = 'project.activity.template'
    _description = 'Șablon activitate proiect'
    _order = 'sequence, id'

    name = fields.Char(string='Denumire activitate', required=True)
    code = fields.Char(string='Cod activitate')
    sequence = fields.Integer(string='Ordine', default=10)

    phase = fields.Selection(
        [
            ('pre', 'Înainte de semnare'),
            ('post', 'După semnare'),
        ],
        string='Fază proiect',
        default='post',
        required=True,
    )

    # ------------------------------
    # CONFIGURARE DATA DE ÎNCEPUT (MODEL)
    # ------------------------------
    start_source_type = fields.Selection(
        [
            ('project', 'Dată proiect'),
            ('activity', 'Altă activitate din șablon'),
        ],
        string="Sursă dată început",
        default='project',
        required=True,
    )

    start_project_ref = fields.Selection(
        [
            ('depunere', 'Data depunerii'),
            ('semnare', 'Data semnării'),
            ('finalizare', 'Data finalizării'),
        ],
        string="Dată proiect pentru început",
        default='semnare',
    )

    start_template_id = fields.Many2one(
        'project.activity.template',
        string="Șablon referință (început)",
        domain="[('id', '!=', id)]",
        help="Șablonul de activitate de la care se va prelua data (start/end) pentru început."
    )

    start_activity_ref_type = fields.Selection(
        [
            ('start', 'Data de început a activității'),
            ('end', 'Data de sfârșit a activității'),
        ],
        string="Tip dată referință (început)",
        default='start',
    )

    start_offset_days = fields.Integer(
        string='Offset început (zile)',
        help='Număr de zile (+/-) față de data de referință pentru început.'
    )

    # ------------------------------
    # CONFIGURARE DATA DE SFÂRȘIT (MODEL)
    # ------------------------------
    end_source_type = fields.Selection(
        [
            ('project', 'Dată proiect'),
            ('activity', 'Altă activitate din șablon'),
        ],
        string="Sursă dată sfârșit",
        default='project',
        required=True,
    )

    end_project_ref = fields.Selection(
        [
            ('depunere', 'Data depunerii'),
            ('semnare', 'Data semnării'),
            ('finalizare', 'Data finalizării'),
        ],
        string="Dată proiect pentru sfârșit",
        default='semnare',
    )

    end_template_id = fields.Many2one(
        'project.activity.template',
        string="Șablon referință (sfârșit)",
        domain="[('id', '!=', id)]",
        help="Șablonul de activitate de la care se va prelua data (start/end) pentru sfârșit."
    )

    end_activity_ref_type = fields.Selection(
        [
            ('start', 'Data de început a activității'),
            ('end', 'Data de sfârșit a activității'),
        ],
        string="Tip dată referință (sfârșit)",
        default='end',
    )

    end_offset_days = fields.Integer(
        string='Offset sfârșit (zile)',
        help='Număr de zile (+/-) față de data de referință pentru sfârșit.'
    )

    # ------------------------------
    # GENERARE SET STANDARD DE ȘABLOANE CU DEPENDENȚE
    # ------------------------------
    def action_generate_default_templates(self):
        """Generează un set standard de șabloane de activități, CU dependențe între ele.

        Se rulează o singură dată, la început. Dacă există deja
        șabloane, nu mai creează nimic și afișează un mesaj.
        """
        Template = self.env['project.activity.template']

        # Dacă există deja șabloane, nu mai facem nimic
        existing = Template.search([], limit=1)
        if existing:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Șabloane activități',
                    'message': (
                        "Există deja șabloane de activități definite.\n"
                        "Dacă vrei să regenerezi setul standard, șterge mai întâi "
                        "șabloanele existente."
                    ),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # 1) CREĂM ȘABLOANELE DE BAZĂ (fără legături între ele)
        base_templates = [
            # ----------------- Fază PRE – înainte de semnare -----------------
            {
                'sequence': 10,
                'phase': 'pre',
                'code': 'PRE1',
                'name': 'Analiză oportunitate și eligibilitate',
                'start_source_type': 'project',
                'start_project_ref': 'depunere',
                'start_offset_days': -45,
                'end_source_type': 'project',
                'end_project_ref': 'depunere',
                'end_offset_days': -30,
            },
            {
                'sequence': 20,
                'phase': 'pre',
                'code': 'PRE2',
                'name': 'Pregătire documentație proiect',
                'start_source_type': 'project',
                'start_project_ref': 'depunere',
                'start_offset_days': -30,
                'end_source_type': 'project',
                'end_project_ref': 'depunere',
                'end_offset_days': -1,
            },
            {
                'sequence': 30,
                'phase': 'pre',
                'code': 'PRE3',
                'name': 'Depunere cerere de finanțare',
                'start_source_type': 'project',
                'start_project_ref': 'depunere',
                'start_offset_days': 0,
                'end_source_type': 'project',
                'end_project_ref': 'depunere',
                'end_offset_days': 0,
            },

            # ----------------- Fază POST – după semnare -----------------
            {
                'sequence': 40,
                'phase': 'post',
                'code': 'POST1',
                'name': 'Semnare contract de finanțare',
                'start_source_type': 'project',
                'start_project_ref': 'semnare',
                'start_offset_days': 0,
                'end_source_type': 'project',
                'end_project_ref': 'semnare',
                'end_offset_days': 0,
            },
            {
                'sequence': 50,
                'phase': 'post',
                'code': 'POST2',
                'name': 'Organizare proceduri de achiziție',
                'start_source_type': 'project',   # va fi suprascris mai jos
                'start_project_ref': 'semnare',
                'start_offset_days': 1,
                'end_source_type': 'project',
                'end_project_ref': 'semnare',
                'end_offset_days': 90,
            },
            {
                'sequence': 60,
                'phase': 'post',
                'code': 'POST3',
                'name': 'Execuție lucrări / implementare activități',
                'start_source_type': 'project',   # va fi suprascris mai jos
                'start_project_ref': 'semnare',
                'start_offset_days': 91,
                'end_source_type': 'project',
                'end_project_ref': 'finalizare',
                'end_offset_days': 0,
            },
            {
                'sequence': 70,
                'phase': 'post',
                'code': 'POST4',
                'name': 'Raportare finală și închiderea proiectului',
                'start_source_type': 'project',   # va fi suprascris mai jos
                'start_project_ref': 'finalizare',
                'start_offset_days': 0,
                'end_source_type': 'project',
                'end_project_ref': 'finalizare',
                'end_offset_days': 30,
            },
            {
                'sequence': 80,
                'phase': 'post',
                'code': 'POST5',
                'name': 'Monitorizare post-implementare',
                'start_source_type': 'project',
                'start_project_ref': 'finalizare',
                'start_offset_days': 1,
                'end_source_type': 'project',
                'end_project_ref': 'finalizare',
                'end_offset_days': 365,
            },
        ]

        code_to_tmpl = {}

        for vals in base_templates:
            rec = Template.create(vals)
            code_to_tmpl[rec.code] = rec

        # 2) ADAUGĂM LEGĂTURILE (dependențe) ÎNTRE ȘABLOANE
        #    - POST2 începe din sfârșitul lui POST1
        #    - POST3 începe din sfârșitul lui POST2
        #    - POST4 începe din sfârșitul lui POST3
        relations = [
            {
                'code': 'POST2',
                'start_source_type': 'activity',
                'start_template_code': 'POST1',
                'start_activity_ref_type': 'end',
            },
            {
                'code': 'POST3',
                'start_source_type': 'activity',
                'start_template_code': 'POST2',
                'start_activity_ref_type': 'end',
            },
            {
                'code': 'POST4',
                'start_source_type': 'activity',
                'start_template_code': 'POST3',
                'start_activity_ref_type': 'end',
            },
        ]

        for rel in relations:
            tmpl = code_to_tmpl.get(rel['code'])
            ref_tmpl = code_to_tmpl.get(rel['start_template_code'])
            if tmpl and ref_tmpl:
                tmpl.write({
                    'start_source_type': rel['start_source_type'],
                    'start_template_id': ref_tmpl.id,
                    'start_activity_ref_type': rel['start_activity_ref_type'],
                })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Șabloane activități',
                'message': (
                    "Setul standard de șabloane (cu dependențe PRE/POST) a fost generat.\n"
                    "La proiectele noi, activitățile vor fi create automat după aceste legături."
                ),
                'type': 'success',
                'sticky': False,
            }
        }
