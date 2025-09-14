from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate
from langchain_community.tools.tavily_search import TavilySearchResults
from db.models.skill import SkillCatalog
from db.models.user import APIUser
from db.models.embeddings import embeddings
from pgvector.django import CosineDistance
from agents.agents.feedback import classify_feedback
import json
from django.core.cache import cache
import os
from agents.agents.model_config import SKILL_MODEL
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
SKILL_LLM = None
SKILL_AGENT = None


SKILL_PROMPT = """You are a skill development assistant. Your goal is to help users find relevant learning resources and skills based on their query.

Use the skill catalog search tools (find_similar_skill_titles, find_similar_skill_types, find_skills_with_relevant_tags) to explore relevant skills and resources based on the user's query.

Use the tavily_search tool a maximum of twice. If the skill catalog has no relevant information or you need specific current data that isn't available internally.

When providing recommendations, consider any user feedback insights provided in the query to suggest skills that address their improvement areas and build upon their strengths.

Compile all gathered information into a json string (not actual json object but json string) format. The json string should have a 'skills' array, where each item has 'title', 'description', 'learning_outcomes', and a 'resources' array. Each resource should have 'title', 'url', and 'type'. Also include an 'explanation' string.

Do not invent any new resources or use placeholder/examples for resources (so do not give or use example.com or similar urls). If you need resources for something not in the skill catalog, use tavily_search tool and prioritize free ones.
Try to be as quick and concise and possible using the least amount of finding tool calls and iterations.
Focus on actionable, practical learning resources and current industry-relevant skills.
Use only the tools provided. Output json string directly in your final answer."""


def create_skill_llm():
    """
    This returns the skill llm if initialized, otherwise initializes and returns that.
    The LLM is configured for structured output based on the SkillResponse model.
    """
    global SKILL_LLM
    if not SKILL_LLM:
        # SKILL_LLM = init_chat_model(SKILL_MODEL)
        SKILL_LLM = ChatGroq(model=SKILL_MODEL.split(':')[-1], reasoning_effort='low')
    return SKILL_LLM


def vector_fuzzy_search(query: str, vector_field: str, threshold: float = 0.8) -> list:
    """
    Uniform helper for fuzzy vector search on SkillCatalog.
    Computes embedding for query and finds top 5 similar items using cosine similarity.
    """
    query_vector = embeddings.embed_query(query)
    similar_items = (
        SkillCatalog.objects.annotate(
            distance=CosineDistance(vector_field, query_vector)
        )
        .filter(distance__lt=threshold)
        .order_by("distance")[:5]
    )
    return similar_items


@tool
def find_similar_skill_titles(skill_title: str) -> str:
    """
    Find similar skill titles using vector fuzzy search.
    Input: A skill title or topic (e.g., 'Python programming', 'Data Science')
    """
    cache_key = f"find_similar_skill_titles_{skill_title}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    similar_skills = vector_fuzzy_search(skill_title, "title_vector")
    if not similar_skills:
        result = f"No similar skills found for '{skill_title}'"
    else:
        result = "\n".join(
            [
                f"{skill.title} - Type: {skill.type} - Tags: {', '.join(skill.tags[:3])} - URL: {skill.url} (Similarity: {1 - skill.distance:.2f})"
                for skill in similar_skills
            ]
        )
    cache.set(cache_key, result, timeout=172800)
    return result


@tool
def find_similar_skill_types(skill_type: str) -> str:
    """
    Find similar skill types/categories using vector fuzzy search.
    Input: A skill type or category (e.g., 'tutorial', 'course', 'documentation')
    """
    cache_key = f"find_similar_skill_types_{skill_type}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    similar_types = vector_fuzzy_search(skill_type, "type_vector")
    if not similar_types:
        result = f"No similar skill types found for '{skill_type}'"
    else:
        result = "\n".join(
            [
                f"{skill.title} - Type: {skill.type} - URL: {skill.url} (Similarity: {1 - skill.distance:.2f})"
                for skill in similar_types
            ]
        )
    cache.set(cache_key, result, timeout=172800)
    return result


@tool
def find_skills_with_relevant_tags(tags: str) -> str:
    """
    Find skills with relevant tags using vector fuzzy search.
    Input: Comma-separated tags (e.g., 'python, programming, beginner')
    """
    cache_key = f"find_skills_with_relevant_tags_{tags}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    tags_str = " ".join([tag.strip() for tag in tags.split(",")])
    relevant_skills = vector_fuzzy_search(tags_str, "tags_vector")
    if not relevant_skills:
        result = f"No skills found with relevant tags for '{tags}'"
    else:
        result = "\n".join(
            [
                f"{skill.title} - Tags: {', '.join(skill.tags)} - Type: {skill.type} - URL: {skill.url} (Similarity: {1 - skill.distance:.2f})"
                for skill in relevant_skills
            ]
        )
    cache.set(cache_key, result, timeout=172800)
    return result


@tool
def tavily_search(query: str) -> str:
    """
    Search online for additional skill development resources, courses, tutorials, or current information.
    Use this when the skill catalog doesn't have sufficient information.
    Input: Search query for online resources
    """
    cache_key = f"tavily_search_{query}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    if not TAVILY_API_KEY:
        result = "Tavily search not available - API key not configured"
    else:
        try:
            search_tool = TavilySearchResults(
                api_key=TAVILY_API_KEY, max_results=2, search_depth="basic"
            )
            results = search_tool.invoke({"query": query})

            if not results:
                result = f"No online results found for '{query}'"
            else:
                formatted_results = []
                for result_item in results:
                    formatted_results.append(
                        f"Title: {result_item.get('title', 'N/A')}\nURL: {result_item.get('url', 'N/A')}\nSummary: {result_item.get('content', 'N/A')}\n"
                    )

                result = "\n---\n".join(formatted_results)
        except Exception as e:
            result = f"Error searching online: {str(e)}"

    cache.set(cache_key, result, timeout=172800)
    return result


@tool(name_or_callable="json")
def json_tool(tool_input: str = "") -> str:
    """Guardrail: Call this tool for any json related functions need to be performed"""
    return tool_input


def create_skill_agent():
    """
    This returns the skill agent if initialized, otherwise initializes and returns that.
    """
    global SKILL_AGENT
    if not SKILL_AGENT:
        llm = create_skill_llm()
        tools = [
            find_similar_skill_titles,
            find_similar_skill_types,
            find_skills_with_relevant_tags,
            tavily_search,
            json_tool,     # guardrail
        ]
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SKILL_PROMPT),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}"),
            ]
        )
        agent = create_tool_calling_agent(llm, tools, prompt)
        SKILL_AGENT = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=8,
            early_stopping_method="force",  # Added to force stop on max iterations
            return_intermediate_steps=True,
        )
    return SKILL_AGENT


def run_skill_agent(query: str, email: str = None):
    """
    Runs the skill agent with the given query and email, returns the JSON response.
    If email is provided, automatically gets feedback insights for personalization.
    """
    cache_key = f"skill_agent_{email}_{query}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    agent = create_skill_agent()

    # If email is provided, enhance the query with feedback insights
    if email:
        user = APIUser.objects.get(email=email)
        if user.feedbacks:
            classified = classify_feedback(user.feedbacks)
            feedback_context = f"User feedback insights - Strengths: {', '.join(classified.get('strengths', []))}, Areas for Improvement: {', '.join(classified.get('improvements', []))}. "
            query = f"{feedback_context}{query}"

    result = agent.invoke({"input": query})

    output = result.get("output", "{}")

    # Check for early stopping due to max iterations
    if output == "Agent stopped due to max iterations.":
        intermediate_steps = result.get("intermediate_steps", [])
        if intermediate_steps:
            # Format intermediate steps into a string for summarization
            steps_text = "\n".join(
                [f"Step {i+1}: {step}" for i, step in enumerate(intermediate_steps)]
            )
            summarization_prompt = f"Based on the reasoning so far:\n{steps_text}\n\nCompile all gathered information into a JSON format. Do not invent any new resources or use placeholder/examples for resources (so do not give or use example.com or similar urls). The JSON object should have a 'skills' array, where each item has 'title', 'description', 'learning_outcomes', and a 'resources' array. Each resource should have 'title', 'url', and 'type'. Also include an 'explanation' string."

            # Use the LLM to generate a summary
            llm = create_skill_llm()
            summary_result = llm.invoke(
                [{"role": "user", "content": summarization_prompt}]
            )
            output = (
                summary_result.content
                if hasattr(summary_result, "content")
                else str(summary_result)
            )

    start = output.find("{")
    end = output.rfind("}")

    json_substring = output[start : end + 1]

    final_result = json.loads(json_substring)
    cache.set(cache_key, final_result, timeout=172800)
    return final_result
