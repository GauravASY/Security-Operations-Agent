from agents import Runner, trace, set_tracing_export_api_key
from openai.types.responses import ResponseTextDeltaEvent
import asyncio, os
from dotenv import load_dotenv
load_dotenv()
from agent import career_assistant
import gradio as gr

tracing_api_key = os.environ["OPENAI_API_KEY"]
set_tracing_export_api_key(tracing_api_key)

async def handleChat(messages, history):
    conversation_chain = []
    if len(history) > 0:
        for message_dict in history:
            conversation_chain.append({'content': message_dict['content'][0]['text'], 'role': message_dict['role']})
        conversation_chain.append({'content': messages, 'role': 'user'})
    else:
        conversation_chain = [{"content": messages, "role": "user"}]
    try:
        with trace('job assistant workflow'):
            result = Runner.run_streamed(career_assistant, conversation_chain)
            response_text = ""
            async for event in result.stream_events():
                if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                    response_text += event.data.delta
                    yield response_text
    except Exception as e:
        yield f"Unexpected exception occured"

async def main():
    gr.ChatInterface(
        fn=handleChat,
        title="CERT SIEM POC v2",
        autoscroll=True,
        fill_height=True,
        save_history=True,
    ).launch(footer_links=[])
        

if __name__ == "__main__":
    asyncio.run(main())
