"""
WSGI config for AIAscentBackend project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AIAscentBackend.settings')

application = get_wsgi_application()

# Load heavy models once during app import so worker processes share memory via copy-on-write.
try:
	# Hugging Face text pipelines from safety module
	from agents.agents.safety import (
		get_hate_speech_classifier,
		get_prompt_guarder_classifier,
	)

	# Embeddings and sentiment analysis
	from db.models.embeddings import sentiment_analysis, embeddings

	# Initialize safety classifiers
	get_hate_speech_classifier()
	get_prompt_guarder_classifier()

except Exception as _warmup_err:
	pass
