from django.db import models
from django.contrib.postgres.fields import ArrayField

class OnboardCatalog(models.Model):
    title = models.CharField(max_length=255, verbose_name="Job Title")
    specialization = models.CharField(max_length=255, verbose_name="Specialization within the Job Title", null=True, blank=True)
    tags = ArrayField(models.CharField(max_length=100), default=list)
    checklist = ArrayField(models.CharField(max_length=255), default=list)
    resources = ArrayField(models.CharField(max_length=255), default=list)

    def __str__(self):
        return self.title
