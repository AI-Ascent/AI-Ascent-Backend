import os
from langchain.chat_models import init_chat_model
from langchain.agents import initialize_agent, AgentType
from dotenv import load_dotenv

load_dotenv()


CORDINATOR_MODEL = os.getenv("CORDINATOR_MODEL")
CORDINATOR_AGENT = None


def get_coordinator_agent():
    """
    This returns the cordinator agent if initialised, otherwise initialises and returns that.

    02:24 01/09/2025
    """

    global CORDINATOR_AGENT
    if not CORDINATOR_AGENT:
        llm = init_chat_model(model=CORDINATOR_MODEL)
        tools = []
        CORDINATOR_AGENT = initialize_agent(
            tools=tools,
            llm=llm,
            # Using a non-reasoning model, so contraining it with a structured and convo type is good
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            handle_parsing_errors=True,
        )

    return CORDINATOR_AGENT
