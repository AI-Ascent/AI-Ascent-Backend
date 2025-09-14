"""
Centralized model configuration for AI-Ascent agents.
"""

from dotenv import load_dotenv
import os

# Ensure .env is loaded if present so env vars can override defaults
load_dotenv()


# Coordinator agent model
CORDINATOR_MODEL: str = os.getenv("CORDINATOR_MODEL", "groq:openai/gpt-oss-120b")

# Feedback agent model
FEEDBACK_MODEL: str = os.getenv("FEEDBACK_MODEL", "groq:llama-3.1-8b-instant")

# Opportunity (mentorship) agent model
OPPORTUNITY_MODEL: str = os.getenv("OPPORTUNITY_MODEL", "groq:llama-3.1-8b-instant")

# Onboard agent model
ONBOARD_MODEL: str = os.getenv("ONBOARD_MODEL", "groq:qwen/qwen3-32b")

# Skill agent model
SKILL_MODEL: str = os.getenv("SKILL_MODEL", "groq:openai/gpt-oss-20b")
