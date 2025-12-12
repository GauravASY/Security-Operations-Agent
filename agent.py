from agents import Agent
from agents.extensions.models.litellm_model import LitellmModel
import os
from prompt import career_assistant_prompt
from tools import get_list_of_jobs


google_model = LitellmModel(
    model="ollama/llama3:latest",  # specific LiteLLM model identifier
    base_url="http://localhost:11434",
    api_key="ollama"
)

career_assistant = Agent(
    name= "Gaurav",
    instructions= career_assistant_prompt,
    model = google_model,
    tools = [get_list_of_jobs]
)
