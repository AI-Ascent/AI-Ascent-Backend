from django.db import models
from django.contrib.postgres.fields import ArrayField
from pgvector.django import VectorField 
from db.models.embeddings import embeddings
from django.utils import timezone
from django.conf import settings

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


class InterestedSkill(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    set_at = models.DateTimeField(default=timezone.now)

    # Fields mirroring skill agent item shape
    skill_title = models.TextField()
    skill_description = models.TextField(blank=True)
    learning_outcomes = ArrayField(models.TextField(), default=list)
    resources = models.JSONField(default=list)

    title_vector = VectorField(dimensions=384, null=True)

    class Meta:
        pass

    def save(self, *args, **kwargs):
        if self.title_vector is None:
            self.title_vector = embeddings.embed_query(self.skill_title)
        super().save(*args, **kwargs)
