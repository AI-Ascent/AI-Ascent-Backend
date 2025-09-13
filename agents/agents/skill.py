import os
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
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

load_dotenv()

SKILL_MODEL = os.getenv("SKILL_MODEL")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
SKILL_LLM = None
SKILL_AGENT = None


SKILL_PROMPT = """You are a skill development assistant. Your goal is to help users find relevant learning resources and skills based on their query.

Primarily use the skill catalog search tools (find_similar_skill_titles, find_similar_skill_types, find_skills_with_relevant_tags) to explore relevant skills and resources based on the user's query. At the end, with relevant skill titles found, use get_skill_details (multiple times if needed but atleast once) to retrieve the specific URL of that resource.

Only use the tavily_search tool sparingly if the skill catalog has no relevant information or you need very specific current data that isn't available internally. Avoid over-relying on external searches to keep recommendations focused on the catalog.

When providing recommendations, consider any user feedback insights provided in the query to suggest skills that address their improvement areas and build upon their strengths.

Compile all gathered information into a JSON format. The JSON object should have a 'skills' array, where each item has 'title', 'description', 'learning_outcomes', and a 'resources' array. Each resource should have 'title', 'url', and 'type'. Also include an 'explanation' string.

Do not invent any new resources or use placeholder/examples for resources (so no example.com or similar urls). If you need resources for something not in the skill catalog, use tavily_search tool and prioritize free ones.
Try to be as quick and concise and possible using the least amount of finding tool calls and iterations.
Focus on actionable, practical learning resources and current industry-relevant skills.
Use only the tools provided. If you intend to use a tool that is NOT in the provided list,
call the tool named 'noop_func' instead with a short note describing what you wanted to do."""


def create_skill_llm():
    """
    This returns the skill llm if initialized, otherwise initializes and returns that.
    The LLM is configured for structured output based on the SkillResponse model.
    """
    global SKILL_LLM
    if not SKILL_LLM:
        SKILL_LLM = init_chat_model(SKILL_MODEL)
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
    similar_skills = vector_fuzzy_search(skill_title, "title_vector")
    if not similar_skills:
        return f"No similar skills found for '{skill_title}'"

    return "\n".join(
        [
            f"{skill.title} - Type: {skill.type} - Tags: {', '.join(skill.tags[:3])} (Similarity: {1 - skill.distance:.2f})"
            for skill in similar_skills
        ]
    )


@tool
def find_similar_skill_types(skill_type: str) -> str:
    """
    Find similar skill types/categories using vector fuzzy search.
    Input: A skill type or category (e.g., 'tutorial', 'course', 'documentation')
    """
    similar_types = vector_fuzzy_search(skill_type, "type_vector")
    if not similar_types:
        return f"No similar skill types found for '{skill_type}'"

    return "\n".join(
        [
            f"{skill.title} - Type: {skill.type} (Similarity: {1 - skill.distance:.2f})"
            for skill in similar_types
        ]
    )


@tool
def find_skills_with_relevant_tags(tags: str) -> str:
    """
    Find skills with relevant tags using vector fuzzy search.
    Input: Comma-separated tags (e.g., 'python, programming, beginner')
    """
    tags_str = " ".join([tag.strip() for tag in tags.split(",")])
    relevant_skills = vector_fuzzy_search(tags_str, "tags_vector")
    if not relevant_skills:
        return f"No skills found with relevant tags for '{tags}'"

    return "\n".join(
        [
            f"{skill.title} - Tags: {', '.join(skill.tags)} - Type: {skill.type} (Similarity: {1 - skill.distance:.2f})"
            for skill in relevant_skills
        ]
    )


@tool
def get_skill_details(skill_title: str) -> str:
    """
    Get full details of the 3 most similar skill by title using fuzzy vector search.
    Input: A string representing the skill title to search for.
    Output: A formatted string with details of the top matching skill.
    """
    similar_skills = vector_fuzzy_search(skill_title, "title_vector", threshold=0.8)
    if similar_skills:
        details = []
        for i in range(3):
            skill = similar_skills[i]
            details.append(
                f"""
            Title: {skill.title}
            Type: {skill.type}
            Tags: {', '.join(skill.tags) if skill.tags else 'N/A'}
            URL: {skill.url}
            Similarity: {1 - skill.distance:.2f}
            """
            )

        return "\n------\n".join(details)
    else:
        return f"No similar skill found for '{skill_title}'."


@tool
def noop_func(tool_input: str = "", *args) -> str:
    """
    Fallback tool: called when a requested tool is not available. Returns a skip message.
    """

    return "[SKIPPED TOOL] The agent attempted to call a tool that is not available."


@tool
def tavily_search(query: str) -> str:
    """
    Search online for additional skill development resources, courses, tutorials, or current information.
    Use this when the skill catalog doesn't have sufficient information.
    Input: Search query for online resources
    """
    if not TAVILY_API_KEY:
        return "Tavily search not available - API key not configured"

    try:
        search_tool = TavilySearchResults(
            api_key=TAVILY_API_KEY, max_results=2, search_depth="advanced"
        )
        results = search_tool.invoke({"query": query})

        if not results:
            return f"No online results found for '{query}'"

        formatted_results = []
        for result in results:
            formatted_results.append(
                f"Title: {result.get('title', 'N/A')}\nURL: {result.get('url', 'N/A')}\nSummary: {result.get('content', 'N/A')}\n"
            )

        return "\n---\n".join(formatted_results)
    except Exception as e:
        return f"Error searching online: {str(e)}"


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
            get_skill_details,
            tavily_search,
            noop_func,
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
            summarization_prompt = f"Based on the reasoning so far:\n{steps_text}\n\nCompile all gathered information into a JSON format. The JSON object should have a 'skills' array, where each item has 'title', 'description', 'learning_outcomes', and a 'resources' array. Each resource should have 'title', 'url', and 'type'. Also include an 'explanation' string."

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
