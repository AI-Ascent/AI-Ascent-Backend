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

load_dotenv()

HATE_SPEECH_CLASSIFIER = None

def get_hate_speech_classifier():
    """
    Initialize and return the hate speech classifier model.
    Uses facebook/roberta-hate-speech-dynabench-r4-target for bias and discrimination detection.
    
    Returns:
        pipeline: Hugging Face pipeline for hate speech classification
    """
    global HATE_SPEECH_CLASSIFIER
    if not HATE_SPEECH_CLASSIFIER:
        login(token=os.getenv("HF_TOKEN"))
        HATE_SPEECH_CLASSIFIER = pipeline(
            "text-classification",
            model="facebook/roberta-hate-speech-dynabench-r4-target",
        )
    
    return HATE_SPEECH_CLASSIFIER

get_hate_speech_classifier() # Load model for inference so that it does'nt for the first actual request

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
                raise Exception(f"Unknown label in HATE_SPEECH_CLASSIFIER output: {result}")
    return {
        "safe_feedback": safe_feedback,
        "flagged_feedback": flagged_feedback
    }

