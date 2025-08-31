import os
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


FEEDBACK_MODEL = os.getenv("FEEDBACK_MODEL")
FEEDBACK_LLM = None
STRUCT_LLM = None


def get_feedback_llm():
    """
    This returns the feedback agent if initialised, otherwise initialises and returns that.

    03:07 01/09/2025
    """

    global FEEDBACK_LLM
    if not FEEDBACK_LLM:
        FEEDBACK_LLM = init_chat_model(model=FEEDBACK_MODEL, temperature=0.0)

    return FEEDBACK_LLM


class ClassifiedFeedback(BaseModel):
    strengths: list[str] = Field(description="The strengths or this person / employee")
    improvements: list[str] = Field(
        description="The improvements this person / employee can work on"
    )


def get_classifier_llm():
    """
    This returns the struct classifier agent if initialised, otherwise initialises and returns that.

    03:38 01/09/2025
    """

    global STRUCT_LLM
    if not STRUCT_LLM:
        STRUCT_LLM = get_feedback_llm().with_structured_output(ClassifiedFeedback)

    return STRUCT_LLM


def classify_feedback(feedbacks: list):

    feedbacks_str = "|".join(feedbacks)

    messages = [
        SystemMessage(
            content="""Classify the feedback items into strengths and improvements. Be concise and bulleted.\
                Remove any feedback items that seem to be biased towards gender, race, ethnicity, age,\
                    religion, disability, nationality, or cultural; or is neutral."""
        ),
        HumanMessage(content=feedbacks_str),
    ]

    struct_class_llm = get_classifier_llm()
    result = struct_class_llm.invoke(messages)
    return result.model_dump()
