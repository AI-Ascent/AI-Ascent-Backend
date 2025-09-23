from django.db import models
from pgvector.django import VectorField
from db.models.embeddings import embeddings
from db.models.user import APIUser


class NegativeFeedback(models.Model):
    user = models.ForeignKey(APIUser, on_delete=models.CASCADE, related_name='negative_feedbacks')
    feedback_text = models.TextField()
    feedback_vector = VectorField(dimensions=384, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if self.feedback_vector is None and self.feedback_text:
            vec = embeddings.embed_query(self.feedback_text)
            self.feedback_vector = vec
        super().save(*args, **kwargs)