from django.db import models
from django.contrib.postgres.fields import ArrayField
from pgvector.django import VectorField 
from db.models.embeddings import embeddings

class SkillCatalog(models.Model):
    title = models.CharField(max_length=256, verbose_name="Skill Title")
    tags = ArrayField(models.CharField(max_length=256), default=list)
    type = models.CharField(max_length=16, verbose_name="Resource Type")
    url = models.URLField(verbose_name="Resource URL")

    title_vector = VectorField(dimensions=384, null=True)
    tags_vector = VectorField(dimensions=384, null=True)
    type_vector = VectorField(dimensions=384, null=True)

    def save(self, *args, **kwargs):
        if self.title:
            self.title_vector = embeddings.embed_query(self.title)
        if self.tags:
            tags_str = " ".join(self.tags)  # Concatenate tags for embedding
            self.tags_vector = embeddings.embed_query(tags_str)
        if self.type:
            self.type_vector = embeddings.embed_query(self.type)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
