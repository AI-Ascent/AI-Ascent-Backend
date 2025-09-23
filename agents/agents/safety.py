"""
A. Rule based (used as a filter)
i. For feedback -> filter out bias and discrimination (facebook/roberta-hate-speech-dynabench-r4-target) # Using models other than just LLMS
ii. For places where user interacts with models -> check for prompt goodness and prevent prompt injection (meta-llama/Llama-Prompt-Guard-2-22M) # Using models other than just LLMS (login using hf token in .env)
iii. Redact personal user information from the prompt -> replace with placeholders | using regex for emails, phone numbers, ids | since it is being sent to an outside source for inference

B. Trusted data (we know is gonna be mostly safe - comes from the db except for feedback) - no need to check
"""

from typing import List, Dict
from transformers import pipeline
from dotenv import load_dotenv
from huggingface_hub import login
import os
import re
from db.models.kpi import KPI

load_dotenv()
login(token=os.getenv("HF_TOKEN"))

HATE_SPEECH_CLASSIFIER = None
PROMPT_GUARDER_CLASSIFIER = None


def get_hate_speech_classifier():
    """
    Initialize and return the hate speech classifier model.
    Uses facebook/roberta-hate-speech-dynabench-r4-target for bias and discrimination detection.

    Returns:
        pipeline: Hugging Face pipeline for hate speech classification
    """
    global HATE_SPEECH_CLASSIFIER
    if not HATE_SPEECH_CLASSIFIER:
        HATE_SPEECH_CLASSIFIER = pipeline(
            "text-classification",
            model="facebook/roberta-hate-speech-dynabench-r4-target",
        )

    return HATE_SPEECH_CLASSIFIER


def get_prompt_guarder_classifier():
    """
    Initialize and return the Prompt Injection and Malicious Guarder.
    Uses protectai/deberta-v3-base-prompt-injection-v2 for this.

    Returns:
        pipeline: Hugging Face pipeline for Prompt Injection classification
    """
    global PROMPT_GUARDER_CLASSIFIER
    if not PROMPT_GUARDER_CLASSIFIER:
        PROMPT_GUARDER_CLASSIFIER = pipeline(
            "text-classification", model="protectai/deberta-v3-base-prompt-injection-v2"
        )

    return PROMPT_GUARDER_CLASSIFIER


# Load model for inference so that it does'nt for the first actual request
get_hate_speech_classifier()
get_prompt_guarder_classifier()


def filter_feedback_for_bias(feedbacks: List[str]) -> Dict[str, List]:
    """
    Filter a list of feedback texts for bias and discrimination.

    Args:
        feedbacks (List[str]): List of feedback texts to filter

    Returns:
        Dict containing:
        - safe_feedback (List[str]): Feedback that passed the bias filter
        - flagged_feedback (List[str]): Feedback that was flagged for bias/discrimination
    """
    safe_feedback = []
    flagged_feedback = []

    results = HATE_SPEECH_CLASSIFIER(feedbacks)

    for idx, result in enumerate(results):
        match result["label"]:
            case "hate":
                flagged_feedback.append(feedbacks[idx])
            case "nothate":
                safe_feedback.append(feedbacks[idx])
            case _:
                raise Exception(
                    f"Unknown label in HATE_SPEECH_CLASSIFIER output: {result}"
                )
    return {"safe_feedback": safe_feedback, "flagged_feedback": flagged_feedback}


def check_prompt_safety(prompt: str) -> bool:
    """
    Checks a prompt for safety to give to an LLM. This is to prevent prompt injections and other malicious prompts to agents with tools.

    Args:
        prompt: a prompt in string format

    Returns:
        A boolean value of if the prompt is safe (True) or not (False)
    """

    result = get_prompt_guarder_classifier()(prompt)

    if result[0]["label"] == "INJECTION":
        kpi = KPI.create_or_get_current_month()
        kpi.prompt_injection_count += 1
        kpi.save()
        return False
    else:
        return True


def redact_pii(prompt: str) -> str:
    """
    Redacts Personal Identifiable Information (PII) from a given prompt string.
    Currently redacts emails and phone numbers.

    Args:
        prompt (str): The input string to redact.

    Returns:
        str: The prompt with PII replaced by placeholders.
    """
    # Regex for emails
    prompt, email_count = re.subn(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "[REDACTED_EMAIL]",
        prompt,
    )

    # Regex for phone numbers (handles various common formats)
    prompt, phone_count = re.subn(
        r"(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})", "[REDACTED_PHONE]", prompt
    )

    kpi = KPI.create_or_get_current_month()
    kpi.pii_redacted_count += email_count + phone_count
    kpi.save()

    return prompt