import os
from langchain.chat_models import init_chat_model
from langchain.agents import initialize_agent, AgentType

CORDINATOR_MODEL = os.getenv("CORDINATOR_LLM")
CORDINATOR_AGENT = None


def get_coordinator_agent():
    """
    This gets the cordinator agent if initialised, otherwise initialises and returns that.

    02:24 01/09/2025
    """

    if not CORDINATOR_AGENT:
        llm = init_chat_model(model=CORDINATOR_MODEL)
        tools = []
        CORDINATOR_AGENT = initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            handle_parsing_errors=True,
        )

    return CORDINATOR_AGENT
