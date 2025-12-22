from agents import Runner, trace, set_tracing_export_api_key
from openai.types.responses import ResponseTextDeltaEvent
import asyncio, os, json, re
from dotenv import load_dotenv
load_dotenv()
from agent import career_assistant
from tools import get_list_of_jobs, search_knowledge_base
from vectorstore import ingest_txt
from utils import upload_file_to_s3
import gradio as gr

tracing_api_key = os.environ["OPENAI_API_KEY"]
set_tracing_export_api_key(tracing_api_key)

async def handleChat(messages, history):
   # print("history:\n", history)
   # print("messages:\n", messages)

    conversation_chain = []
    if len(messages['text']) > 0:
        if len(history) > 0:
            for message_dict in history:
                if message_dict['content'][0]['type'] == 'text':
                    conversation_chain.append({'content': message_dict['content'][0]['text'], 'role': message_dict['role']})
                else:
                    conversation_chain.append({'content': message_dict['content'][0]['file']['path'], 'role': message_dict['role']})
            conversation_chain.append({'content': messages['text'], 'role': 'user'})
        else:
            conversation_chain = [{"content": messages['text'], "role": "user"}]
    
    max_turns = 5
    accumulated_response = ""
    if len(messages['files']) > 0:
        for file in messages['files']:
            if file.endswith('.txt'):
                s3_response = upload_file_to_s3(file, os.environ.get("S3_BUCKET_NAME"))
                result = ingest_txt(file, s3_response)
                accumulated_response += "```File Processed``` \n"
                yield accumulated_response   
        
    if len(messages['text']) > 0:
        for _ in range(max_turns):
            full_turn_response = ""
            try:
                with trace('job assistant workflow'):
                    result = Runner.run_streamed(career_assistant, conversation_chain)
                    async for event in result.stream_events():
                        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                            chunk = event.data.delta
                            full_turn_response += chunk
                            yield accumulated_response + full_turn_response
                        
                        # Keep original event handling if needed, but we are primarily looking for the text response matching the tool call
                        if event.type == "run_item_output_event" and hasattr(event.data, 'output'):
                            # Fallback if the runner actually handles it but yields output
                            pass
                            
            except Exception as e:
                yield f"Unexpected exception occured \n{e}"
                return

            # Check if response is a tool call (JSON list)
            tool_calls_found = False
            try:
                match = re.search(r'(\[.*"get_list_of_jobs".*\]|\[.*"search_knowledge_base".*\])', full_turn_response, re.DOTALL)
                
                if match:
                    possible_json = match.group(1)
                    tool_calls = json.loads(possible_json)
                    if isinstance(tool_calls, list):
                        tool_calls_found = True
                        accumulated_response += full_turn_response + "\n\n```Executing Tool...```\n\n"
                        yield accumulated_response
                        
                        tool_outputs = []
                        for call in tool_calls:
                            if call.get("name") == "get_list_of_jobs":
                                args = call.get("arguments", {})
                                try:
                                    if callable(get_list_of_jobs):
                                        res = await get_list_of_jobs(**args)
                                    else:
                                        res = "Error: Tool is not callable"
                                except Exception as tool_err:
                                    res = f"Tool Execution Error: {tool_err}"
                                
                                tool_outputs.append(res)
                            
                            if call.get("name") == "search_knowledge_base":
                                args = call.get("arguments", {})
                                try:
                                    if callable(search_knowledge_base):
                                        res = await search_knowledge_base(**args)
                                    else:
                                        res = "Error: Tool is not callable"
                                except Exception as tool_err:
                                    res = f"Tool Execution Error: {tool_err}"
                                
                                tool_outputs.append(res)
                            
            
                        conversation_chain.append({"role": "assistant", "content": full_turn_response})
                        conversation_chain.append({"role": "user", "content": f"Tool Output: {json.dumps(tool_outputs)}"})
                        
            except json.JSONDecodeError:
                pass
            except Exception as e:
                print(f"Error parsing tool call: {e}")
            
            if not tool_calls_found:
                break


async def main():
    gr.ChatInterface(
        fn=handleChat,
        title="CERT SIEM POC v2",
        autoscroll=True,
        fill_height=True,
        save_history=True,
        multimodal=True,
        textbox=gr.MultimodalTextbox(file_count="multiple", file_types=[".txt"], sources=["upload"])
    ).launch(footer_links=[])
        

if __name__ == "__main__":
    asyncio.run(main())
