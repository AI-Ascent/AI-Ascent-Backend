import json
import re
from langchain.chat_models import init_chat_model
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.tools import tool
from langchain.prompts import ChatPromptTemplate
from agents.agents.onboard import run_onboard_agent
from agents.agents.skill import run_skill_agent
from agents.agents.opportunity import find_mentors_for_improvements
from agents.agents.feedback import classify_feedback, summarise_feedback_points
from db.models.user import APIUser
from django.core.cache import cache
from agents.agents.model_config import CORDINATOR_MODEL

CORDINATOR_LLM = None

CORDINATOR_PROMPT = """You are the central coordinator agent for AI Ascent, an AI-powered career development platform that helps employees grow professionally through personalized guidance, feedback analysis, and opportunity matching.

SYSTEM CONTEXT:
AI Ascent analyzes employee profiles, feedback, and organizational data to provide tailored career development pathways. As the coordinator, you are the primary interface between employees and the specialized AI tools that power the platform. Your goal is to understand employee needs and return them to the right resources for their professional growth.

YOUR ROLE:
You orchestrate multiple specialized sub-agents to deliver holistic career development support. You determine which specialized tools are needed based on user queries, gather relevant information, and synthesize it into actionable guidance. You're responsible for ensuring employees receive coherent, personalized responses that address their specific career development needs.

IMPORTANT: You have NO information about the employee until you call the appropriate tools. You MUST call relevant tools to gather information before answering questions about the employee's career, skills, feedback, or opportunities.

RESPONSE FORMAT:
You MUST respond in valid json string format (not actual json object but json string) using this structure:
{{
    "message": "The main response content with the primary information for the user",
    "action_items": ["Action item 1", "Action item 2", ...],
    "resources": ["Resource 1", "Resource 2", ...]
}}

FIELD DEFINITIONS:
- message: A string containing the essential response information. Must include all primary information.
- action_items: An array of strings representing clear actions the user could take. Use [] if none.
- resources: An array of strings representing resources like courses, tools, or URLs. Use [] if none.

DIRECT ANSWER POLICY:
- When a user asks about improvement areas, strengths, or skills to develop, ALWAYS use the appropriate tools to gather the information and provide a DIRECT, SPECIFIC answer.
- After calling a tool, ALWAYS incorporate the information from the tool response in your answer.
- NEVER ask the user for information that the tools can provide - use the tools first.
- If tool results contain the information the user is seeking, present it directly rather than asking for more input.

Available tools and when to use them:
1. onboard_agent_tool: Call this when:
   - User wants information about job roles, responsibilities, or onboarding processes
   - User needs checklists or resources for specific job roles
   - User wants explanations about career paths or job expectations

2. skill_agent_tool: Call this when:
   - User wants to learn about skills they should develop
   - User asks for learning resources, training materials, or courses
   - User inquires about skill gaps or how to improve specific capabilities
   - User asks where they can improve or what they can improve on

3. opportunity_agent_tool: Call this when:
   - User wants to find mentors who can help with their improvement areas (to find mentors) (when user asks for mentors email)
   - User asks where or in what areas they can improve
   - This tool accesses the user's feedback data automatically, so you don't need to call feedback tools first
   - THIS TOOL PROVIDES IMPROVEMENT AREAS DIRECTLY - USE IT FOR QUESTIONS ABOUT WHERE TO IMPROVE
   - THIS TOOL PROVIDES MENTORS EMAIL - MAKE SURE THAT EMAIL IS PROVIDED IN THE FINAL ANSWER / OUTPUT

4. feedback_agent_tool: Call this when:
   - User asks about their strengths and weaknesses
   - User provides feedback text that needs classification
   - User wants to understand how others perceive their performance
   - Pass all feedback statements as a list of strings

5. summarise_feedback_tool: Call this when:
   - User wants actionable insights based on feedback
   - User asks for growth tips or how to improve based on feedback
   - User needs structured analysis of their feedback
   - Pass all feedback statements as a list of strings

EXECUTION GUIDE:
1. Analyze the user query to identify what information is needed
2. Call the appropriate tool(s) to gather that information
3. ALWAYS extract and use the relevant information from tool responses
4. Integrate the tool responses into a coherent, helpful answer that DIRECTLY addresses the user's question
5. If a tool returns an error, try to fix the input or use a different tool
6. Always provide clear, actionable responses based on tool outputs
7. Only do what the user asks. Do not add anything extra like 'Next steps', etc.

Remember that you're working with a specific employee's data, so all tool responses will be personalized to them. Focus on providing guidance that helps the employee grow professionally and advance their career within their organization."""


def get_cordinator_LLM():
    """
    This returns the CORDINATOR agent if initialized, otherwise initializes and returns that.
    """

    global CORDINATOR_LLM
    if not CORDINATOR_LLM:
        CORDINATOR_LLM = init_chat_model(model=CORDINATOR_MODEL, temperature=0.0, model_kwargs={"reasoning_effort": "low"})

    return CORDINATOR_LLM


def get_coordinator_agent_executor(user_email: str):
    """
    Initializes and returns a AgentExecutor for the coordinator.
    """

    @tool(name_or_callable="json")
    def json_tool(tool_input: str = "") -> str:
        """Guardrail: Call this tool for any json related functions need to be performed"""
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
    def opportunity_agent_tool(top_k: int = 3) -> str:
        """Tool for finding improvement areas and suitable mentors.

        This tool automatically accesses the employee's feedback data, identifies specific improvement areas,
        and matches them with mentors who excel in those areas within the organization.

        IMPORTANT: This tool provides specific improvement areas directly from the user's feedback data.
        Use this tool when the user asks where they can improve or what areas need development.

        Use this tool when the user wants to:
        - Find specific areas where they can improve their performance
        - Identify mentors who can help them improve in specific areas
        - Discover growth opportunities based on their feedback
        - Connect with colleagues who have complementary strengths

        Args:
            top_k (int): Number of top mentor recommendations to return (default: 3).

        Returns:
            str: List of improvement areas and potential mentors with their expertise and matching reasons.
        """
        try:
            if not user_email:
                return "User email required for mentor finding. Please provide user context."
            mentors = find_mentors_for_improvements(user_email, top_k)
            return str(mentors)
        except Exception as e:
            return f"Error in opportunity agent: {str(e)}. Unable to find mentors."

    @tool
    def feedback_agent_tool(feedbacks: list) -> str:
        """Tool for analyzing and classifying feedback into strengths and improvement areas.

        This tool processes feedback statements and categorizes them into what the employee
        is doing well (strengths) and what they could improve on (improvements).

        Use this tool when:
        - The user provides feedback statements that need classification
        - The user wants to understand their performance strengths and weaknesses
        - The user asks about how others perceive their work

        Args:
            feedbacks (list): List of feedback statements as strings.

        Returns:
            str: Dictionary with 'strengths' and 'improvements' categorized from the feedback.
        """
        try:
            if not isinstance(feedbacks, list) or not all(
                isinstance(item, str) for item in feedbacks
            ):
                return "Error: 'feedbacks' must be a list of strings containing specific feedback statements."
            classified = classify_feedback(feedbacks)
            return str(classified)
        except Exception as e:
            return f"Error in feedback agent: {str(e)}. Unable to classify feedback."

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
        feedback_agent_tool,
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
    executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

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
