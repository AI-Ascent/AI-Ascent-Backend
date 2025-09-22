from django.db import models
from datetime import date

class KPI(models.Model):
    year = models.IntegerField()
    month = models.IntegerField()
    
    completed_onboard_tasks = models.IntegerField("Amount of onboard tasks completed by the employees", default=0)
    assigned_onboard_tasks = models.IntegerField("Total number of onboard tasks assigned to the employees", default=0)
    
    class Meta:
        unique_together = [['year', 'month']]
    
    @classmethod
    def create_or_get_current_month(cls):
        today = date.today()
        kpi, created = cls.objects.get_or_create(
            year=today.year,
            month=today.month,
            defaults={}
        )
        return kpi
    

