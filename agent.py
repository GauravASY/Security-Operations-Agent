from agents import Agent, set_tracing_disabled, handoff
from agents.extensions.models.litellm_model import LitellmModel
from openai import AsyncOpenAI
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
import os
from prompt import career_assistant_prompt, analysis_agent_prompt
from tools import get_list_of_jobs, search_knowledge_base

set_tracing_disabled(True)

def log_analyses_handoff(context):
    yield "```Delegating Analyses to Analysis Agent```\n\n"

#keeping this model for testing purposes.
google_model = LitellmModel(
    model="ollama/llama3:latest",  # specific LiteLLM model identifier
    base_url="http://localhost:11434",
    api_key="ollama"
)
custom_client = AsyncOpenAI(
    base_url=os.environ.get("LMAAS_URL"),
    api_key=os.environ.get("LMAAS_KEY"),
)

custom_model = OpenAIChatCompletionsModel(
    openai_client=custom_client,
    model=os.environ.get("LMAAS_MODEL"),
)

analysis_agent = Agent(
    name= "Analysis Agent",
    instructions= analysis_agent_prompt,
    handoff_description="Handles analysis of the uploaded text files for threats and provides recommendations",
    model = custom_model,
    tools = [search_knowledge_base]
)

career_assistant = Agent(
    name= "Gaurav",
    instructions= career_assistant_prompt,
    handoffs=[
        handoff(
            agent=analysis_agent,
            tool_name_override="analyze_text_file",
            on_handoff = log_analyses_handoff
        )
    ],
    model = custom_model,
    tools = [get_list_of_jobs, search_knowledge_base]
)