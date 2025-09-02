from django.db import models
from django.contrib.postgres.fields import ArrayField
from pgvector.django import VectorField 
from db.models.embeddings import embeddings

class OnboardCatalog(models.Model):
    title = models.CharField(max_length=255, verbose_name="Job Title")
    specialization = models.CharField(max_length=255, verbose_name="Specialization within the Job Title", null=True, blank=True)
    tags = ArrayField(models.CharField(max_length=100), default=list)
    checklist = ArrayField(models.CharField(max_length=255), default=list)
    resources = ArrayField(models.CharField(max_length=255), default=list)

    title_vector = VectorField(dimensions=384, null=True)
    specialization_vector = VectorField(dimensions=384, null=True)
    tags_vector = VectorField(dimensions=384, null=True)

    def save(self, *args, **kwargs):
        if self.title:
            self.title_vector = embeddings.embed_query(self.title)
        if self.specialization:
            self.specialization_vector = embeddings.embed_query(self.specialization)
        if self.tags:
            tags_str = " ".join(self.tags)  # Concatenate tags for embedding
            self.tags_vector = embeddings.embed_query(tags_str)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
