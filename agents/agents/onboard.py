from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from db.models.onboard import OnboardCatalog
from db.models.embeddings import embeddings
from pgvector.django import CosineDistance
import json
from django.core.cache import cache
from agents.agents.model_config import ONBOARD_MODEL

ONBOARD_LLM = None
ONBOARD_AGENT = None

ONBOARD_PROMPT = "You are an onboarding assistant.\
First, use the search tools (find_similar_job_titles, find_similar_specializations, find_jobs_with_relevant_tags)\
to explore relevant job information based on the query. Do not jump straight to get_job_details.\
If you find promising matches from the searches, then use get_job_details\
(repeatedly if multiple similar job titles and/or specialization and/or tags) to retrieve full details for similar jobs.\
From the gathered information and various similar jobs and/or specialization and/or tags,\
you can create invent details from the gathered info. Compile the information into the compulsory json string (not actual json object but json string) format with keys:\
'checklist' (array), 'resources' (array), and 'explanation' (string).\
Use only the tools provided."


def create_onboard_llm():
    """
    This returns the onboard llm if initialized, otherwise initializes and returns that.

    05:23 01/09/2025
    """

    global ONBOARD_LLM
    if not ONBOARD_LLM:
        # ONBOARD_LLM = init_chat_model(ONBOARD_MODEL, reasoning_effort= "low")
        ONBOARD_LLM = ChatGroq(model=ONBOARD_MODEL.split(':')[-1], reasoning_effort='low')

    return ONBOARD_LLM


def vector_fuzzy_search(query: str, vector_field: str, threshold: float = 0.8) -> list:
    """
    Uniform helper for fuzzy vector search.
    Computes embedding for query and finds top 3 similar items using cosine similarity.
    """
    query_vector = embeddings.embed_query(query)
    similar_items = (
        OnboardCatalog.objects.annotate(
            distance=CosineDistance(vector_field, query_vector)
        )
        .filter(distance__lt=threshold)
        .order_by("distance")[:3]
    )  # Lower distance = higher similarity
    return similar_items


@tool(name_or_callable="json")
def json_tool(tool_input: str = "") -> str:
    """Guardrail: Call this tool for any json related functions need to be performed"""
    return tool_input


@tool
def find_similar_job_titles(job_title: str) -> str:
    """
    Find similar job titles using vector fuzzy search.
    """
    cache_key = f"find_similar_job_titles_{job_title}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    similar_jobs = vector_fuzzy_search(job_title, "title_vector")
    result = "\n".join(
        [
            f"{job.title} - Specialization: {job.specialization} (Similarity: {1 - job.distance:.2f})"
            for job in similar_jobs
        ]
    )
    cache.set(cache_key, result, timeout=172800)
    return result


@tool
def find_similar_specializations(specialization: str) -> str:
    """
    Find similar specializations using vector fuzzy search.
    """
    cache_key = f"find_similar_specializations_{specialization}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    similar_specs = vector_fuzzy_search(specialization, "specialization_vector")
    result = "\n".join(
        [
            f"{spec.title} - Specialization: {spec.specialization} (Similarity: {1 - spec.distance:.2f})"
            for spec in similar_specs
        ]
    )
    cache.set(cache_key, result, timeout=172800)
    return result


@tool
def find_jobs_with_relevant_tags(tags: str) -> str:
    """
    Find jobs with relevant tags using vector fuzzy search. The tags will be split on commas and used.
    """
    cache_key = f"find_jobs_with_relevant_tags_{tags}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    tags_str = " ".join([tag.strip() for tag in tags.split(",")])
    relevant_jobs = vector_fuzzy_search(tags_str, "tags_vector")
    result = "\n".join(
        [
            f"{job.title} - Tags: {', '.join(job.tags)} (Similarity: {1 - job.distance:.2f})"
            for job in relevant_jobs
        ]
    )
    cache.set(cache_key, result, timeout=172800)
    return result


@tool
def get_job_details(job_title: str) -> str:
    """
    Get full details of the most similar job by title using fuzzy vector search, including title, specialization, tags, checklist, and resources.
    Input: A string representing the job title to search for (e.g., 'Software Engineer').
    Output: A formatted string with details of the top matching job.
    """
    cache_key = f"get_job_details_{job_title}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    similar_jobs = vector_fuzzy_search(job_title, "title_vector", threshold=0.8)
    if similar_jobs:
        job = similar_jobs[0]  # Top result

        details = f"""
        Title: {job.title}
        Specialization: {job.specialization or 'N/A'}
        Tags: {', '.join(job.tags) if job.tags else 'N/A'}
        Checklist: {'; '.join(job.checklist) if job.checklist else 'N/A'}
        Resources: {'; '.join(job.resources) if job.resources else 'N/A'}
        Similarity: {1 - job.distance:.2f}
        """
        result = details.strip()
    else:
        result = f"No similar job found for '{job_title}'."

    cache.set(cache_key, result, timeout=172800)
    return result


def get_job_details_title_spec(job_title: str, specialization: str = "N/A") -> str:
    """
    Get full details of the most similar job by title and specialization using fuzzy vector search, including title, specialization, tags, checklist, and resources.
    Input: A string representing the job title - specialization to search for (e.g., 'Software Engineer - Backend').
    Output: A formatted string with details of the top matching job.
    """

    # Search for similar jobs by title
    similar_jobs_by_title = vector_fuzzy_search(
        job_title, "title_vector", threshold=0.8
    )

    if not specialization:
        specialization = "N/A"

    # Search for similar jobs by specialization
    similar_jobs_by_spec = vector_fuzzy_search(
        specialization, "specialization_vector", threshold=0.8
    )

    # Combine results and sort by the closest match
    combined_results = list(set(list(similar_jobs_by_title)) & set(list(similar_jobs_by_spec)))
    combined_results = sorted(combined_results, key=lambda job: job.distance)

    if combined_results and combined_results[0].distance < 0.1:
        job = combined_results[0]  # Top result

        details = {
            "checklist": job.checklist,
            "resources": job.resources,
            "explanation": f"Near Exact match found in Onboard Catalog with similarity of {(1 - job.distance)*100:.1f}%",
        }

        return details
    else:
        return None


def create_onboard_agent():
    """
    This returns the onboard agent if initialized, otherwise initializes and returns that.
    """
    global ONBOARD_AGENT
    if not ONBOARD_AGENT:
        llm = create_onboard_llm()
        tools = [
            find_similar_job_titles,
            find_similar_specializations,
            find_jobs_with_relevant_tags,
            get_job_details,
            json_tool
        ]
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    ONBOARD_PROMPT,
                ),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}"),
            ]
        )
        agent = create_tool_calling_agent(llm, tools, prompt)
        ONBOARD_AGENT = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True,
            return_intermediate_steps=True,
            early_stopping_method="generate",
            max_iterations=8
        )

    return ONBOARD_AGENT


def run_onboard_agent(
    query: str = None, job_title: str = None, specialization: str = None
):
    """
    Runs the onboard agent with the given query and returns the JSON response. If no query is given, returns the best matching job
    if the similarity is greater than 0.95.
    """
    cache_key = f"onboard_agent_{job_title}_{specialization}_{query}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    if not query:
        if not job_title:
            raise Exception("Job title is required if no additional query is given!")

        job_details = get_job_details_title_spec(job_title, specialization)
        if job_details:
            cache.set(cache_key, job_details, timeout=172800)
            return job_details
        else:
            pass  # No good similar job

    if specialization:
        base_query = f"{job_title} - {specialization}"
    else:
        base_query = job_title

    full_query = f"{base_query}. Extra user query: {query}".strip()

    agent = create_onboard_agent()
    result = agent.invoke({"input": full_query})

    data: str = result.get("output", "{}")
    data = data[data.find("{") : data.rfind("}") + 1]

    final_result = json.loads(data)
    cache.set(cache_key, final_result, timeout=172800)
    return final_result
