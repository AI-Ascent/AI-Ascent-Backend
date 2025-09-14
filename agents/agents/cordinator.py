import json
import re
from langchain.chat_models import init_chat_model
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.tools import tool
from langchain.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from agents.agents.onboard import run_onboard_agent
from agents.agents.skill import run_skill_agent
from agents.agents.opportunity import find_mentors_for_improvements
from agents.agents.feedback import summarise_feedback_points
from db.models.user import APIUser
from django.core.cache import cache
from agents.agents.model_config import CORDINATOR_MODEL

CORDINATOR_LLM = None

CORDINATOR_PROMPT = """
You are the central coordinator agent for AI Ascent (career development platform). Your job: route employee requests to the correct sub-agents, gather data via tools, synthesize personalized, actionable guidance, and return a single JSON-string response.

CONTEXT
- AI Ascent analyzes employee profiles, feedback, and org data to create tailored development pathways.
- You have no employee data until you call the appropriate tools.

RESPONSE FORMAT
- Return a JSON string (not a native object) exactly matching this structure:

```
{{
  "message": "primary response content",
  "action_items": ["Action 1", "Action 2"],
  "resources": ["Resource 1", "Resource 2"]
}}
```

- `message`: essential, complete answer.
- `action_items`: array of clear next steps (or `[]`).
- `resources`: array of courses/tools/URLs (or `[]`).

TOOLS & USAGE LIMITS (call counts enforced)
- `onboard_agent_tool` - call only once
  Use when: role descriptions, onboarding checklists, job expectations.
- `skill_agent_tool` - call at most twice
  Use when: skill recommendations, learning resources, skill gaps.
- `opportunity_agent_tool` - call only once
  Use when: find mentors. This tool auto-accesses feedback and returns mentor emails - include those emails in the final output.
- `summarise_feedback_tool` - call only once
  Use when: analyze existing feedback; pass feedback as a list of strings.

CORE RULES
- Always call the relevant tool(s) before answering any question about an employee’s career/skills/feedback/opportunities.
- Never ask the user for information that tools can provide.
- After calling a tool, incorporate its response directly and specifically into `message`.
- If a tool returns the requested information, present it - do not prompt the user for the same data.
- If a tool errors, fix the input or use another tool.
- Use as few tool calls/iterations as possible.
- Only perform what the user asked; do not add unsolicited sections.

Be concise, factual, and strictly follow the format and tool rules.
Remember that you're working with a specific employee's data, so all tool responses will be personalized to them
"""


def get_cordinator_LLM():
    """
    This returns the CORDINATOR agent if initialized, otherwise initializes and returns that.
    """

    global CORDINATOR_LLM
    if not CORDINATOR_LLM:
        # CORDINATOR_LLM = init_chat_model(model=CORDINATOR_MODEL, temperature=0.0, reasoning_effort= "low")
        CORDINATOR_LLM = ChatGroq(model=CORDINATOR_MODEL.split(':')[-1], reasoning_effort='low', temperature=0.0)

    return CORDINATOR_LLM


def get_coordinator_agent_executor(user_email: str):
    """
    Initializes and returns a AgentExecutor for the coordinator.
    """

    @tool(name_or_callable="json")
    def json_tool(tool_input: str = "") -> str:
        """Guardrail: Call this tool for any json related functions need to be performed. You should never have to create a json object however. Give the json string directly in final message."""
        return tool_input

    # Create tools dynamically with email context
    @tool
    def onboard_agent_tool(query: str) -> str:
        """Tool for getting personalized onboarding information and resources.

        This tool retrieves job-specific onboarding details, checklists, resources, and career path information
        based on the employee's job title and specialization from the database.

        Use this tool when the user needs information about:
        - Their specific job responsibilities and expectations
        - Onboarding resources and checklists for their role
        - Career development paths related to their position

        Args:
            query (str): Specific question about job role, onboarding needs, or career path.

        Returns:
            str: Structured information with onboarding checklists, resources, and explanations.
        """
        try:
            user = APIUser.objects.get(email=user_email)
            return run_onboard_agent(query, user.job_title, user.specialization)
        except Exception as e:
            return f"Error in onboarding agent: {str(e)}. Unable to process onboarding request."

    @tool
    def skill_agent_tool(query: str) -> str:
        """Tool for personalized skill development recommendations.

        This tool analyzes the employee's profile and provides tailored skill recommendations,
        learning resources, and training materials based on their job role and career goals.

        Use this tool when the user wants to:
        - Learn which skills they should develop for career growth
        - Find specific learning resources for skill improvement
        - Understand skill gaps in their current profile
        - Find areas where they can improve their capabilities

        Args:
            query (str): Question about skill development or learning needs.

        Returns:
            str: Personalized skill recommendations with descriptions, learning outcomes, and resources.
        """
        try:
            return run_skill_agent(query, user_email)
        except Exception as e:
            return f"Error in skill agent: {str(e)}. Unable to process skill development request."

    @tool
    def opportunity_agent_tool() -> str:
        """Tool for finding improvement areas and suitable mentors.

        This tool automatically accesses the employee's feedback data, identifies specific improvement areas,
        and matches them with mentors who excel in those areas within the organization.

        IMPORTANT: This tool provides specific improvement areas directly from the user's feedback data.
        Use this tool when the user asks where they can improve or what areas need development.

        Use this tool when the user wants to:
        - Find specific areas where they can improve their performance based on their feedbacks
        - Identify mentors who can help them improve in specific areas

        Returns:
            str: List of improvement areas and potential mentors with their expertise and matching reasons.
        """
        try:
            if not user_email:
                return "User email required for mentor finding. Please provide user context."
            mentors = find_mentors_for_improvements(user_email)
            return str(mentors)
        except Exception as e:
            return f"Error in opportunity agent: {str(e)}. Unable to find mentors."

    @tool
    def summarise_feedback_tool(feedbacks: list) -> str:
        """Tool for generating actionable insights and growth tips from feedback.

        This tool analyzes feedback in depth and provides structured insights on strengths,
        specific improvement suggestions, and practical growth tips the employee can implement.

        Use this tool when:
        - The user wants actionable advice based on their feedback
        - The user needs specific strategies to leverage strengths or address weaknesses
        - The user asks for practical ways to improve their performance

        Args:
            feedbacks (list): List of feedback statements as strings.

        Returns:
            str: Dictionary with 'strengths_insights', 'improvements_insights', and 'growth_tips'.
        """
        try:
            if not isinstance(feedbacks, list) or not all(
                isinstance(item, str) for item in feedbacks
            ):
                return "Error: 'feedbacks' must be a list of strings containing specific feedback statements."
            insights = summarise_feedback_points(feedbacks)
            return str(insights)
        except Exception as e:
            return f"Error in feedback summarization: {str(e)}. Unable to generate feedback insights."

    llm = get_cordinator_LLM()
    tools = [
        json_tool,
        onboard_agent_tool,
        skill_agent_tool,
        opportunity_agent_tool,
        summarise_feedback_tool,
    ]
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", CORDINATOR_PROMPT),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    )
    agent = create_tool_calling_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=8)

    return executor


def invoke_coordinator(user_input: str, user_email: str) -> str:
    """
    Invokes the coordinator agent with user input and optional user email.

    The coordinator routes the query to appropriate sub-agents and composes a response.
    User email is used internally for personalized tools without exposing it to the LLM.

    Args:
        user_input (str): The user's query or request.
        user_email (str): User's email for personalized features like mentor finding.

    Returns:
        str: The composed response from the coordinator agent in JSON format.
    """
    cache_key = f"coordinator_response_{user_email}_{user_input}"
    cached_response = cache.get(cache_key)
    if cached_response:
        return cached_response

    executor = get_coordinator_agent_executor(user_email)
    result = executor.invoke({"input": user_input})

    # Extract the JSON output from the text response
    output_text: str = result["output"]

    try:
        json_str = output_text[output_text.find("{") : output_text.rfind("}") + 1]
        json_obj = json.loads(json_str)
        cache.set(cache_key, json_obj, timeout=172800)  # Cache for 2 days
        return json_obj
    except json.JSONDecodeError:
        # If JSON is malformed, ask the LLM to fix it
        fix_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a JSON repair specialist. The following JSON string is malformed. 
            Fix it to create valid JSON that follows this schema:
            {{
                "message": "string with main content",
                "action_items": ["string item 1", "string item 2", ...],
                "resources": ["string resource 1", "string resource 2", ...]
            }}
            
            Return ONLY the fixed JSON with no additional text or explanations.""",
                ),
                ("human", json_str),
            ]
        )

        fix_chain = fix_prompt | get_cordinator_LLM()
        fixed_result = fix_chain.invoke({"json_str": json_str})
        fixed_json = fixed_result.content

        fixed_json_str = fixed_json[fixed_json.find("{") : fixed_json.rfind("}") + 1]
        final_json = json.loads(fixed_json_str)
        cache.set(cache_key, final_json, timeout=172800)
        return final_json
