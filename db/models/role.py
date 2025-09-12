from django.db import models
from django.contrib.postgres.fields import ArrayField
from pgvector.django import VectorField
from db.models.embeddings import embeddings
import numpy as np


class OpenRole(models.Model):
    """
    Represents an open role in the company. Stores vectors for semantic matching
    against a user's skills/job profile using cosine similarity.
    """

    # Core role info
    title = models.CharField(max_length=255)
    specialization = models.CharField(max_length=255, null=True, blank=True)
    skills = ArrayField(models.CharField(max_length=128), default=list, help_text="Key skills/tech stack for this role")
    description = models.TextField(null=True, blank=True)

    # Filters/metadata
    level = models.CharField(max_length=64, null=True, blank=True, help_text="e.g., Intern, Junior, Mid, Senior, Staff, Principal")
    salary_min = models.IntegerField(null=True, blank=True)
    salary_max = models.IntegerField(null=True, blank=True)

    # Vector fields for semantic search (all-MiniLM-L6-v2 dims = 384)
    title_vector = VectorField(dimensions=384, null=True)
    specialization_vector = VectorField(dimensions=384, null=True)
    skills_vector = VectorField(dimensions=384, null=True)
    description_vector = VectorField(dimensions=384, null=True)
    # optional aggregate vector for all text fields
    aggregate_vector = VectorField(dimensions=384, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Individual pieces
        if self.title:
            self.title_vector = embeddings.embed_query(self.title)
        if self.specialization:
            self.specialization_vector = embeddings.embed_query(self.specialization)
        if self.skills:
            # Sum + L2 normalization for potential stronger signal from repeated/related skills
            vecs = embeddings.embed_documents(self.skills)
            if vecs:
                mat = np.array(vecs, dtype=np.float32)
                # Optionally L2-normalize rows before summing; we'll just sum raw vectors, then L2
                summed = mat.sum(axis=0)
                s_norm = np.linalg.norm(summed)
                if s_norm > 0:
                    summed = summed / s_norm
                self.skills_vector = summed.tolist()

        # Aggregate over title, specialization, and a flattened skills string
        # Description vector
        if self.description:
            self.description_vector = embeddings.embed_query(self.description[:1000])  # limit tokens a bit

        # Aggregate by summing available vectors, then L2-normalize
        agg_parts = []
        if self.title_vector is not None:
            agg_parts.append(np.array(self.title_vector, dtype=np.float32))
        if self.specialization_vector is not None:
            agg_parts.append(np.array(self.specialization_vector, dtype=np.float32))
        if self.skills_vector is not None:
            agg_parts.append(np.array(self.skills_vector, dtype=np.float32))
        if self.description_vector is not None:
            agg_parts.append(np.array(self.description_vector, dtype=np.float32))
        if agg_parts:
            agg = np.sum(agg_parts, axis=0)
            a_norm = np.linalg.norm(agg)
            if a_norm > 0:
                agg = agg / a_norm
            self.aggregate_vector = agg.tolist()

        super().save(*args, **kwargs)

    def __str__(self):
        base = self.title or "Open Role"
        if self.specialization:
            base += f" - {self.specialization}"
        return base
