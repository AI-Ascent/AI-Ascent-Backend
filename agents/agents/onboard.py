import os
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
from langchain.tools import tool
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate
from db.models.onboard import OnboardCatalog
from langchain_huggingface import HuggingFaceEmbeddings
from pgvector.django import CosineDistance
from langchain_core.output_parsers import JsonOutputParser
import json

load_dotenv()

ONBOARD_MODEL = os.getenv("ONBOARD_MODEL")
ONBOARD_LLM = None
ONBOARD_AGENT = None

ONBOARD_PROMPT = "You are an onboarding assistant. First, use the search tools (find_similar_job_titles, find_similar_specializations, find_jobs_with_relevant_tags) to explore relevant job information based on the query. Do not jump straight to get_job_details. If you find promising matches from the searches, then use get_job_details (repeatedly if multiple similar job titles and/or specialization and/or tags) to retrieve full details for similar jobs. If the job title is a nearly a perfect match, return exactly those details; if not, from the gathered information and various similar jobs and/or specialization and/or tags, you can create invent details from the gathered info. Compile the information into the required JSON format with keys: 'checklist' (array), 'resources' (array), and 'explanation' (string).\n{format_instructions}"

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


def create_onboard_llm():
    """
    This returns the onboard llm if initialized, otherwise initializes and returns that.

    05:23 01/09/2025
    """

    global ONBOARD_LLM
    if not ONBOARD_LLM:
        ONBOARD_LLM = init_chat_model(ONBOARD_MODEL, temperature=0.0)

    return ONBOARD_LLM


def vector_fuzzy_search(query: str, vector_field: str, threshold: float = 0.8) -> list:
    """
    Uniform helper for fuzzy vector search.
    Computes embedding for query and finds top 5 similar items using cosine similarity.
    """
    query_vector = embeddings.embed_query(query)
    similar_items = (
        OnboardCatalog.objects.annotate(
            distance=CosineDistance(vector_field, query_vector)
        )
        .filter(distance__lt=threshold)
        .order_by("distance")[:5]
    )  # Lower distance = higher similarity
    return similar_items


@tool
def find_similar_job_titles(job_title: str) -> str:
    """
    Find similar job titles using vector fuzzy search.
    """
    similar_jobs = vector_fuzzy_search(job_title, "title_vector")
    return "\n".join(
        [
            f"{job.title} - Specialization: {job.specialization} (Similarity: {1 - job.distance:.2f})"
            for job in similar_jobs
        ]
    )


@tool
def find_similar_specializations(specialization: str) -> str:
    """
    Find similar specializations using vector fuzzy search.
    """
    similar_specs = vector_fuzzy_search(specialization, "specialization_vector")
    return "\n".join(
        [
            f"{spec.title} - Specialization: {spec.specialization} (Similarity: {1 - spec.distance:.2f})"
            for spec in similar_specs
        ]
    )


@tool
def find_jobs_with_relevant_tags(tags: str) -> str:
    """
    Find jobs with relevant tags using vector fuzzy search. The tags will be split on commas and used.
    """
    tags_str = " ".join([tag.strip() for tag in tags.split(",")])
    relevant_jobs = vector_fuzzy_search(tags_str, "tags_vector")
    return "\n".join(
        [
            f"{job.title} - Tags: {', '.join(job.tags)} (Similarity: {1 - job.distance:.2f})"
            for job in relevant_jobs
        ]
    )


@tool
def get_job_details(job_title: str) -> str:
    """
    Get full details of the most similar job by title using fuzzy vector search, including title, specialization, tags, checklist, and resources.
    Input: A string representing the job title to search for (e.g., 'Software Engineer').
    Output: A formatted string with details of the top matching job.
    """
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
        return details.strip()
    else:
        return f"No similar job found for '{job_title}'."


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
        ]
        parser = JsonOutputParser()
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    ONBOARD_PROMPT,
                ),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}"),
            ]
        ).partial(format_instructions=parser.get_format_instructions())
        agent = create_tool_calling_agent(llm, tools, prompt)
        ONBOARD_AGENT = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)

    return ONBOARD_AGENT


def run_onboard_agent(query: str):
    """
    Runs the onboard agent with the given query and returns the JSON response.
    """
    agent = create_onboard_agent()
    result = agent.invoke({"input": query})

    return json.loads(result.get("output", '{}'))


