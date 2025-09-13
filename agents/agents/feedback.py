import os
import json
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from db.models.embeddings import sentiment_analysis
from agents.agents.safety import filter_feedback_for_bias
from django.core.cache import cache

load_dotenv()


FEEDBACK_MODEL = os.getenv("FEEDBACK_MODEL")
FEEDBACK_LLM = None
INSIGHTS_LLM = None

INSIGHTS_PROMPT = "Based on the following rough raw strengths and improvements, generate actionable insights for\
    strengths, improvements, and growth tips. Fill the structured fields accordingly."


def get_feedback_llm():
    """
    This returns the feedback agent if initialized, otherwise initializes and returns that.

    03:07 01/09/2025
    """

    global FEEDBACK_LLM
    if not FEEDBACK_LLM:
        FEEDBACK_LLM = init_chat_model(model=FEEDBACK_MODEL, temperature=0.0)

    return FEEDBACK_LLM


def classify_feedback(feedbacks: list):
    cache_key = f"classify_feedback_{hash(tuple(feedbacks))}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    cleaned_feedbacks = filter_feedback_for_bias(feedbacks)["safe_feedback"]
    classified = {"strengths": [], "improvements": []}

    for text in cleaned_feedbacks:
        result = sentiment_analysis(text)
        data = result[0]

        if data["label"] == "positive":
            classified["strengths"].append(text)
        else:
            classified["improvements"].append(text)

    cache.set(cache_key, classified, timeout=172800)  # Cache for 1 hour
    return classified


class FeedbackInsights(BaseModel):
    strengths_insights: list[str] = Field(
        description="Actionable insights based on strengths"
    )
    improvements_insights: list[str] = Field(
        description="Actionable insights based on improvements"
    )
    growth_tips: list[str] = Field(
        description="Helpful growth tips derived from the feedback"
    )


def get_structured_insights_llm():
    """
    This returns the insights LLM with structured output if initialized, otherwise initializes and returns that.
    """
    global INSIGHTS_LLM
    if not INSIGHTS_LLM:
        INSIGHTS_LLM = get_feedback_llm().with_structured_output(FeedbackInsights)
    return INSIGHTS_LLM


def generate_insights(classified: dict) -> dict:
    cache_key = f"generate_insights_{hash(json.dumps(classified, sort_keys=True))}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    content = f"Strengths: {classified['strengths']}\nImprovements: {classified['improvements']}"
    messages = [
        SystemMessage(content=INSIGHTS_PROMPT),
        HumanMessage(content=content),
    ]
    insights_llm = get_structured_insights_llm()
    result = insights_llm.invoke(messages)
    result_dump = result.model_dump()
    cache.set(cache_key, result_dump, timeout=3600)
    return result_dump


def summarise_feedback_points(feedbacks: list):
    pipe = RunnableLambda(classify_feedback) | RunnableLambda(generate_insights)
    return pipe.invoke(feedbacks)
