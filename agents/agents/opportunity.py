"""
Opportunity agent for skills improvement and mentorship matching.

Checks the users skill - strengths and improvements needed | Check the skill loom or cached info
1. Improve your own things that and to be improved and Use the other peoples strengths from the cached feedback (so stregnths and improvement vectors ig) only to see who we can ask for help. (1)

2. Uses the skills the user has (so use user input) to find more relevant roles in the company. (this is to keep talent within the company and not waste resources spent on this person) (Have multiple filters for the user to use)
i. Filters: Money, level, sort by particular skill, etc
Use the above skill profile and vector based cosine scoring to get / find similar skill to fnd roles with similar skills.

Model to store open roles in the company with the skills for it and other stuff needed.
"""

from typing import List, Dict
from django.db.models import Q
from pgvector.django import CosineDistance
from db.models.user import APIUser
from db.models.embeddings import embeddings


def find_mentors_for_improvements(user_email: str, top_k: int = 1) -> List[Dict]:
    """
    Find users whose strengths match with the current user's improvement areas using vector similarity.

    Args:
        user_email: email of the user seeking mentorship
        top_k: Number of top mentors to return

    Returns:
        List of dictionaries containing mentor information and similarity scores
    """

    current_user = APIUser.objects.get(email=user_email)

    improvements_texts = [
        imp
        for imp in (current_user.improvements or [])
        if isinstance(imp, str) and imp.strip()
    ]
    if not improvements_texts:
        return []

    improvement_vectors = [embeddings.embed_query(text) for text in improvements_texts]

    mentors: List[Dict] = []

    for idx, imp_vec in enumerate(improvement_vectors):
        imp_text = improvements_texts[idx] if idx < len(improvements_texts) else None
        # Find users whose strengths vectors are similar to this improvement vector
        potential_mentors = (
            APIUser.objects.filter(
                ~Q(email=user_email),  # Exclude the current user
                strengths_vector__isnull=False,  # Only users with strengths vectors
            )
            .annotate(similarity=CosineDistance("strengths_vector", imp_vec))
            .order_by("similarity")[:top_k]
        )

        for mentor in potential_mentors:
            mentors.append(
                {
                    "email": mentor.email,
                    "job_title": mentor.job_title,
                    "specialization": mentor.specialization,
                    "strengths": mentor.strengths,
                    "similarity_score": (
                        1 - mentor.similarity
                        if mentor.similarity is not None
                        else None
                    ),
                    "can_help_with": imp_text,
                }
            )

    return mentors
