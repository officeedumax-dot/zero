from odoo import models, fields

class ProjectPurchase(models.Model):
    _name = 'project.purchase'
    _description = 'Achizitie proiect'

    project_id = fields.Many2one('project.funding', string="Proiect", ondelete="cascade")
    name = fields.Char(string="Denumire achiziție")
    furnizor = fields.Char(string="Furnizor")
    valoare = fields.Float(string="Valoare")
    data = fields.Date(string="Data")
