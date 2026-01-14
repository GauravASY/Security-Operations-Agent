from agents import Runner, trace, set_tracing_export_api_key
from openai.types.responses import ResponseTextDeltaEvent
import asyncio, os, json, re
from dotenv import load_dotenv
load_dotenv()
from llmAgent import career_assistant
from tools import get_file_content, search_indicators_by_report, search_by_victim, get_reportsID_by_technique, get_reports_by_reportID
from vectorstore import ingest_txt, ingest_pdf
from utils import upload_file_to_s3
from database import init_db
import gradio as gr


import traceback

tracing_api_key = os.environ["OPENAI_API_KEY"]
set_tracing_export_api_key(tracing_api_key)

async def handleChat(messages, history):
    try:
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
                    result = await ingest_txt(file, s3_response)
                    if result['success']:
                        accumulated_response += f"```{result['message']}``` \n"
                    else:
                        accumulated_response += f"```{result['message']}``` \n"
                    yield accumulated_response  
                
                if file.endswith('.pdf'):
                    s3_response = upload_file_to_s3(file, os.environ.get("S3_BUCKET_NAME"))
                    result = await ingest_pdf(file, s3_response)
                    if result['success']:
                        accumulated_response += f"```{result['message']}``` \n"
                    else:
                        accumulated_response += f"```{result['message']}``` \n"
                    yield accumulated_response  
            
        if len(messages['text']) > 0:
            for turn_num in range(max_turns):
                full_turn_response = ""
                try:
                    with trace('job assistant workflow'):
                        result = Runner.run_streamed(career_assistant, conversation_chain)
                        async for event in result.stream_events():
                            if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                                chunk = event.data.delta
                                full_turn_response += chunk
                            
                            # Keep original event handling if needed, but we are primarily looking for the text response matching the tool call
                            if event.type == "run_item_output_event" and hasattr(event.data, 'output'):
                                # Fallback if the runner actually handles it but yields output
                                pass
                    
                    print(f"\n=== TURN {turn_num} DEBUG ===")
                    print(f"full_turn_response length: {len(full_turn_response)}")
                    print(f"full_turn_response content: {full_turn_response[:500] if full_turn_response else 'EMPTY'}")
                    print("=== END DEBUG ===\n")
                                
                except Exception as e:
                    accumulated_response += f"\nUnexpected exception occurred: {e}"
                    yield accumulated_response
                    return

                # Handle empty response (can happen between tool calls)
                if not full_turn_response or len(full_turn_response.strip()) == 0:
                    print(f"WARNING: Turn {turn_num} returned empty response. Ending conversation.")
                    # If we have accumulated response, yield it; otherwise yield a default message
                    if not accumulated_response:
                        accumulated_response = "Processing completed."
                    yield accumulated_response
                    break

                # Check if response is a tool call (JSON list)
                tool_calls_found = False
                try:
                    match = re.search(r'(\[.*?"get_file_content".*?\]|\[.*?"search_indicators_by_report".*?\]|\[.*?"search_by_victim".*?\]|\[.*?"get_reportsID_by_technique".*?\]|\[.*?"get_reports_by_reportID".*?\])', full_turn_response, re.DOTALL)
                    
                    if match:
                        possible_json = match.group(1)
                        tool_calls = json.loads(possible_json)
                        if isinstance(tool_calls, list):
                            tool_calls_found = True
                            
                            tool_outputs = []
                            for call in tool_calls:
                                if call.get("name") == "search_indicators_by_report":
                                    args = call.get("arguments", {})
                                    try:
                                        if callable(search_indicators_by_report):
                                            res = await search_indicators_by_report(**args)
                                        else:
                                            res = "Error: Tool is not callable"
                                    except Exception as tool_err:
                                        res = f"Tool Execution Error: {tool_err}"
                                    
                                    tool_outputs.append(res)
                                
                                if call.get("name") == "get_file_content":
                                    args = call.get("arguments", {})
                                    try:
                                        if callable(get_file_content):
                                            res = await get_file_content(**args)
                                        else:
                                            res = "Error: Tool is not callable"
                                    except Exception as tool_err:
                                        res = f"Tool Execution Error: {tool_err}"
                                    
                                    tool_outputs.append(res)
                                
                                if call.get("name") == "search_by_victim":
                                    args = call.get("arguments", {})
                                    try:
                                        if callable(search_by_victim):
                                            res = await search_by_victim(**args)
                                        else:
                                            res = "Error: Tool is not callable"
                                    except Exception as tool_err:
                                        res = f"Tool Execution Error: {tool_err}"
                                    
                                    tool_outputs.append(res)
                                
                                if call.get("name") == "get_reportsID_by_technique":
                                    args = call.get("arguments", {})
                                    try:
                                        if callable(get_reportsID_by_technique):
                                            res = await get_reportsID_by_technique(**args)
                                        else:
                                            res = "Error: Tool is not callable"
                                    except Exception as tool_err:
                                        res = f"Tool Execution Error: {tool_err}"
                                    
                                    tool_outputs.append(res)
                                
                                if call.get("name") == "get_reports_by_reportID":
                                    args = call.get("arguments", {})
                                    try:
                                        if callable(get_reports_by_reportID):
                                            res = await get_reports_by_reportID(**args)
                                        else:
                                            res = "Error: Tool is not callable"
                                    except Exception as tool_err:
                                        res = f"Tool Execution Error: {tool_err}"
                                    
                                    tool_outputs.append(res)
                
                            # Helper function to format tool outputs in a readable way
                            def format_tool_output(output):
                                if isinstance(output, tuple):
                                    # Handle database tuple results
                                    if len(output) == 3:
                                        # Likely (content, summary, id) from get_file_content
                                        return f"Content: {output[0]}\nSummary: {output[1]}\nReport ID: {output[2]}"
                                    else:
                                        return str(output)
                                elif isinstance(output, list):
                                    return json.dumps(output, indent=2)
                                else:
                                    return str(output)
                            
                            conversation_chain.append({"role": "assistant", "content": full_turn_response})
                            # Format tool outputs more clearly for the agent
                            tool_result_message = "The tools have been executed successfully. Here are the results:\n\n"
                            for i, output in enumerate(tool_outputs):
                                formatted_output = format_tool_output(output)
                                tool_result_message += f"Result {i+1}:\n{formatted_output}\n\n"
                            tool_result_message += "Now please synthesize these results and provide a complete answer to the user. DO NOT call the tools again."
                            
                            print(f"\n=== TOOL RESULT MESSAGE ===")
                            print(tool_result_message[:500])
                            print("=== END TOOL RESULT ===\n")
                            
                            conversation_chain.append({"role": "user", "content": tool_result_message})
                            # Continue to next turn to let agent process tool outputs
                            continue
                            
                except json.JSONDecodeError:
                    pass
                except Exception as e:
                    print(f"Error parsing tool call: {e}")
                
                if not tool_calls_found:
                    # This is the final answer - stream it to the user
                    if full_turn_response:
                        for char in full_turn_response:
                            accumulated_response += char
                            yield accumulated_response
                    else:
                        # Edge case: no tool calls but also no content
                        if not accumulated_response:
                            accumulated_response = "Processing completed."
                        yield accumulated_response
                    break
    except StopAsyncIteration:
        # Always yield something before returning to prevent RuntimeError
        if accumulated_response:
            yield accumulated_response
        else:
            yield "Processing completed."
        return
    except Exception as e:
        traceback.print_exc()
        accumulated_response += f"\nUnexpected Critical Error: {e}"
        yield accumulated_response


async def main():
    init_db()
    gr.ChatInterface(
        fn=handleChat,
        title="Security Operations Agent Interface",
        autoscroll=True,
        fill_height=True,
        save_history=True,
        multimodal=True,
        textbox=gr.MultimodalTextbox(file_count="multiple", file_types=[".txt", ".pdf"], sources=["upload"])
    ).launch(footer_links=[], theme=gr.themes.Citrus(primary_hue=gr.themes.colors.emerald, secondary_hue=gr.themes.colors.yellow))
        

if __name__ == "__main__":
    asyncio.run(main())
