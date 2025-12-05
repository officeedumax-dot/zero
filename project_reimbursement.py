from odoo import models, fields

class ProjectReimbursement(models.Model):
    _name = 'project.reimbursement'
    _description = 'Rambursare proiect'

    project_id = fields.Many2one('project.funding', string="Proiect", ondelete="cascade")
    data = fields.Date(string="Data rambursării")
    suma = fields.Float(string="Sumă")
    status = fields.Selection([
        ('planificata', 'Planificată'),
        ('trimisa', 'Trimisă'),
        ('aprobata', 'Aprobată'),
        ('platita', 'Plătită'),
    ], string="Status", default='planificata')
