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

    feedbacks = ArrayField(models.CharField(max_length=1000), default=list)

    strengths = ArrayField(models.TextField(), default=list)
    improvements = ArrayField(models.TextField(), default=list)

    strengths_vector = VectorField(dimensions=384, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = APIUserManager()

    def save(self, *args, **kwargs):
        if self.strengths:
            # Batch embed each strength to save time
            vecs = embeddings.embed_documents(self.strengths)
            if vecs:
                mat = np.array(vecs, dtype=np.float32)
                # L2-normalize each row, mean-pool, then L2-normalize the centroid
                norms = np.linalg.norm(mat, axis=1, keepdims=True)
                # Avoid division by zero
                norms[norms == 0] = 1.0
                mat = mat / norms
                centroid = mat.mean(axis=0)
                c_norm = np.linalg.norm(centroid)
                if c_norm > 0:
                    centroid = centroid / c_norm
                self.strengths_vector = centroid.tolist()
        super().save(*args, **kwargs)
