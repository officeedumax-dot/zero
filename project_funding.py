from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ProjectFunding(models.Model):
    _name = 'project.funding'
    _description = 'Proiect finantat'
    _rec_name = 'cod'  # Folosește codul ca nume afișat

    # ------------------------------
    # Informații beneficiar / client
    # ------------------------------
    beneficiar = fields.Char(string="Beneficiar")
    cui = fields.Char(string="CUI")

    # ------------------------------
    # Detalii proiect
    # ------------------------------
    denumire = fields.Char(string="Denumire proiect")
    cod = fields.Char(
        string="Cod proiect",  # SMIS / MySMIS / cod apel etc.
        required=True,
    )

    data_depunere = fields.Date(string="Data depunerii")
    data_semnare = fields.Date(string="Data semnării")
    data_finalizare = fields.Date(string="Data finalizării")

    curs_eur = fields.Float(string="Curs EUR")
    tva_eligibila = fields.Selection(
        [
            ('da', 'Da'),
            ('nu', 'Nu'),
        ],
        string="TVA eligibilă"
    )

    # ------------------------------
    # Indicatori financiari și fizici
    # ------------------------------
    aport_valoare = fields.Float(
        string="Valoare aport (lei)",
        help="Valoarea aportului beneficiarului în lei."
    )

    stadiu_financiar = fields.Float(
        string="Stadiu financiar (%)",
        help="Procentul de realizare financiară a proiectului (0-100)."
    )

    stadiu_fizic = fields.Float(
        string="Stadiu fizic (%)",
        help="Procentul de realizare fizică a proiectului (0-100), introdus manual."
    )

    data_monitorizare = fields.Date(
        string="Data monitorizare",
        help="Data finală a perioadei de monitorizare a proiectului."
    )

    status_proiect = fields.Selection(
        [
            ('in_lucru', 'In lucru'),
            ('contractat', 'Contractat'),
            ('monitorizare', 'Monitorizare'),
            ('inchis', 'Inchis'),
        ],
        string="Status proiect",
        default='in_lucru',
        help="Stadiul general al proiectului."
    )

    # ------------------------------
    # Devize (tab DEVIZ)
    # ------------------------------
    budget_line_ids = fields.One2many(
        'project.budget',
        'project_id',
        string="Linii deviz"
    )

    deviz_note = fields.Text(string="Note deviz")

    total_deviz_eligibil = fields.Float(
        string="Total deviz eligibil",
        compute="_compute_totals_deviz",
        store=True
    )
    total_deviz_neeligibil = fields.Float(
        string="Total deviz neeligibil",
        compute="_compute_totals_deviz",
        store=True
    )
    total_deviz_general = fields.Float(
        string="Total deviz general",
        compute="_compute_totals_deviz",
        store=True
    )

    @api.depends('budget_line_ids.total_eligibil', 'budget_line_ids.total_neeligibil')
    def _compute_totals_deviz(self):
        for project in self:
            elig = sum(project.budget_line_ids.mapped('total_eligibil'))
            neelig = sum(project.budget_line_ids.mapped('total_neeligibil'))
            project.total_deviz_eligibil = elig
            project.total_deviz_neeligibil = neelig
            project.total_deviz_general = elig + neelig

    # ------------------------------
    # Activități proiect
    # ------------------------------
    activity_ids = fields.One2many(
        'project.activity', 'project_id', string="Activități"
    )

    # ------------------------------
    # Achizitii proiect
    # ------------------------------
    acquisition_ids = fields.One2many(
        'project.acquisition', 'project_id', string="Achiziții"
    )

    def action_open_acquisitions(self):
        """Deschide lista de achiziții filtrată pe proiectul curent."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Achiziții proiect",
            "res_model": "project_acquisition",
            "view_mode": "list,form",   # în 19.0 se folosește 'list' în loc de 'tree'
            "domain": [("project_id", "=", self.id)],
            "context": {
                "default_project_id": self.id,
            },
            "target": "current",
        }

    # ------------------------------
    # Alte tab-uri (note simple deocamdată)
    # ------------------------------
    achizitii_note = fields.Text(string="Note achiziții")
    activitati_note = fields.Text(string="Note activități")
    rambursare_note = fields.Text(string="Note grafic rambursare")

    # ------------------------------
    # Afișarea numelui în Odoo (breadcrumb, many2one, titlu)
    # ------------------------------
    def name_get(self):
        return [(rec.id, rec.cod or f"Proiect {rec.id}") for rec in self]

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Permite căutarea directă după cod, beneficiar sau denumire proiect în many2one."""
        args = args or []
        domain = []
        if name:
            domain = ['|', '|',
                      ('cod', operator, name),
                      ('beneficiar', operator, name),
                      ('denumire', operator, name)]
        records = self.search(domain + args, limit=limit)
        return records.name_get()

    # ------------------------------
    # Repartizare aport pe linii de deviz
    # ------------------------------
    def action_distribute_aport(self):
        """
        Distribuie valoarea aportului proporțional cu totalul eligibil al devizului.

        - Dacă totalul eligibil = 0 -> NU modifică nimic, afișează mesaj și abandonează.
        - Dacă aport <= 0 -> NU modifică nimic, afișează mesaj și abandonează.
        - Dacă aport > total eligibil -> eroare (ValidationError), fără modificări.
        - Altfel:
            * coef = aport / total_elig
            * total_chelt_eligibile_aport  = total_eligibil_linie * coef (rotunjit la 2 zecimale)
            * total_chelt_eligibile_neramb = total_eligibil_linie - aport_linie (rotunjit la 2 zecimale)

        La final afișează un mesaj cu valoarea aportului și procentul aportului (4 zecimale).
        """
        self.ensure_one()
        project = self

        total_elig = project.total_deviz_eligibil or 0.0
        aport = project.aport_valoare or 0.0

        # 1) Total eligibil = 0 -> nu facem nimic, doar mesaj
        if total_elig == 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Repartizare aport',
                    'message': (
                        "Totalul cheltuielilor eligibile este 0.\n"
                        "Nu se poate calcula procentul de aport.\n"
                        "Operațiunea a fost anulată, câmpurile nu au fost actualizate."
                    ),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # 2) Aport 0 sau negativ -> nu are sens să distribuim
        if aport <= 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Repartizare aport',
                    'message': (
                        "Valoarea aportului este 0 sau negativă.\n"
                        "Introduceți o valoare de aport mai mare decât 0 pentru a o putea repartiza."
                    ),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # 3) Aport mai mare decât totalul eligibil -> nu permitem (mai sigur)
        if aport > total_elig:
            raise ValidationError(
                "Valoarea aportului (%.2f) nu poate depăși totalul cheltuielilor eligibile (%.2f)."
                % (aport, total_elig)
            )

        # 4) Calcul procent aport
        coef = aport / total_elig
        coef_display = round(coef, 4)

        # 5) Repartizăm pe linii
        for line in project.budget_line_ids:
            # recalculăm eligibilul direct din baza + TVA, ca să fim siguri
            elig_line = (line.chelt_elig_baza or 0.0) + (line.chelt_elig_tva or 0.0)

            aport_line = round(elig_line * coef, 2)
            neramb_line = round(elig_line - aport_line, 2)

            line.write({
                'total_chelt_eligibile_aport': aport_line,
                'total_chelt_eligibile_neramb': neramb_line,
            })

        # 6) Mesaj informativ către utilizator (non-blocant, fără rollback)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Repartizare aport',
                'message': (
                    "Repartizarea aportului a fost realizată.\n"
                    "Valoare aport: %.2f lei.\n"
                    "Total cheltuieli eligibile: %.2f lei.\n"
                    "Procent aport la cheltuieli eligibile: %.4f."
                ) % (aport, total_elig, coef_display),
                'type': 'success',
                'sticky': False,
            }
        }

    # ------------------------------
    # Generare automată ACTIVITĂȚI din șabloane
    # ------------------------------
    def _generate_activities_from_templates(self):
        """Generează activități pentru proiect pe baza șabloanelor definite.

        - Creează câte o activitate pentru fiecare șablon, păstrând sequence/phase/code/name.
        - Copiază regulile de planificare (sursă dată proiect/altă activitate).
        - În a doua trecere leagă activitățile între ele conform referințelor dintre șabloane.
        """
        Activity = self.env['project.activity']
        Template = self.env['project.activity.template']

        templates = Template.search([], order='sequence,id')
        if not templates:
            return

        for project in self:
            # dacă are deja activități, nu mai generăm (poți schimba logica dacă vrei)
            if project.activity_ids:
                continue

            template_to_activity = {}

            # 1) Creăm activitățile fără legături între ele
            for tmpl in templates:
                vals = {
                    'project_id': project.id,
                    'name': tmpl.name,
                    'code': tmpl.code,
                    'sequence': tmpl.sequence,
                    'phase': tmpl.phase,

                    'start_source_type': tmpl.start_source_type,
                    'start_project_ref': tmpl.start_project_ref,
                    'start_offset_days': tmpl.start_offset_days,
                    'start_activity_ref_type': tmpl.start_activity_ref_type,

                    'end_source_type': tmpl.end_source_type,
                    'end_project_ref': tmpl.end_project_ref,
                    'end_offset_days': tmpl.end_offset_days,
                    'end_activity_ref_type': tmpl.end_activity_ref_type,
                }
                activity = Activity.create(vals)
                template_to_activity[tmpl.id] = activity

            # 2) A doua trecere: legăm activitățile între ele (start/end) conform șabloanelor
            for tmpl in templates:
                activity = template_to_activity[tmpl.id]
                vals_update = {}

                if tmpl.start_source_type == 'activity' and getattr(tmpl, 'start_template_id', False):
                    ref_act = template_to_activity.get(tmpl.start_template_id.id)
                    if ref_act:
                        vals_update['start_activity_id'] = ref_act.id

                if tmpl.end_source_type == 'activity' and getattr(tmpl, 'end_template_id', False):
                    ref_act = template_to_activity.get(tmpl.end_template_id.id)
                    if ref_act:
                        vals_update['end_activity_id'] = ref_act.id

                if vals_update:
                    activity.write(vals_update)

    @api.model
    def create(self, vals):
        """
        La crearea unui proiect nou, generează automat activitățile din șabloane.
        """
        project = super(ProjectFunding, self).create(vals)
        project._generate_activities_from_templates()
        return project

    def action_generate_activities_from_templates(self):
        """
        Buton manual pentru a genera activitățile din șabloane
        pentru proiectele selectate care nu au încă activități.
        """
        self._generate_activities_from_templates()
        return True

    # -----------------------------
    # Generare ACHIZIȚII din șabloane (legate de ACTIVITĂȚI)
    # -----------------------------
    def _generate_acquisitions_from_templates(self):
        """
        Generează achiziții pentru fiecare proiect, pe baza
        șabloanelor din `project.acquisition.template`.

        - Șabloanele se leagă de ȘABLOANE DE ACTIVITĂȚI
          (start_template_id / end_template_id).
        - Când generăm achizițiile reale, căutăm activitatea
          corespunzătoare în `project.activity` (același cod / secvență / fază).
        - Achizițiile rezultate au regulile de dată legate de ACTIVITĂȚI
          (prin start_activity_id / end_activity_id), astfel încât
          modificarea activităților actualizează automat datele achizițiilor.
        """
        Acquisition = self.env["project.acquisition"]
        AcquisitionTemplate = self.env["project.acquisition.template"]

        templates = AcquisitionTemplate.search([], order="sequence,id")
        if not templates:
            return

        for project in self:
            # Dacă vrei să regenerezi complet achizițiile pentru proiect:
            if project.acquisition_ids:
                project.acquisition_ids.unlink()

            # helper: mapăm șablon de activitate -> activitate din proiect
            def _find_activity_for_template(act_tmpl):
                if not act_tmpl:
                    return False

                activities = project.activity_ids

                # 1) încercăm întâi după cod (dacă există)
                if act_tmpl.code:
                    candidates = activities.filtered(
                        lambda a: a.code == act_tmpl.code
                    )
                    if candidates:
                        return candidates[0]

                # 2) fallback: după sequence + phase
                candidates = activities
                if act_tmpl.sequence:
                    candidates = candidates.filtered(
                        lambda a: a.sequence == act_tmpl.sequence
                    )
                if act_tmpl.phase:
                    candidates = candidates.filtered(
                        lambda a: a.phase == act_tmpl.phase
                    )
                return candidates[0] if candidates else False

            template_to_acq = {}

            # PAS 1: creăm achizițiile pe baza șabloanelor
            for tmpl in templates:
                # --- început
                start_source_type = "project"
                start_project_ref = tmpl.start_project_ref
                start_activity_id = False
                start_activity_ref_type = "end"

                if tmpl.start_source_type == "project":
                    # legăm de data din proiect indicată de start_project_ref
                    start_source_type = "project"
                elif tmpl.start_source_type == "template":
                    # legăm de o ACTIVITATE din proiect, corespunzătoare
                    # șablonului de activitate
                    act = _find_activity_for_template(tmpl.start_template_id)
                    if act:
                        start_source_type = "activity"
                        start_activity_id = act.id
                        start_activity_ref_type = tmpl.start_template_ref_type
                    else:
                        # dacă nu găsim activitatea, rămânem pe proiect
                        start_source_type = "project"

                # --- sfârșit
                end_source_type = "project"
                end_project_ref = tmpl.end_project_ref
                end_activity_id = False
                end_activity_ref_type = "end"

                if tmpl.end_source_type == "project":
                    end_source_type = "project"
                elif tmpl.end_source_type == "template":
                    act_end = _find_activity_for_template(tmpl.end_template_id)
                    if act_end:
                        end_source_type = "activity"
                        end_activity_id = act_end.id
                        end_activity_ref_type = tmpl.end_template_ref_type
                    else:
                        end_source_type = "project"

                vals = {
                    "project_id": project.id,
                    "sequence": tmpl.sequence,
                    "phase": tmpl.phase,
                    "code": tmpl.code,
                    "name": tmpl.name,
                    "description": tmpl.description,
                    "state": "draft",

                    # reguli dată început (legate de ACTIVITĂȚI sau PROIECT)
                    "start_source_type": start_source_type,
                    "start_project_ref": start_project_ref,
                    "start_activity_id": start_activity_id,
                    "start_activity_ref_type": start_activity_ref_type,
                    "start_offset_days": tmpl.start_offset_days,

                    # reguli dată sfârșit
                    "end_source_type": end_source_type,
                    "end_project_ref": end_project_ref,
                    "end_activity_id": end_activity_id,
                    "end_activity_ref_type": end_activity_ref_type,
                    "end_offset_days": tmpl.end_offset_days,
                }

                acq = Acquisition.create(vals)
                template_to_acq[tmpl.id] = acq

            # PAS 2: mapăm dependențele dintre șabloane pe achizițiile nou create
            for tmpl in templates:
                new_acq = template_to_acq.get(tmpl.id)
                if not new_acq:
                    continue

                mapped_dep_ids = []
                for dep_tmpl in tmpl.dependency_ids:
                    mapped = template_to_acq.get(dep_tmpl.id)
                    if mapped:
                        mapped_dep_ids.append(mapped.id)

                if mapped_dep_ids:
                    new_acq.dependency_ids = [(6, 0, mapped_dep_ids)]

    def action_generate_acquisitions_from_templates(self):
        """Buton pe formularul de proiect: 'Generează achiziții din șablon'."""
        for project in self:
            project._generate_acquisitions_from_templates()
        return True

    # -----------------------------
    # BUTON: Setare achiziții (doar pentru proiectul curent)
    # -----------------------------
    def action_open_acquisitions(self):
        """Deschide lista de achiziții filtrată pe proiectul curent."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Achiziții proiect",
            "res_model": "project.acquisition",
            "view_mode": "list,form",
            "domain": [("project_id", "=", self.id)],
            "context": {
                "default_project_id": self.id,
            },
            "target": "current",
        }

    # ------------------------------
    # Integritate: nu permitem ștergerea proiectului cu copii
    # ------------------------------
    def unlink(self):
        for project in self:
            if project.budget_line_ids or project.activity_ids or project.acquisition_ids:
                raise ValidationError(
                    "Nu puteți șterge proiectul «%s» deoarece are linii de deviz, activități și/sau achiziții asociate.\n"
                    "Ștergeți mai întâi înregistrările asociate dacă este cu adevărat necesar."
                    % (project.cod or project.denumire or project.id)
                )
        return super(ProjectFunding, self).unlink()
