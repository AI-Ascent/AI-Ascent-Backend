"""
Opportunity agent for skills improvement and mentorship matching.

Checks the users skill - strengths and improvements needed | Check the skill loom or cached info
1. Improve your own things that and to be improved and Use the other peoples strengths from the cached feedback (so stregnths and improvement vectors ig) only to see who we can ask for help. (1)

2. Uses the skills the user has (so use user input) to find more relevant roles in the company. (this is to keep talent within the company and not waste resources spent on this person) (Have multiple filters for the user to use)
i. Filters: Money, level, sort by particular skill, etc
Use the above skill profile (from the user and feedback cuz why not) and vector based cosine scoring to get / find similar skill to fnd roles with similar skills. You can also use the llm here for whateevr need.

Model to store open roles in the company with the skills for it and other stuff needed.
"""

from typing import List, Dict, Optional, Union
from django.db.models import Q
from pgvector.django import CosineDistance
from db.models.user import APIUser
from db.models.embeddings import embeddings
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from agents.agents.safety import check_prompt_safety
from agents.agents.model_config import OPPORTUNITY_MODEL

_OPPORTUNITY_LLM = None


def get_opportunity_llm():
    global _OPPORTUNITY_LLM
    if not _OPPORTUNITY_LLM:
        _OPPORTUNITY_LLM = init_chat_model(model=OPPORTUNITY_MODEL, temperature=0.2)
    return _OPPORTUNITY_LLM


class MentorSelection(BaseModel):
    best_candidate_index: Union[str, int, None] = Field(
        default=None,
        description="Zero-based index of the best-suited mentor in the provided candidates, or null if none is suitable",
    )
    reason: Optional[str] = Field(
        default=None, description="Short explanation. Address the final candidate as 'Mentor' and do not mention the candidate index here. If none suitable, explain why and what is missing."
    )
    no_good_mentor: Union[str, bool, None] = Field(
        default=False, description="True if no candidate is a strong enough match for the user's improvement areas"
    )


def _pick_best_mentor_with_llm(
    *,
    improvements: List[str],
    candidates: List[Dict],
) -> Optional[MentorSelection]:
    if not candidates:
        return None

    cand_lines = []
    for idx, c in enumerate(candidates):
        strengths = c.get('strengths') or []
        strengths_snip = ', '.join(strengths[:2])
        sim = c.get('similarity_score')
        cand_lines.append(
            f"[{idx}] job: {c.get('job_title')} | spec: {c.get('specialization')} | strengths: {strengths_snip} | sim: {round(sim, 3) if sim is not None else 'NA'}"
        )
    improvements_str = "; ".join([i for i in improvements if i])
    content = (
        f"Improvements: {improvements_str}\n"
        f"Candidates:\n" + "\n".join(cand_lines)
    )

    if not check_prompt_safety(content):
        return None

    llm = get_opportunity_llm().with_structured_output(MentorSelection)
    sys = SystemMessage(
        content=(
            "You are a careful mentor selector. From the shortlist, pick ONE mentor only if their strengths directly and specifically address the user's improvements. "
            "Return the zero-based index as best_candidate_index. If none is a decent fit, set no_good_mentor=True and leave best_candidate_index null. "
            "Be strict and aim for quality over quantity. Address the final candidate as 'Mentor' and do not mention the candidate index in the reason field."
        )
    )
    result = llm.invoke([sys, HumanMessage(content=content)])
    
    if result.best_candidate_index:
        if result.best_candidate_index.isdigit():
            result.best_candidate_index = int(result.best_candidate_index)
        else:
            result.best_candidate_index = None
    
    if result.no_good_mentor:
        if result.no_good_mentor == 'false':
            result.no_good_mentor = False
        else:
            result.no_good_mentor = True
        
    return result


def find_mentors_for_improvements(user_email: str, top_k: int = 3) -> List[Dict]:
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

    selected_per_improvement: List[Dict] = []

    for idx, imp_vec in enumerate(improvement_vectors):
        imp_text = improvements_texts[idx] if idx < len(improvements_texts) else None
        # Find users whose strengths vectors are similar to this improvement vector
        potential_qs = (
            APIUser.objects.filter(
                ~Q(email=user_email),  # Exclude the current user
                strengths_vector__isnull=False,  # Only users with strengths vectors
            )
            .annotate(similarity=CosineDistance("strengths_vector", imp_vec))
            .order_by("similarity")[:top_k]
        )

        candidates: List[Dict] = []
        for m in potential_qs:
            candidates.append(
                {
                    "email": m.email,
                    "job_title": m.job_title,
                    "specialization": m.specialization,
                    "strengths": m.strengths,
                    "similarity_score": 1 - m.similarity if m.similarity is not None else None,
                }
            )

        selection = _pick_best_mentor_with_llm(
            improvements=[imp_text] if imp_text else [], candidates=candidates
        )

        if not selection or selection.no_good_mentor or selection.best_candidate_index is None:
            selected_per_improvement.append(
                {
                    "can_help_with": imp_text,
                    "no_good_mentor": True,
                    "llm_reason": (selection.reason if selection and selection.reason else "No strong mentor found for this improvement"),
                }
            )
            continue

        # find the chosen mentor details by index
        idx_sel = selection.best_candidate_index
        chosen = candidates[idx_sel] if 0 <= idx_sel < len(candidates) else None
        if chosen:
            selected_per_improvement.append(
                {
                    "email": chosen.get("email"),
                    "job_title": chosen.get("job_title"),
                    "specialization": chosen.get("specialization"),
                    "strengths": chosen.get("strengths"),
                    "can_help_with": imp_text,
                    "llm_reason": selection.reason or "Chosen by LLM as the best match for this improvement",
                }
            )
        else:
            selected_per_improvement.append(
                {
                    "can_help_with": imp_text,
                    "no_good_mentor": True,
                    "llm_reason": "Invalid candidate index returned by the model",
                }
            )

    return selected_per_improvement
