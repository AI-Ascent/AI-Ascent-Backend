from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from pgvector.django import VectorField 
from django.contrib.postgres.fields import ArrayField
from db.models.embeddings import embeddings
import numpy as np

class APIUserManager(UserManager):
    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if password is None:
            raise ValueError("Superuser must have a password.")
        return self._create_user(email, email, password, **extra_fields)


class APIUser(AbstractUser):
    email = models.EmailField(unique=True)
    job_title = models.CharField("Job Title of the employee", null=True)
    specialization = models.CharField("Specialization of the employee", blank=True, null=True)
    job_level = models.IntegerField("The job level of the person", default=1)

    feedbacks = ArrayField(models.CharField(max_length=1000), default=list)

    strengths = ArrayField(models.TextField(), default=list)
    improvements = ArrayField(models.TextField(), default=list)

    strengths_vector = VectorField(dimensions=384, null=True)

    onboard_supp_hr_query = models.CharField("Supplementary query by the HR for the employee", blank=True, null=True)
    onboard_finalized = models.BooleanField("If the employee's onboard items have been finalized by the employee", blank=True, null=True)
    onboard_json = models.JSONField("The customized onboard items for this employee", blank=True, null=True) # Will have checklist, resources, explanation.
    onboard_completed_checklist_items = ArrayField(models.TextField(), default=list)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = APIUserManager()

    def save(self, *args, **kwargs):
        if self.strengths:
            # Batch embed each strength to save time
            vecs = embeddings.embed_documents(self.strengths)
            if vecs:
                mat = np.array(vecs, dtype=np.float32)
                centroid = mat.mean(axis=0)
                self.strengths_vector = centroid.tolist()
        super().save(*args, **kwargs)
