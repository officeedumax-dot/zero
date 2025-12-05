# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import timedelta


class ProjectAcquisition(models.Model):
    _name = 'project.acquisition'
    _description = 'Achiziție proiect'
    _order = 'sequence, id'

    name = fields.Char(string='Denumire achiziție', required=True)
    code = fields.Char(string='Cod achiziție')
    phase = fields.Selection(
        [
            ('before', 'Înainte de semnarea contractului'),
            ('after', 'După semnarea contractului'),
        ],
        string='Fază',
        required=True,
        default='after',
    )
    sequence = fields.Integer(string='Ordine', default=10)

    project_id = fields.Many2one(
        'project.funding',
        string='Proiect',
        required=True,
        ondelete='cascade',
    )

    state = fields.Selection(
        [
            ('draft', 'Planificată'),
            ('in_progress', 'În derulare'),
            ('done', 'Finalizată'),
            ('cancelled', 'Anulată'),
        ],
        string='Stare',
        default='draft',
        required=True,
    )

    description = fields.Text(string='Descriere')

    # Date calculate automat pe baza regulilor de planificare
    date_start = fields.Date(
        string='Data început',
        compute='_compute_dates',
        store=True,
    )
    date_end = fields.Date(
        string='Data sfârșit',
        compute='_compute_dates',
        store=True,
    )

    # REGULI PENTRU DATA DE ÎNCEPUT
    start_source_type = fields.Selection(
        [
            ('project', 'Dată din proiect'),
            ('activity', 'Activitate proiect'),
        ],
        string='Tip sursă dată început',
        default='project',
        required=True,
    )

    start_project_ref = fields.Selection(
        [
            ('depunere', 'Data depunerii proiectului'),
            ('contractare', 'Data semnării contractului'),
            ('finalizare', 'Data finalizării proiectului'),
        ],
        string='Referință proiect pentru început',
        default='contractare',
    )

    # referință la ACTIVITATE, nu la altă achiziție
    start_activity_id = fields.Many2one(
        'project.activity',
        string='Activitate de referință (început)',
    )

    start_activity_ref_type = fields.Selection(
        [
            ('start', 'Data de început'),
            ('end', 'Data de sfârșit'),
        ],
        string='Tip dată de referință (început)',
        default='end',
        required=True,
    )

    start_offset_days = fields.Integer(
        string='Decalaj zile (început)',
        default=0,
        help='Număr de zile (+/-) față de data de referință pentru început.',
    )

    # REGULI PENTRU DATA DE SFÂRȘIT
    end_source_type = fields.Selection(
        [
            ('project', 'Dată din proiect'),
            ('activity', 'Activitate proiect'),
        ],
        string='Tip sursă dată sfârșit',
        default='project',
        required=True,
    )

    end_project_ref = fields.Selection(
        [
            ('depunere', 'Data depunerii proiectului'),
            ('contractare', 'Data semnării contractului'),
            ('finalizare', 'Data finalizării proiectului'),
        ],
        string='Referință proiect pentru sfârșit',
        default='finalizare',
    )

    end_activity_id = fields.Many2one(
        'project.activity',
        string='Activitate de referință (sfârșit)',
    )

    end_activity_ref_type = fields.Selection(
        [
            ('start', 'Data de început'),
            ('end', 'Data de sfârșit'),
        ],
        string='Tip dată de referință (sfârșit)',
        default='end',
        required=True,
    )

    end_offset_days = fields.Integer(
        string='Decalaj zile (sfârșit)',
        default=0,
        help='Număr de zile (+/-) față de data de referință pentru sfârșit.',
    )

    # Dependențe între achiziții (ex: Documentație -> SEAP -> Contract)
    dependency_ids = fields.Many2many(
        'project.acquisition',
        'project_acquisition_dependency_rel',
        'acquisition_id',
        'dependency_id',
        string='Dependențe',
    )

    @api.depends(
        'start_source_type', 'start_project_ref',
        'start_activity_id.date_start', 'start_activity_id.date_end',
        'start_activity_ref_type', 'start_offset_days',
        'end_source_type', 'end_project_ref',
        'end_activity_id.date_start', 'end_activity_id.date_end',
        'end_activity_ref_type', 'end_offset_days',
        'project_id.data_depunere', 'project_id.data_semnare', 'project_id.data_finalizare',
    )
    def _compute_dates(self):
        """Calculează datele de început și sfârșit pe baza regulilor definite."""
        for rec in self:
            rec.date_start = rec._compute_single_date(
                source_type=rec.start_source_type,
                project_ref=rec.start_project_ref,
                other_activity=rec.start_activity_id,
                other_ref_type=rec.start_activity_ref_type,
                offset_days=rec.start_offset_days,
            )
            rec.date_end = rec._compute_single_date(
                source_type=rec.end_source_type,
                project_ref=rec.end_project_ref,
                other_activity=rec.end_activity_id,
                other_ref_type=rec.end_activity_ref_type,
                offset_days=rec.end_offset_days,
            )

    def _compute_single_date(
        self,
        source_type,
        project_ref,
        other_activity,
        other_ref_type,
        offset_days,
    ):
        """Returnează o singură dată (start / end) pentru o regulă."""
        self.ensure_one()
        base_date = False
        project = self.project_id

        # sursă: date din proiect
        if source_type == 'project' and project:
            if project_ref == 'depunere':
                base_date = project.data_depunere
            elif project_ref == 'contractare':
                base_date = project.data_semnare
            elif project_ref == 'finalizare':
                base_date = project.data_finalizare

        # sursă: ACTIVITATE (nu altă achiziție)
        elif source_type == 'activity' and other_activity:
            base_date = (
                other_activity.date_start
                if other_ref_type == 'start'
                else other_activity.date_end
            )

        if base_date:
            return base_date + timedelta(days=offset_days or 0)

        return False


class ProjectAcquisitionTemplate(models.Model):
    _name = 'project.acquisition.template'
    _description = 'Șablon achiziție proiect'
    _order = 'sequence, id'

    name = fields.Char(string='Denumire șablon achiziție', required=True)
    code = fields.Char(string='Cod șablon')
    phase = fields.Selection(
        [
            ('before', 'Înainte de semnarea contractului'),
            ('after', 'După semnarea contractului'),
        ],
        string='Fază',
        required=True,
        default='after',
    )
    sequence = fields.Integer(string='Ordine', default=10)
    description = fields.Text(string='Descriere')

    # REGULI PENTRU DATA DE ÎNCEPUT (ȘABLON)
    # Păstrăm valorile ('project', 'template'), dar 'template' înseamnă *alt șablon de activitate*
    start_source_type = fields.Selection(
        [
            ('project', 'Dată din proiect'),
            ('template', 'Alt șablon de activitate'),
        ],
        string='Tip sursă dată început',
        default='project',
        required=True,
    )

    start_project_ref = fields.Selection(
        [
            ('depunere', 'Data depunerii proiectului'),
            ('contractare', 'Data semnării contractului'),
            ('finalizare', 'Data finalizării proiectului'),
        ],
        string='Referință proiect pentru început',
        default='contractare',
    )

    # Legăm șablonul de achiziție la ȘABLON DE ACTIVITATE
    start_template_id = fields.Many2one(
        'project.activity.template',
        string='Șablon activitate de referință (început)',
    )

    start_template_ref_type = fields.Selection(
        [
            ('start', 'Data de început'),
            ('end', 'Data de sfârșit'),
        ],
        string='Tip dată de referință (început)',
        default='end',
        required=True,
    )

    start_offset_days = fields.Integer(
        string='Decalaj zile (început)',
        default=0,
    )

    # REGULI PENTRU DATA DE SFÂRȘIT (ȘABLON)
    end_source_type = fields.Selection(
        [
            ('project', 'Dată din proiect'),
            ('template', 'Alt șablon de activitate'),
        ],
        string='Tip sursă dată sfârșit',
        default='project',
        required=True,
    )

    end_project_ref = fields.Selection(
        [
            ('depunere', 'Data depunerii proiectului'),
            ('contractare', 'Data semnării contractului'),
            ('finalizare', 'Data finalizării proiectului'),
        ],
        string='Referință proiect pentru sfârșit',
        default='finalizare',
    )

    end_template_id = fields.Many2one(
        'project.activity.template',
        string='Șablon activitate de referință (sfârșit)',
    )

    end_template_ref_type = fields.Selection(
        [
            ('start', 'Data de început'),
            ('end', 'Data de sfârșit'),
        ],
        string='Tip dată de referință (sfârșit)',
        default='end',
        required=True,
    )

    end_offset_days = fields.Integer(
        string='Decalaj zile (sfârșit)',
        default=0,
    )

    # Dependențe între șabloane de achiziții (le păstrăm, nu afectează logica de date)
    dependency_ids = fields.Many2many(
        'project.acquisition.template',
        'project_acquisition_template_dependency_rel',
        'template_id',
        'dependency_id',
        string='Dependențe',
    )

    def action_generate_default_acquisition_templates(self):
        """Opțional: generează un set standard de șabloane de achiziții."""
        for rec in self:
            pass  # momentan lăsăm gol; putem completa ulterior la nevoie

class ProjectFunding(models.Model):
    _inherit = 'project.funding'

    acquisition_ids = fields.One2many(
        comodel_name='project.acquisition',
        inverse_name='project_id',
        string='Achiziții proiect',
    )
