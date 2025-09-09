from langchain_huggingface import HuggingFaceEmbeddings
from transformers import pipeline

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Here because more huggingface stuff here - move to feedback if we decide not to usethis anywhere else
sentiment_analysis = pipeline(
    "sentiment-analysis",
    model="cardiffnlp/twitter-roberta-base-sentiment-latest"
)

# Init sentiment_analysis
print('Initializing sentiment analysis...')
sentiment_analysis('')
print('Initialized sentiment analysis successfully')