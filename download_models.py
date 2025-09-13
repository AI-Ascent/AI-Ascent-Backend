#!/usr/bin/env python3
"""
Script to download HuggingFace models during Docker build.
This ensures models are cached in the Docker image for faster startup.
"""

import os
import sys

# Set environment variables to avoid warnings
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'

try:
    from transformers import pipeline
    from langchain_huggingface import HuggingFaceEmbeddings

    print("Starting model downloads...")

    # Download embeddings model
    print("Downloading embeddings model: all-MiniLM-L6-v2")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    # Download sentiment analysis pipeline
    print("Downloading sentiment analysis pipeline: cardiffnlp/twitter-roberta-base-sentiment-latest")
    sentiment_pipeline = pipeline(
        "sentiment-analysis",
        model="cardiffnlp/twitter-roberta-base-sentiment-latest"
    )

    # Download hate speech detection pipeline
    print("Downloading hate speech detection pipeline: facebook/roberta-hate-speech-dynabench-r4-target")
    hate_pipeline = pipeline(
        "text-classification",
        model="facebook/roberta-hate-speech-dynabench-r4-target"
    )

    # Download prompt injection detection pipeline
    print("Downloading prompt injection detection pipeline: protectai/deberta-v3-base-prompt-injection-v2")
    injection_pipeline = pipeline(
        "text-classification",
        model="protectai/deberta-v3-base-prompt-injection-v2"
    )

    print("All models downloaded successfully!")

except Exception as e:
    print(f"Error downloading models: {e}")
    sys.exit(1)