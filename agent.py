from agents import Agent, set_tracing_disabled
from agents.extensions.models.litellm_model import LitellmModel
from openai import AsyncOpenAI
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
import os
from prompt import career_assistant_prompt
from tools import get_list_of_jobs, search_knowledge_base

set_tracing_disabled(True)

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

career_assistant = Agent(
    name= "Gaurav",
    instructions= career_assistant_prompt,
    model = custom_model,
    tools = [get_list_of_jobs, search_knowledge_base]
)
