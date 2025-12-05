from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ProjectBudget(models.Model):
    _name = 'project.budget'
    _description = 'Linie deviz proiect'

    # ------------------------------
    # Constrângeri de integritate
    # ------------------------------
    _sql_constraints = [
        (
            'unique_nr_crt_per_project',
            'unique(project_id, nr_crt)',
            'Numărul de ordine (Nr. crt) trebuie să fie unic în cadrul aceluiași proiect.'
        ),
    ]

    # ------------------------------
    # Legătura cu proiectul (părinte)
    # ------------------------------
    project_id = fields.Many2one(
        'project.funding',
        string="Proiect",
        required=True,
        ondelete="restrict",   # nu permitem ștergerea proiectului cât timp are linii
        index=True,
    )

    # ------------------------------
    # Identificatori HG 907
    # ------------------------------
    chapter = fields.Char(string="Capitol")
    subchapter = fields.Char(string="Subcapitol")

    nr_crt = fields.Char(
        string="Nr. crt",
        compute="_compute_nr_crt",
        store=True,
        readonly=True,
        help="Identificator unic de linie, derivat din Capitol și Subcapitol (ex. 1.1.1).",
    )

    name = fields.Char(string="Denumire capitol / subcapitol")

    # ------------------------------
    # Cheltuieli eligibile / neeligibile
    # ------------------------------
    chelt_elig_baza = fields.Float(string="Chelt. eligibile - Bază")
    chelt_elig_tva = fields.Float(string="Chelt. eligibile - TVA eligibilă")
    total_eligibil = fields.Float(
        string="TOTAL ELIGIBIL",
        compute="_compute_totals",
        store=True,
    )

    chelt_neelig_baza = fields.Float(string="Chelt. neeligibile - Bază")
    chelt_neelig_tva = fields.Float(string="Chelt. neeligibile - TVA ne-eligibilă")
    total_neeligibil = fields.Float(
        string="TOTAL NEELIGIBIL",
        compute="_compute_totals",
        store=True,
    )

    # Totaluri agregate
    total_baza = fields.Float(
        string="TOTAL Bază",
        compute="_compute_totals",
        store=True,
    )
    total_tva = fields.Float(
        string="TOTAL TVA",
        compute="_compute_totals",
        store=True,
    )
    total = fields.Float(
        string="TOTAL",
        compute="_compute_totals",
        store=True,
    )

    # Alte informații
    tip_cheltuiala = fields.Selection(
        [
            ('Directa', 'Directa'),
            ('Indirecta', 'Indirecta'),
        ],
        string="Tip cheltuială",
    )

    mysmis = fields.Selection(
        [
            ('Active C', 'Active C'),
            ('Active N', 'Active N'),
            ('Alte Ch.', 'Alte Ch.'),
            ('Lucrari', 'Lucrari'),
            ('Marja', 'Marja'),
            ('Rezerva', 'Rezerva'),
            ('Servicii', 'Servicii'),
            ('Taxe', 'Taxe'),
            ('Echipam.', 'Echipam.'),
        ],
        string="MySMIS",
    )

    total_chelt_eligibile_neramb = fields.Float(
        string="Total chelt. eligibile (nerambursabile)"
    )
    total_chelt_eligibile_aport = fields.Float(
        string="Total chelt. eligibile (aport)"
    )

    # ------------------------------
    # Compute Nr. crt (HG 907 style)
    # ------------------------------
    @api.depends('chapter', 'subchapter')
    def _compute_nr_crt(self):
        """
        Generează Nr. crt ca <Capitol>.<Subcapitol>.

        Exemplu:
          Capitol = '1'
          Subcapitol = '1.1'
          => Nr. crt = '1.1.1'
        """
        for rec in self:
            chapter = (rec.chapter or '').strip()
            subchapter = (rec.subchapter or '').strip()
            parts = []
            if chapter:
                parts.append(chapter)
            if subchapter:
                parts.append(subchapter)
            rec.nr_crt = ".".join(parts) if parts else False

    # ------------------------------
    # Compute totaluri
    # ------------------------------
    @api.depends(
        'chelt_elig_baza',
        'chelt_elig_tva',
        'chelt_neelig_baza',
        'chelt_neelig_tva',
    )
    def _compute_totals(self):
        for line in self:
            ce_baza = line.chelt_elig_baza or 0.0
            ce_tva = line.chelt_elig_tva or 0.0
            cne_baza = line.chelt_neelig_baza or 0.0
            cne_tva = line.chelt_neelig_tva or 0.0

            # total eligibil = baza + tva eligibilă
            line.total_eligibil = ce_baza + ce_tva

            # total neeligibil = baza + tva neeligibilă
            line.total_neeligibil = cne_baza + cne_tva

            # total baza = eligibilă + neeligibilă
            line.total_baza = ce_baza + cne_baza

            # total tva = eligibilă + neeligibilă
            line.total_tva = ce_tva + cne_tva

            # total general = baza + tva
            line.total = line.total_baza + line.total_tva

    # ------------------------------
    # Constrângere Python: nr_crt unic pe proiect
    # ------------------------------
    @api.constrains('nr_crt', 'project_id')
    def _check_unique_nr_crt(self):
        for rec in self:
            # dacă nu e setat încă nr_crt, nu verificăm
            if not rec.nr_crt or not rec.project_id:
                continue
            domain = [
                ('project_id', '=', rec.project_id.id),
                ('nr_crt', '=', rec.nr_crt),
                ('id', '!=', rec.id),
            ]
            if self.search_count(domain):
                raise ValidationError(
                    "Numărul de ordine (Nr. crt = %s) trebuie să fie unic în cadrul proiectului %s."
                    % (rec.nr_crt, rec.project_id.display_name)
                )

    # ------------------------------
    # Afișare nume linie în many2one / referințe
    # ------------------------------
    def name_get(self):
        result = []
        for rec in self:
            label_parts = []
            if rec.nr_crt:
                label_parts.append(rec.nr_crt)
            elif rec.chapter:
                label_parts.append(str(rec.chapter))
            if rec.subchapter:
                label_parts.append(str(rec.subchapter))
            if rec.name:
                label_parts.append(rec.name)
            label = " - ".join(label_parts) if label_parts else f"Linie deviz {rec.id}"
            result.append((rec.id, label))
        return result
